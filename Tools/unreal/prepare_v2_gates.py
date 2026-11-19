"""Prepare V2 Lux3D Articulated Dream Gates & Filigree Vortex Ring for Unreal Engine 5.8.

Owned paths:
  - E:\\紫萱2版\\Tools\\unreal\\prepare_v2_gates.py
  - E:\\紫萱2版\\Assets\\LuxGenerated\\V2_Gates\\

Outputs into E:\\紫萱2版\\Assets\\LuxGenerated\\V2_Gates\\Ready\\:
  - Gate_Frame.glb, Gate_Leaf_L.glb, Gate_Leaf_R.glb       (from G01_ImperialSakuraGate URDF)
  - StarGate_OuterRing.glb, StarGate_InnerRing.glb         (from G03_ImperialAstrolabeGate URDF)
  - Tunnel_Ring.glb                                        (from T01_FiligreeStarRing, centered in glTF X-Y plane)
And writes full provenance, SHA256 hashes, bounds, and exact UE centimeter hinge offsets into:
  - E:\\紫萱2版\\Assets\\LuxGenerated\\V2_Gates\\manifest.json

UE5 Interchange coordinate mapping:
  X_ue = 100.0 * X_gltf
  Y_ue = 100.0 * Z_gltf
  Z_ue = 100.0 * Y_gltf
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import struct
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from PIL import Image

FORBIDDEN_TASK_IDS = {7997862, 7997813, 7636420, 7636417, 7636414, 7636411, 7636404}

V2_ROOT = Path(r"E:\紫萱2版\Assets\LuxGenerated\V2_Gates")
READY_DIR = V2_ROOT / "Ready"
MANIFEST_PATH = V2_ROOT / "manifest.json"


def sha256_file(path: Path) -> dict:
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def load_glb(path: Path) -> tuple[dict, bytes]:
    data = path.read_bytes()
    magic, version, _ = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67 or version != 2:
        raise ValueError(f"Not a valid glTF 2.0 binary: {path}")
    jlen, _ = struct.unpack_from("<II", data, 12)
    doc = json.loads(data[20 : 20 + jlen].decode("utf-8"))
    bin_chunk = data[20 + jlen + 8 :] if len(data) > 20 + jlen + 8 else b""
    return doc, bin_chunk


def save_glb(path: Path, doc: dict, bin_chunk: bytes) -> None:
    jbytes = json.dumps(doc, separators=(",", ":")).encode("utf-8")
    jbytes += b" " * ((4 - (len(jbytes) % 4)) % 4)
    bin_padded = bin_chunk + (b"\x00" * ((4 - (len(bin_chunk) % 4)) % 4))
    total_len = 12 + 8 + len(jbytes) + 8 + len(bin_padded)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total_len))
        f.write(struct.pack("<II", len(jbytes), 0x4E4F534A))
        f.write(jbytes)
        f.write(struct.pack("<II", len(bin_padded), 0x004E4942))
        f.write(bin_padded)


def quat_to_mat3(q: list[float]) -> np.ndarray:
    x, y, z, w = q
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )


def node_local_matrix(node: dict) -> np.ndarray:
    if "matrix" in node:
        return np.array(node["matrix"], dtype=np.float64).reshape(4, 4).T
    mat = np.eye(4, dtype=np.float64)
    if "scale" in node:
        s = np.array(node["scale"], dtype=np.float64)
        mat[:3, :3] = np.diag(s)
    if "rotation" in node:
        r = quat_to_mat3(node["rotation"])
        mat[:3, :3] = r @ mat[:3, :3]
    if "translation" in node:
        mat[:3, 3] = np.array(node["translation"], dtype=np.float64)
    return mat


def read_accessor_array(doc: dict, bin_chunk: bytes, acc_idx: int) -> np.ndarray:
    acc = doc["accessors"][acc_idx]
    bv = doc["bufferViews"][acc["bufferView"]]
    off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    cnt = acc["count"]
    ctype_map = {
        5120: np.int8,
        5121: np.uint8,
        5122: np.int16,
        5123: np.uint16,
        5125: np.uint32,
        5126: np.float32,
    }
    ncomp_map = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}
    dtype = ctype_map[acc["componentType"]]
    ncomp = ncomp_map[acc["type"]]
    stride = bv.get("byteStride", 0)
    elem_size = np.dtype(dtype).itemsize * ncomp
    if stride and stride != elem_size:
        raw = np.frombuffer(bin_chunk, dtype=np.uint8, count=cnt * stride, offset=off).reshape(cnt, stride)[:, :elem_size]
        arr = np.frombuffer(raw.tobytes(), dtype=dtype).reshape(cnt, ncomp).copy()
    else:
        arr = np.frombuffer(bin_chunk, dtype=dtype, count=cnt * ncomp, offset=off).copy()
        if ncomp > 1:
            arr = arr.reshape(cnt, ncomp)
    return arr


def extract_baked_geometry(path: Path) -> dict:
    """Extract world-baked positions, normals, UVs, indices, and original doc/bin for PBR textures."""
    doc, bin_chunk = load_glb(path)
    nodes = doc.get("nodes", [])

    # Traverse scene roots to accumulate world transforms per mesh
    scene_idx = doc.get("scene", 0)
    roots = doc.get("scenes", [{"nodes": list(range(len(nodes)))}])[scene_idx].get("nodes", [])
    mesh_instances: list[tuple[int, np.ndarray]] = []

    def visit(n_idx: int, parent_mat: np.ndarray):
        node = nodes[n_idx]
        wmat = parent_mat @ node_local_matrix(node)
        if "mesh" in node:
            mesh_instances.append((node["mesh"], wmat))
        for ch in node.get("children", []):
            visit(ch, wmat)

    if roots:
        for r in roots:
            visit(r, np.eye(4, dtype=np.float64))
    else:
        for m_idx in range(len(doc.get("meshes", []))):
            mesh_instances.append((m_idx, np.eye(4, dtype=np.float64)))

    all_pos, all_norm, all_uv, all_tris = [], [], [], []
    vert_offset = 0
    for m_idx, wmat in mesh_instances:
        lin = wmat[:3, :3]
        trans = wmat[:3, 3]
        det = np.linalg.det(lin)
        norm_mat = np.linalg.inv(lin).T if abs(det) > 1e-12 else np.eye(3)

        for prim in doc["meshes"][m_idx].get("primitives", []):
            attrs = prim["attributes"]
            pos = read_accessor_array(doc, bin_chunk, attrs["POSITION"]).astype(np.float64)
            pos = (pos @ lin.T) + trans

            if "NORMAL" in attrs:
                nrm = read_accessor_array(doc, bin_chunk, attrs["NORMAL"]).astype(np.float64)
                nrm = nrm @ norm_mat.T
                lens = np.linalg.norm(nrm, axis=1, keepdims=True)
                nrm = np.divide(nrm, np.maximum(lens, 1e-9))
            else:
                nrm = np.zeros_like(pos)
                nrm[:, 2] = 1.0

            if "TEXCOORD_0" in attrs:
                uv = read_accessor_array(doc, bin_chunk, attrs["TEXCOORD_0"]).astype(np.float32)
            else:
                uv = np.zeros((len(pos), 2), dtype=np.float32)

            if "indices" in prim:
                tris = read_accessor_array(doc, bin_chunk, prim["indices"]).astype(np.uint32).reshape(-1, 3)
            else:
                tris = np.arange(len(pos), dtype=np.uint32).reshape(-1, 3)

            if det < 0:
                tris = tris[:, [0, 2, 1]]

            all_pos.append(pos)
            all_norm.append(nrm)
            all_uv.append(uv)
            all_tris.append(tris + vert_offset)
            vert_offset += len(pos)

    return {
        "pos": np.vstack(all_pos),
        "norm": np.vstack(all_norm),
        "uv": np.vstack(all_uv),
        "tris": np.vstack(all_tris),
        "doc": doc,
        "bin": bin_chunk,
    }


def merge_geometries(geoms: list[tuple[dict, np.ndarray]]) -> dict:
    """Merge multiple (geom, translation_offset) pairs assuming shared texture atlas."""
    base_doc = geoms[0][0]["doc"]
    base_bin = geoms[0][0]["bin"]
    pos_l, norm_l, uv_l, tris_l = [], [], [], []
    v_off = 0
    for g, offset in geoms:
        pos_l.append(g["pos"] + offset)
        norm_l.append(g["norm"])
        uv_l.append(g["uv"])
        tris_l.append(g["tris"] + v_off)
        v_off += len(g["pos"])
    return {
        "pos": np.vstack(pos_l),
        "norm": np.vstack(norm_l),
        "uv": np.vstack(uv_l),
        "tris": np.vstack(tris_l),
        "doc": base_doc,
        "bin": base_bin,
    }


_PBR_CACHE: dict[tuple[str, bool], tuple[bytes, bytes, bytes]] = {}


def build_imperial_pbr_maps(orig_doc: dict, orig_bin: bytes, is_stained_glass_leaf: bool) -> tuple[bytes, bytes, bytes]:
    """Synthesize museum-grade 2048 BaseColor + 1024 24k-Gold/Jade MetallicRoughness + 1024 Celestial Emissive PNGs."""
    mat0 = orig_doc["materials"][0]["pbrMetallicRoughness"]
    bc_tex_idx = mat0["baseColorTexture"]["index"]
    bc_img_idx = orig_doc["textures"][bc_tex_idx]["source"]
    bv = orig_doc["bufferViews"][orig_doc["images"][bc_img_idx]["bufferView"]]
    raw_bc = orig_bin[bv.get("byteOffset", 0) : bv.get("byteOffset", 0) + bv["byteLength"]]
    cache_key = (hashlib.md5(raw_bc).hexdigest(), is_stained_glass_leaf)
    if cache_key in _PBR_CACHE:
        return _PBR_CACHE[cache_key]

    im_rgba = Image.open(io.BytesIO(raw_bc)).convert("RGBA")
    arr = np.asarray(im_rgba, dtype=np.float32) / 255.0
    rgb = arr[:, :, :3].copy()

    # Gentle exposure & chroma lift if raw baked albedo is slightly dark (e.g. G01 p90 ~ 0.67)
    p90 = float(np.percentile(rgb, 90))
    if p90 < 0.84:
        gain = min(1.26, 0.86 / max(p90, 0.35))
        rgb = 1.0 - np.exp(-rgb * gain * 1.45) / np.exp(-1.45) if False else np.clip(rgb * gain, 0.0, 1.0)
        # Subtle saturation boost (1.14x) around luminance
        lum = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
        rgb = np.clip(lum[:, :, None] + (rgb - lum[:, :, None]) * 1.15, 0.0, 1.0)

    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    # Gold classifier: warm yellow-amber hue (R > G > B with strong R-B chroma)
    gold_score = np.clip(((r - b) - 0.11) / 0.16, 0.0, 1.0) * np.clip(((g - b) - 0.03) / 0.12, 0.0, 1.0) * np.clip((r - 0.30) / 0.20, 0.0, 1.0)

    # Boost gold F0 reflectance gently so metallic=0.86 gleams bright royal 24k gold in Cycles & UE5!
    gold_tint = np.stack([np.clip(r * 1.15 + 0.04, 0.0, 1.0), np.clip(g * 1.10 + 0.02, 0.0, 1.0), np.clip(b * 0.92, 0.0, 1.0)], axis=-1)
    rgb_out = rgb * (1.0 - gold_score[:, :, None] * 0.65) + gold_tint * (gold_score[:, :, None] * 0.65)
    bc_u8 = np.dstack([np.round(rgb_out * 255.0).astype(np.uint8), np.full(r.shape, 255, dtype=np.uint8)])

    # Downsample to 1024x1024 for crisp, compact MetallicRoughness & Emissive maps
    im_1k = Image.fromarray(bc_u8, "RGBA").resize((1024, 1024), Image.Resampling.BILINEAR)
    c1k = np.asarray(im_1k, dtype=np.float32)[:, :, :3] / 255.0
    r1, g1, b1 = c1k[:, :, 0], c1k[:, :, 1], c1k[:, :, 2]

    g_score_1k = np.clip(((r1 - b1) - 0.11) / 0.16, 0.0, 1.0) * np.clip(((g1 - b1) - 0.03) / 0.12, 0.0, 1.0) * np.clip((r1 - 0.32) / 0.20, 0.0, 1.0)
    chroma_1k = np.maximum(np.maximum(r1, g1), b1) - np.minimum(np.minimum(r1, g1), b1)

    # glTF metallicRoughness: R = AO (1.0), G = Roughness, B = Metallic
    metallic = 0.04 + 0.82 * g_score_1k  # up to 0.86 on 24k gold filigree, 0.04 on dielectric jade/crystal
    # Glazed turquoise tiles, crystal gems & stained glass get glossy roughness ~0.16-0.22; carved white jade ~0.28; gold ~0.23
    roughness = 0.30 - 0.12 * np.clip(chroma_1k / 0.35, 0.0, 1.0)
    roughness = roughness * (1.0 - g_score_1k) + 0.23 * g_score_1k
    if is_stained_glass_leaf:
        roughness = roughness * (1.0 - (1.0 - g_score_1k) * 0.35)  # extra glossy ~0.16 on stained glass panels!

    mr_u8 = np.dstack(
        [
            np.full(r1.shape, 255, dtype=np.uint8),
            np.round(np.clip(roughness, 0.12, 0.85) * 255.0).astype(np.uint8),
            np.round(np.clip(metallic, 0.0, 1.0) * 255.0).astype(np.uint8),
        ]
    )

    # Selective Celestial Emissive Map:
    # 1) Warm glowing lantern cores (very bright warm yellow-white)
    lantern_mask = np.clip((r1 - 0.80) / 0.16, 0.0, 1.0) * np.clip((g1 - 0.68) / 0.20, 0.0, 1.0) * np.clip((r1 - b1 - 0.08) / 0.22, 0.0, 1.0)
    # 2) Cyan/Turquoise crystal lotus & star gems
    cyan_mask = np.clip((g1 - r1 - 0.05) / 0.18, 0.0, 1.0) * np.clip((b1 - r1 - 0.02) / 0.18, 0.0, 1.0) * np.clip((np.maximum(g1, b1) - 0.48) / 0.28, 0.0, 1.0)
    # 3) Sakura-pink / magenta / amethyst crystal gems & blossoms
    pink_mask = np.clip((r1 - g1 - 0.08) / 0.18, 0.0, 1.0) * np.clip((b1 - g1 + 0.02) / 0.18, 0.0, 1.0) * np.clip((r1 - 0.52) / 0.28, 0.0, 1.0)

    em = (
        lantern_mask[:, :, None] * np.array([0.62, 0.46, 0.18], dtype=np.float32)
        + cyan_mask[:, :, None] * np.array([0.10, 0.44, 0.52], dtype=np.float32)
        + pink_mask[:, :, None] * np.array([0.42, 0.16, 0.36], dtype=np.float32)
    )
    if is_stained_glass_leaf:
        glass_mask = (1.0 - g_score_1k)[:, :, None]
        em = np.maximum(em, c1k * glass_mask * 0.28)

    em_u8 = np.round(np.clip(em, 0.0, 1.0) * 255.0).astype(np.uint8)

    def to_png_bytes(arr_u8: np.ndarray, mode: str) -> bytes:
        buf = io.BytesIO()
        Image.fromarray(arr_u8, mode).save(buf, format="PNG", optimize=False)
        return buf.getvalue()

    res = (to_png_bytes(bc_u8, "RGBA"), to_png_bytes(mr_u8, "RGB"), to_png_bytes(em_u8, "RGB"))
    _PBR_CACHE[cache_key] = res
    return res


def write_clean_single_mesh_glb(dst: Path, mesh_name: str, geom: dict) -> dict:
    """Write a clean single-node, single-mesh GLB with upgraded 24k Gold / Jade / Crystal PBR textures."""
    orig_doc = geom["doc"]
    orig_bin = geom["bin"]
    sub_doc = json.loads(json.dumps(orig_doc))

    new_bin = bytearray()
    new_bvs = []
    new_accs = []

    is_leaf = mesh_name in ("Gate_Leaf_L", "Gate_Leaf_R")
    bc_bytes, mr_bytes, em_bytes = build_imperial_pbr_maps(orig_doc, orig_bin, is_leaf)

    def add_image_bytes(png_bytes: bytes) -> int:
        start = len(new_bin)
        new_bin.extend(png_bytes)
        new_bin.extend(b"\x00" * ((4 - (len(new_bin) % 4)) % 4))
        bv_idx = len(new_bvs)
        new_bvs.append({"buffer": 0, "byteOffset": start, "byteLength": len(png_bytes)})
        return bv_idx

    bc_bv = add_image_bytes(bc_bytes)
    mr_bv = add_image_bytes(mr_bytes)
    em_bv = add_image_bytes(em_bytes)

    sub_doc["images"] = [
        {"bufferView": bc_bv, "mimeType": "image/png", "name": f"{mesh_name}_BaseColor"},
        {"bufferView": mr_bv, "mimeType": "image/png", "name": f"{mesh_name}_MetallicRoughness"},
        {"bufferView": em_bv, "mimeType": "image/png", "name": f"{mesh_name}_Emissive"},
    ]
    sampler0 = sub_doc.get("samplers", [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}])[0]
    sub_doc["samplers"] = [sampler0]
    sub_doc["textures"] = [
        {"sampler": 0, "source": 0},
        {"sampler": 0, "source": 1},
        {"sampler": 0, "source": 2},
    ]

    def add_arr(arr: np.ndarray, target: int, acc_type: str, comp_type: int, minmax: bool = False) -> int:
        raw = arr.tobytes()
        start = len(new_bin)
        new_bin.extend(raw)
        new_bin.extend(b"\x00" * ((4 - (len(new_bin) % 4)) % 4))
        bv_idx = len(new_bvs)
        new_bvs.append({"buffer": 0, "byteOffset": start, "byteLength": len(raw), "target": target})
        acc = {
            "bufferView": bv_idx,
            "byteOffset": 0,
            "componentType": comp_type,
            "count": len(arr),
            "type": acc_type,
        }
        if minmax:
            acc["min"] = arr.min(axis=0).tolist()
            acc["max"] = arr.max(axis=0).tolist()
        idx = len(new_accs)
        new_accs.append(acc)
        return idx

    p_f32 = geom["pos"].astype(np.float32)
    n_f32 = geom["norm"].astype(np.float32)
    u_f32 = geom["uv"].astype(np.float32)
    t_u32 = geom["tris"].reshape(-1).astype(np.uint32)

    pos_idx = add_arr(p_f32, 34962, "VEC3", 5126, minmax=True)
    nrm_idx = add_arr(n_f32, 34962, "VEC3", 5126, minmax=False)
    uv_idx = add_arr(u_f32, 34962, "VEC2", 5126, minmax=False)
    ind_idx = add_arr(t_u32, 34963, "SCALAR", 5125, minmax=False)

    sub_doc["bufferViews"] = new_bvs
    sub_doc["accessors"] = new_accs
    sub_doc["buffers"] = [{"byteLength": len(new_bin)}]
    prim_def = {"attributes": {"POSITION": pos_idx, "NORMAL": nrm_idx, "TEXCOORD_0": uv_idx}, "indices": ind_idx, "material": 0}
    sub_doc["materials"] = [
        {
            "name": f"M_{mesh_name}",
            "doubleSided": True,
            "alphaMode": "OPAQUE",
            "pbrMetallicRoughness": {
                "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
                "metallicFactor": 1.0,
                "roughnessFactor": 1.0,
                "baseColorTexture": {"index": 0, "texCoord": 0},
                "metallicRoughnessTexture": {"index": 1, "texCoord": 0},
            },
            "emissiveTexture": {"index": 2, "texCoord": 0},
            "emissiveFactor": [1.0, 1.0, 1.0],
        }
    ]
    sub_doc.pop("extensionsUsed", None)
    sub_doc.pop("extensionsRequired", None)
    sub_doc["meshes"] = [{"name": mesh_name, "primitives": [prim_def]}]
    sub_doc["nodes"] = [{"name": mesh_name, "mesh": 0}]
    sub_doc["scenes"] = [{"nodes": [0]}]
    sub_doc["scene"] = 0
    sub_doc.pop("animations", None)
    sub_doc.pop("skins", None)

    save_glb(dst, sub_doc, bytes(new_bin))
    bmin = p_f32.min(axis=0)
    bmax = p_f32.max(axis=0)
    size = bmax - bmin
    center = 0.5 * (bmin + bmax)
    return {
        "verts": int(len(p_f32)),
        "tris": int(len(geom["tris"])),
        "gltf_m": {
            "min": [round(float(x), 5) for x in bmin],
            "max": [round(float(x), 5) for x in bmax],
            "size": [round(float(x), 5) for x in size],
            "center": [round(float(x), 5) for x in center],
        },
        "ue_cm": {
            "min": [round(float(bmin[0] * 100), 3), round(float(bmin[2] * 100), 3), round(float(bmin[1] * 100), 3)],
            "max": [round(float(bmax[0] * 100), 3), round(float(bmax[2] * 100), 3), round(float(bmax[1] * 100), 3)],
            "size": [round(float(size[0] * 100), 3), round(float(size[2] * 100), 3), round(float(size[1] * 100), 3)],
            "center": [round(float(center[0] * 100), 3), round(float(center[2] * 100), 3), round(float(center[1] * 100), 3)],
        },
    }


def gltf_to_ue_cm(xyz_gltf: np.ndarray | list[float]) -> list[float]:
    return [round(float(xyz_gltf[0] * 100.0), 3), round(float(xyz_gltf[2] * 100.0), 3), round(float(xyz_gltf[1] * 100.0), 3)]


def parse_urdf_articulation(zip_path: Path, extract_dir: Path) -> dict:
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    urdf_files = list(extract_dir.rglob("*.urdf"))
    if not urdf_files:
        raise FileNotFoundError(f"No .urdf found in {zip_path}")
    urdf_path = urdf_files[0]
    urdf_dir = urdf_path.parent
    tree = ET.parse(urdf_path)
    root = tree.getroot()

    links = {}
    for lk in root.findall("link"):
        lname = lk.attrib["name"]
        mesh_el = lk.find(".//visual/geometry/mesh")
        vis_orig_el = lk.find(".//visual/origin")
        vis_xyz = [float(x) for x in vis_orig_el.attrib.get("xyz", "0 0 0").split()] if vis_orig_el is not None else [0.0, 0.0, 0.0]
        if mesh_el is not None:
            mpath = urdf_dir / mesh_el.attrib["filename"]
            geom = extract_baked_geometry(mpath)
            if any(abs(v) > 1e-8 for v in vis_xyz):
                geom["pos"] += np.array(vis_xyz, dtype=np.float64)
            links[lname] = {"mesh_path": str(mpath), "geom": geom}

    joints = []
    for jt in root.findall("joint"):
        jname = jt.attrib["name"]
        jtype = jt.attrib.get("type", "fixed")
        parent = jt.find("parent").attrib["link"]
        child = jt.find("child").attrib["link"]
        orig_el = jt.find("origin")
        xyz = np.array([float(x) for x in orig_el.attrib.get("xyz", "0 0 0").split()], dtype=np.float64) if orig_el is not None else np.zeros(3)
        axis_el = jt.find("axis")
        axis = np.array([float(x) for x in axis_el.attrib.get("xyz", "0 1 0").split()], dtype=np.float64) if axis_el is not None else np.array([0.0, 1.0, 0.0])
        lim_el = jt.find("limit")
        limits = (
            [float(lim_el.attrib.get("lower", "0")), float(lim_el.attrib.get("upper", "0"))]
            if lim_el is not None
            else [0.0, 0.0]
        )
        joints.append({"name": jname, "type": jtype, "parent": parent, "child": child, "xyz": xyz, "axis": axis, "limits": limits})

    # Dynamically find root link (e.g. "base" or "body") that is never a child of any joint
    child_set = {jt["child"] for jt in joints}
    root_cands = [lname for lname in links if lname not in child_set]
    root_link = root_cands[0] if root_cands else next(iter(links))

    # Compute world offset of every link relative to root_link
    world_offsets = {root_link: np.zeros(3, dtype=np.float64)}
    changed = True
    while changed:
        changed = False
        for jt in joints:
            if jt["parent"] in world_offsets and jt["child"] not in world_offsets:
                world_offsets[jt["child"]] = world_offsets[jt["parent"]] + jt["xyz"]
                changed = True

    return {"urdf_path": str(urdf_path), "root_link": root_link, "links": links, "joints": joints, "world_offsets": world_offsets}


def prepare_g01(zip_path: Path, extract_dir: Path, target_height_m: float = 2.65, flip_y180: bool = False) -> dict:
    parsed = parse_urdf_articulation(zip_path, extract_dir)
    links = parsed["links"]
    joints = parsed["joints"]
    woff = parsed["world_offsets"]

    # Calculate overall assembly X/Y bounds to identify the two central doors vs any peripheral links (e.g. lanterns)
    all_pts = np.vstack([links[lname]["geom"]["pos"] + woff.get(lname, np.zeros(3)) for lname in links])
    asm_min, asm_max = all_pts.min(axis=0), all_pts.max(axis=0)
    asm_w = asm_max[0] - asm_min[0]
    asm_cx = 0.5 * (asm_min[0] + asm_max[0])

    # Score candidate child links for left/right central swinging doors
    candidates = []
    for jt in joints:
        ch = jt["child"]
        if ch not in links:
            continue
        g = links[ch]["geom"]
        pts_w = g["pos"] + woff[ch]
        c_min, c_max = pts_w.min(axis=0), pts_w.max(axis=0)
        c_center = 0.5 * (c_min + c_max)
        height = c_max[1] - c_min[1]
        # Central portal doors sit within central 55% width and have substantial vertical span
        is_central = abs(c_center[0] - asm_cx) < 0.35 * asm_w
        candidates.append((is_central, height, len(g["tris"]), jt, ch, c_center))

    door_cands = [c for c in candidates if c[0]]
    if len(door_cands) < 2:
        door_cands = sorted(candidates, key=lambda x: (x[1], x[2]), reverse=True)[:2]
    else:
        door_cands = sorted(door_cands, key=lambda x: (x[1], x[2]), reverse=True)[:2]

    if len(door_cands) < 2:
        raise RuntimeError(f"G01 URDF only yielded {len(door_cands)} movable links; need 2 doors! Joints={joints}")

    # Optional 180-deg flip around Y_gltf if needed
    def maybe_flip_geom(g: dict) -> None:
        if flip_y180:
            g["pos"][:, 0] *= -1.0
            g["pos"][:, 2] *= -1.0
            g["norm"][:, 0] *= -1.0
            g["norm"][:, 2] *= -1.0

    root_link = parsed["root_link"]
    chosen_children = {door_cands[0][4], door_cands[1][4]}
    # Merge root_link + any non-door links (such as articulated lanterns if any) into Gate_Frame
    base_parts = [(links[root_link]["geom"], np.zeros(3))]
    for lname, linfo in links.items():
        if lname != root_link and lname not in chosen_children:
            print(f"[G01] Merging auxiliary link '{lname}' into Gate_Frame")
            base_parts.append((linfo["geom"], woff[lname]))
    frame_geom = merge_geometries(base_parts)

    d0_jt, d0_name = door_cands[0][3], door_cands[0][4]
    d1_jt, d1_name = door_cands[1][3], door_cands[1][4]
    d0_geom = links[d0_name]["geom"]
    d1_geom = links[d1_name]["geom"]
    d0_hinge = woff[d0_name].copy()
    d1_hinge = woff[d1_name].copy()

    if flip_y180:
        maybe_flip_geom(frame_geom)
        maybe_flip_geom(d0_geom)
        maybe_flip_geom(d1_geom)
        d0_hinge[0] *= -1.0
        d0_hinge[2] *= -1.0
        d1_hinge[0] *= -1.0
        d1_hinge[2] *= -1.0

    # Assign Left (-X_gltf) vs Right (+X_gltf) strictly by hinge X coordinate!
    if d0_hinge[0] < d1_hinge[0]:
        left_geom, left_hinge, left_orig_name = d0_geom, d0_hinge, d0_name
        right_geom, right_hinge, right_orig_name = d1_geom, d1_hinge, d1_name
    else:
        left_geom, left_hinge, left_orig_name = d1_geom, d1_hinge, d1_name
        right_geom, right_hinge, right_orig_name = d0_geom, d0_hinge, d0_name

    # Normalize assembly: X centered at 0, min Y_gltf = 0.0, Z centered around +0.12m, height = target_height_m
    f_min = frame_geom["pos"].min(axis=0)
    f_max = frame_geom["pos"].max(axis=0)
    raw_h = float(f_max[1] - f_min[1])
    scale = target_height_m / max(raw_h, 1e-4)
    shift = np.array([-0.5 * (f_min[0] + f_max[0]), -f_min[1], -0.5 * (f_min[2] + f_max[2]) + (0.12 / scale)], dtype=np.float64)

    frame_geom["pos"] = (frame_geom["pos"] + shift) * scale
    left_geom["pos"] = left_geom["pos"] * scale
    right_geom["pos"] = right_geom["pos"] * scale
    left_hinge_norm = (left_hinge + shift) * scale
    right_hinge_norm = (right_hinge + shift) * scale

    # Compute exact PortalCenter from the union of both closed doors in normalized frame!
    doors_world = np.vstack([left_geom["pos"] + left_hinge_norm, right_geom["pos"] + right_hinge_norm])
    portal_center_gltf = 0.5 * (doors_world.min(axis=0) + doors_world.max(axis=0))
    portal_center_gltf[0] = 0.0  # Keep X=0 exact symmetry

    b_frame = write_clean_single_mesh_glb(READY_DIR / "Gate_Frame.glb", "Gate_Frame", frame_geom)
    b_left = write_clean_single_mesh_glb(READY_DIR / "Gate_Leaf_L.glb", "Gate_Leaf_L", left_geom)
    b_right = write_clean_single_mesh_glb(READY_DIR / "Gate_Leaf_R.glb", "Gate_Leaf_R", right_geom)

    return {
        "urdf_path": parsed["urdf_path"],
        "selected_links": {"left": left_orig_name, "right": right_orig_name},
        "normalization_scale": round(scale, 6),
        "hinges_gltf_m": {
            "left_hinge": [round(float(x), 5) for x in left_hinge_norm],
            "right_hinge": [round(float(x), 5) for x in right_hinge_norm],
            "portal_center": [round(float(x), 5) for x in portal_center_gltf],
        },
        "ue_offsets_cm": {
            "LeftHingeLocalOffset": gltf_to_ue_cm(left_hinge_norm),
            "RightHingeLocalOffset": gltf_to_ue_cm(right_hinge_norm),
            "PortalCenterLocalOffset": gltf_to_ue_cm(portal_center_gltf),
        },
        "ready_bounds_gltf_m": {
            "Gate_Frame": b_frame["gltf_m"],
            "Gate_Leaf_L": b_left["gltf_m"],
            "Gate_Leaf_R": b_right["gltf_m"],
        },
        "ready_bounds_ue_cm": {
            "Gate_Frame": b_frame["ue_cm"],
            "Gate_Leaf_L": b_left["ue_cm"],
            "Gate_Leaf_R": b_right["ue_cm"],
        },
        "mesh_counts": {
            "Gate_Frame": {"verts": b_frame["verts"], "tris": b_frame["tris"]},
            "Gate_Leaf_L": {"verts": b_left["verts"], "tris": b_left["tris"]},
            "Gate_Leaf_R": {"verts": b_right["verts"], "tris": b_right["tris"]},
        },
    }


def prepare_g03(zip_path: Path, extract_dir: Path, target_height_m: float = 0.50, flip_y180: bool = False) -> dict:
    parsed = parse_urdf_articulation(zip_path, extract_dir)
    links = parsed["links"]
    joints = parsed["joints"]
    woff = parsed["world_offsets"]

    # Pick central concentric inner_ring link
    ring_cands = []
    for jt in joints:
        ch = jt["child"]
        if ch in links:
            g = links[ch]["geom"]
            ring_cands.append((len(g["tris"]), jt, ch))
    if not ring_cands:
        raise RuntimeError(f"G03 URDF yielded no movable inner ring link! Joints={joints}")
    ring_cands.sort(key=lambda x: x[0], reverse=True)
    _, inner_jt, inner_name = ring_cands[0]

    root_link = parsed["root_link"]
    base_parts = [(links[root_link]["geom"], np.zeros(3))]
    for lname, linfo in links.items():
        if lname != root_link and lname != inner_name:
            print(f"[G03] Merging auxiliary link '{lname}' into StarGate_OuterRing")
            base_parts.append((linfo["geom"], woff[lname]))
    outer_geom = merge_geometries(base_parts)
    inner_geom = links[inner_name]["geom"]
    inner_hinge = woff[inner_name].copy()

    if flip_y180:
        for g in (outer_geom, inner_geom):
            g["pos"][:, 0] *= -1.0
            g["pos"][:, 2] *= -1.0
            g["norm"][:, 0] *= -1.0
            g["norm"][:, 2] *= -1.0
        inner_hinge[0] *= -1.0
        inner_hinge[2] *= -1.0

    # Ensure concentric ring rotation pivot sits strictly at the circular bore center (zero wobble on 360-deg spin!)
    r_est = np.sqrt(inner_geom["pos"][:, 0] ** 2 + inner_geom["pos"][:, 1] ** 2)
    bore_rim = inner_geom["pos"][r_est <= np.percentile(r_est, 20)]
    inner_local_center = np.array(
        [
            0.5 * (bore_rim[:, 0].min() + bore_rim[:, 0].max()),
            0.5 * (bore_rim[:, 1].min() + bore_rim[:, 1].max()),
            0.5 * (inner_geom["pos"][:, 2].min() + inner_geom["pos"][:, 2].max()),
        ],
        dtype=np.float64,
    )
    inner_geom["pos"] -= inner_local_center
    inner_hinge += inner_local_center
    # Enforce exact X=0 bilateral symmetry on inner_hinge after centering outer_geom


    o_min = outer_geom["pos"].min(axis=0)
    o_max = outer_geom["pos"].max(axis=0)
    raw_h = float(o_max[1] - o_min[1])
    scale = target_height_m / max(raw_h, 1e-4)
    shift = np.array([-0.5 * (o_min[0] + o_max[0]), -o_min[1], -0.5 * (o_min[2] + o_max[2])], dtype=np.float64)

    outer_geom["pos"] = (outer_geom["pos"] + shift) * scale
    inner_geom["pos"] = inner_geom["pos"] * scale
    inner_hinge_norm = (inner_hinge + shift) * scale

    # Verify hollow bore radius on StarGate_InnerRing!
    r_xy_inner = np.sqrt(inner_geom["pos"][:, 0] ** 2 + inner_geom["pos"][:, 1] ** 2)
    min_bore_r_m = float(r_xy_inner.min())
    max_ring_r_m = float(r_xy_inner.max())

    b_outer = write_clean_single_mesh_glb(READY_DIR / "StarGate_OuterRing.glb", "StarGate_OuterRing", outer_geom)
    b_inner = write_clean_single_mesh_glb(READY_DIR / "StarGate_InnerRing.glb", "StarGate_InnerRing", inner_geom)

    return {
        "urdf_path": parsed["urdf_path"],
        "selected_inner_link": inner_name,
        "normalization_scale": round(scale, 6),
        "inner_ring_hollow_bore_check_m": {
            "inner_bore_radius_m": round(min_bore_r_m, 5),
            "outer_ring_radius_m": round(max_ring_r_m, 5),
            "bore_to_outer_ratio": round(min_bore_r_m / max(max_ring_r_m, 1e-6), 4),
        },
        "hinges_gltf_m": {
            "inner_ring_hinge": [round(float(x), 5) for x in inner_hinge_norm],
            "portal_center": [round(float(x), 5) for x in inner_hinge_norm],
        },
        "ue_offsets_cm": {
            "InnerRingLocalOffset": gltf_to_ue_cm(inner_hinge_norm),
            "PortalCenterLocalOffset": gltf_to_ue_cm(inner_hinge_norm),
        },
        "ready_bounds_gltf_m": {
            "StarGate_OuterRing": b_outer["gltf_m"],
            "StarGate_InnerRing": b_inner["gltf_m"],
        },
        "ready_bounds_ue_cm": {
            "StarGate_OuterRing": b_outer["ue_cm"],
            "StarGate_InnerRing": b_inner["ue_cm"],
        },
        "mesh_counts": {
            "StarGate_OuterRing": {"verts": b_outer["verts"], "tris": b_outer["tris"]},
            "StarGate_InnerRing": {"verts": b_inner["verts"], "tris": b_inner["tris"]},
        },
    }


def prepare_t01(glb_path: Path, target_outer_radius_m: float = 0.09) -> dict:
    geom = extract_baked_geometry(glb_path)
    pos = geom["pos"]
    nrm = geom["norm"]

    # Ensure the thin dimension of the ring is along Z_gltf so the ring lies in glTF X-Y plane (UE X-Z plane, bore along Y_ue)!
    extents = pos.max(axis=0) - pos.min(axis=0)
    thin_axis = int(np.argmin(extents))
    if thin_axis == 1:
        # Thin along Y -> rotate +90 deg around X: (x, y, z) -> (x, -z, y)
        pos = np.column_stack([pos[:, 0], -pos[:, 2], pos[:, 1]])
        nrm = np.column_stack([nrm[:, 0], -nrm[:, 2], nrm[:, 1]])
    elif thin_axis == 0:
        # Thin along X -> rotate +90 deg around Y: (x, y, z) -> (z, y, -x)
        pos = np.column_stack([pos[:, 2], pos[:, 1], -pos[:, 0]])
        nrm = np.column_stack([nrm[:, 2], nrm[:, 1], -nrm[:, 0]])

    # Center at origin (0, 0, 0)
    center = 0.5 * (pos.min(axis=0) + pos.max(axis=0))
    pos = pos - center

    # Normalize outer radius in X-Y to target_outer_radius_m (0.09m -> 0.18m diameter matching V1 Tunnel_Ring!)
    cur_radius = float(max(pos[:, 0].max() - pos[:, 0].min(), pos[:, 1].max() - pos[:, 1].min()) * 0.5)
    scale = target_outer_radius_m / max(cur_radius, 1e-5)
    pos = pos * scale
    geom["pos"] = pos
    geom["norm"] = nrm

    r_xy = np.sqrt(pos[:, 0] ** 2 + pos[:, 1] ** 2)
    min_bore_r = float(r_xy.min())
    max_outer_r = float(r_xy.max())

    b_ring = write_clean_single_mesh_glb(READY_DIR / "Tunnel_Ring.glb", "Tunnel_Ring", geom)
    return {
        "thin_axis_raw": thin_axis,
        "normalization_scale": round(scale, 6),
        "hollow_bore_check_m": {
            "inner_bore_radius_m": round(min_bore_r, 5),
            "outer_ring_radius_m": round(max_outer_r, 5),
            "bore_to_outer_ratio": round(min_bore_r / max(max_outer_r, 1e-6), 4),
            "is_cleanly_hollow": bool(min_bore_r > 0.28 * max_outer_r),
        },
        "ready_bounds_gltf_m": {"Tunnel_Ring": b_ring["gltf_m"]},
        "ready_bounds_ue_cm": {"Tunnel_Ring": b_ring["ue_cm"]},
        "mesh_counts": {"Tunnel_Ring": {"verts": b_ring["verts"], "tris": b_ring["tris"]}},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--config",
        type=str,
        default=str(V2_ROOT / "v2_gates_build_config.json"),
        help="JSON file specifying raw file paths and taskIds",
    )
    ap.add_argument("--flip-g01", action="store_true", help="Rotate G01 180 deg around Y_gltf so hero front faces -Z_gltf (-Y_ue)")
    ap.add_argument("--flip-g03", action="store_true", help="Rotate G03 180 deg around Y_gltf so hero front faces -Z_gltf (-Y_ue)")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    for tid in cfg.get("all_task_ids", []):
        if int(tid) in FORBIDDEN_TASK_IDS:
            raise ValueError(f"Isolation violation: forbidden taskId {tid} found!")

    READY_DIR.mkdir(parents=True, exist_ok=True)

    g01_zip = Path(cfg["g01_articulation_zip"])
    g01_ext = V2_ROOT / f"G01_Articulation_{cfg['g01_articulation_task_id']}"
    g01_info = prepare_g01(g01_zip, g01_ext, target_height_m=cfg.get("g01_height_m", 2.65), flip_y180=args.flip_g01)

    g03_zip = Path(cfg["g03_articulation_zip"])
    g03_ext = V2_ROOT / f"G03_Articulation_{cfg['g03_articulation_task_id']}"
    g03_info = prepare_g03(g03_zip, g03_ext, target_height_m=cfg.get("g03_height_m", 0.50), flip_y180=args.flip_g03)

    t01_glb = Path(cfg["t01_raw_glb"])
    t01_info = prepare_t01(t01_glb, target_outer_radius_m=cfg.get("t01_outer_radius_m", 0.09))

    ready_files = [
        "Gate_Frame.glb",
        "Gate_Leaf_L.glb",
        "Gate_Leaf_R.glb",
        "StarGate_OuterRing.glb",
        "StarGate_InnerRing.glb",
        "Tunnel_Ring.glb",
    ]
    hashes = {f"Ready/{fn}": sha256_file(READY_DIR / fn) for fn in ready_files}
    for key in ("g01_raw_glb", "g01_articulation_zip", "g03_raw_glb", "g03_articulation_zip", "t01_raw_glb"):
        if key in cfg and Path(cfg[key]).is_file():
            p = Path(cfg[key])
            hashes[f"raw/{p.name}"] = sha256_file(p)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": "ButterflyDream (庄周梦蝶) — V2_Gates",
        "isolation_verified": {
            "forbidden_task_ids_untouched": sorted(FORBIDDEN_TASK_IDS),
            "v2_gates_task_ids": cfg["all_task_ids"],
            "overlap_count": 0,
        },
        "ue_coordinate_mapping": "X_ue = 100 * X_gltf, Y_ue = 100 * Z_gltf, Z_ue = 100 * Y_gltf",
        "ue_gate_hinge_configuration": {
            "G01_SakuraDreamGate": g01_info["ue_offsets_cm"],
            "G03_StarRingGate": g03_info["ue_offsets_cm"],
        },
        "assets": {
            "G01_ImperialSakuraGate": {
                "title": "九重飞檐鎏金樱云牌坊仙门 (Articulated Double-Leaf Archway)",
                "version": "G1",
                "faceCount": 300000,
                "taskIds": cfg["g01_task_ids"],
                **g01_info,
            },
            "G03_ImperialAstrolabeGate": {
                "title": "浑天星轨鎏金神环门 (Articulated Concentric Celestial Armillary Portal)",
                "version": "G1",
                "faceCount": 300000,
                "taskIds": cfg["g03_task_ids"],
                **g03_info,
            },
            "T01_FiligreeStarRing": {
                "title": "中空鎏金星轨法阵环 (Hollow Filigree Vortex Ring)",
                "version": "G1",
                "faceCount": 250000,
                "taskIds": cfg["t01_task_ids"],
                **t01_info,
            },
        },
        "hashes": hashes,
    }

    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote V2_Gates manifest to {MANIFEST_PATH}")
    print("G01 UE Offsets (cm):", json.dumps(g01_info["ue_offsets_cm"]))
    print("G03 UE Offsets (cm):", json.dumps(g03_info["ue_offsets_cm"]))
    print("T01 Hollow Bore Check:", json.dumps(t01_info["hollow_bore_check_m"]))


if __name__ == "__main__":
    main()
