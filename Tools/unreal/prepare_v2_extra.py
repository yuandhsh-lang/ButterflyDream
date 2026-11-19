"""Normalize, clean, verify, measure portal bores, and preview V2_Extra Lux3D G1 assets for UE 5.8.

Owned / target paths:
  - E:\\紫萱2版\\Tools\\unreal\\prepare_v2_extra.py
  - E:\\紫萱2版\\Assets\\LuxGenerated\\V2_Extra\\Ready\\<MeshName>.glb (10 assets)
  - E:\\紫萱2版\\Assets\\LuxGenerated\\V2_Extra\\previews\\<AssetId>_<MeshName>_preview.png
  - E:\\紫萱2版\\Assets\\LuxGenerated\\V2_Extra\\previews\\V2_Extra_Overview.png
  - E:\\紫萱2版\\Assets\\LuxGenerated\\V2_Extra\\manifest.json

Alignment rules:
  - Buildings & Portals (1..4, 6..8): XZ centered at (0, 0), base aligned to min_y = 0.0 (UE min_z = 0.0)
  - Floating Sphere & Dynamic Particle Meshes (5, 9, 10): XYZ geometric center aligned to (0, 0, 0)
"""

from __future__ import annotations

import gc
import hashlib
import io
import json
import math
import struct
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

V2_ROOT = Path(r"E:\紫萱2版\Assets\LuxGenerated\V2_Extra")
RAW_DIR = V2_ROOT / "raw"
READY_DIR = V2_ROOT / "Ready"
PREVIEWS_DIR = V2_ROOT / "previews"
MANIFEST_JSON = V2_ROOT / "manifest.json"

FORBIDDEN_TASK_IDS = {7997862, 7997813, 7636420, 7636417, 7636414, 7636411, 7636404}

# (asset_id, mesh_name, task_id, requested_faces, alignment_mode, is_portal, target_scene, source_url, description)
ASSET_TABLE = [
    (
        "S03_InkCloudMountainComplex",
        "Ink_Cloud_Mountain_Complex",
        8287154,
        300000,
        "ground_xz_center",
        False,
        "Lux_InkCloudDream",
        "https://qhsmodel.kujiale.com/lux3dPbrEmbedResult/2e34298c0fc04faa9e4ba1cd507de03c/textured.glb",
        "Floating Chinese ink-wash mountain sanctuary complex with gilded flying-eave cliff pavilions and jade spirit veins",
    ),
    (
        "S03_LuminousGuqinBridge",
        "Luminous_Guqin_Bridge",
        8287159,
        300000,
        "ground_xz_center",
        False,
        "Lux_InkCloudDream",
        "https://qhsmodel.kujiale.com/lux3dPbrEmbedResult/11c33f1ac9ee4a4aae52acfa8b644ed2/textured.glb",
        "Colossal celestial arch bridge sculpted as a seven-string Chinese Guqin zither with glowing strings",
    ),
    (
        "S04_SevenTierCrystalPagoda",
        "Seven_Tier_Crystal_Pagoda",
        8287165,
        300000,
        "ground_xz_center",
        False,
        "Lux_CrystalMirageDream",
        "https://qhsmodel.kujiale.com/lux3dPbrEmbedResult/5cd11fb8dfd54f7cb7020fb2c95e5dba/textured.glb",
        "Seven-tiered rainbow translucent glazed crystal pagoda (Liuli Baota) with gold filigree eaves",
    ),
    (
        "S04_FloatingCrystalGarden",
        "Floating_Crystal_Garden",
        8287171,
        300000,
        "ground_xz_center",
        False,
        "Lux_CrystalMirageDream",
        "https://qhsmodel.kujiale.com/lux3dPbrEmbedResult/405064166de2480098fba066a0518831/textured.glb",
        "Floating crystal sky-garden island with crystalline blossom tree, stained-glass lotuses, and quartz clusters",
    ),
    (
        "S05_TaijiStarSphere",
        "Taiji_Star_Sphere",
        8287176,
        300000,
        "origin_xyz_center",
        False,
        "Lux_TaijiAwakeningDream",
        "https://qhsmodel.kujiale.com/lux3dPbrEmbedResult/09a141aa756b4711b538ea1e04996472/textured.glb",
        "Cosmic Yin-Yang Taiji sphere encircled by gilded Bagua armillary rings and crystal stars",
    ),
    (
        "S05_CelestialScrollGate",
        "Celestial_Scroll_Gate",
        8287966,
        300000,
        "ground_xz_center",
        True,
        "Lux_TaijiAwakeningDream",
        "https://qhsmodel.kujiale.com/lux3dPbrEmbedResult/f0e5fdee0d484768858da873be26b082/textured.glb",
        "Sky-piercing ultimate portal gate formed by unfurling gilded calligraphy scrolls and jade cloud base",
    ),
    (
        "P03_InkRipplePortal",
        "Ink_Ripple_Portal",
        8287975,
        300000,
        "ground_xz_center",
        True,
        "Lux_InkCloudDream",
        "https://qhsmodel.kujiale.com/lux3dPbrEmbedResult/f15337fa285341aa8bcd32c55aada1d3/textured.glb",
        "Circular sumi-ink wave & kintsugi-gold ripple portal rising from a carved lotus ink-stone basin",
    ),
    (
        "P04_CrystalPrismPortal",
        "Crystal_Prism_Portal",
        8287986,
        300000,
        "ground_xz_center",
        True,
        "Lux_CrystalMirageDream",
        "https://qhsmodel.kujiale.com/lux3dPbrEmbedResult/baf157a9b1164929825935968865ae17/textured.glb",
        "Triangular rainbow-refracting optical crystal prism portal archway with platinum-gold filigree",
    ),
    (
        "VFX01_SpiritKoi",
        "Celestial_Spirit_Koi",
        8288346,
        200000,
        "origin_xyz_center",
        False,
        "All_ParticleSwarm",
        "https://qhsmodel.kujiale.com/lux3dPbrEmbedResult/f1021a8a56d94005906c2a2992f30f11/textured.glb",
        "Luminous celestial spirit koi particle mesh with flowing golden-jade translucent fins",
    ),
    (
        "VFX02_SakuraCrystalPetalCluster",
        "Sakura_Spirit_Swirl",
        8288353,
        200000,
        "origin_xyz_center",
        False,
        "All_ParticleSwarm",
        "https://qhsmodel.kujiale.com/lux3dPbrEmbedResult/7db4f085ec09413b905df7dda9218889/textured.glb",
        "Swirling sakura crystal petals and golden silk ribbon vortex particle cluster",
    ),
]


def sha256_file(path: Path) -> dict:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return {"bytes": path.stat().st_size, "sha256": h.hexdigest()}


def load_and_verify_glb(path: Path) -> tuple[dict, bytes]:
    data = path.read_bytes()
    file_size = len(data)
    if file_size < 28:
        raise ValueError(f"Truncated GLB (<28 bytes): {path} ({file_size} bytes)")
    magic, version, total_len = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67 or version != 2:
        raise ValueError(f"Invalid GLB magic/version in {path}: magic=0x{magic:08x}, version={version}")
    if total_len != file_size:
        raise ValueError(f"Incomplete/truncated GLB in {path}: header total_len={total_len}, actual={file_size}")
    jlen, jtype = struct.unpack_from("<II", data, 12)
    if jtype != 0x4E4F534A or 20 + jlen > file_size:
        raise ValueError(f"Invalid JSON chunk in {path}")
    doc = json.loads(data[20 : 20 + jlen].decode("utf-8"))
    bin_off = 20 + jlen
    blen, btype = struct.unpack_from("<II", data, bin_off)
    if btype != 0x004E4942 or bin_off + 8 + blen > file_size:
        raise ValueError(f"Invalid/truncated BIN chunk in {path}")
    bin_chunk = data[bin_off + 8 : bin_off + 8 + blen]
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
    xx, yy, zz = x * x, y * y, z * z
    xy, xz, yz = x * y, x * z, y * z
    wx, wy, wz = w * x, w * y, w * z
    return np.array(
        [
            [1.0 - 2.0 * (yy + zz), 2.0 * (xy - wz), 2.0 * (xz + wy)],
            [2.0 * (xy + wz), 1.0 - 2.0 * (xx + zz), 2.0 * (yz - wx)],
            [2.0 * (xz - wy), 2.0 * (yz + wx), 1.0 - 2.0 * (xx + yy)],
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
    comp_map = {
        5120: np.int8,
        5121: np.uint8,
        5122: np.int16,
        5123: np.uint16,
        5125: np.uint32,
        5126: np.float32,
    }
    num_map = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
    dtype = comp_map[acc["componentType"]]
    cols = num_map[acc["type"]]
    cnt = acc["count"]
    elem_bytes = np.dtype(dtype).itemsize * cols
    stride = bv.get("byteStride", elem_bytes)
    base_off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    if stride == elem_bytes:
        arr = np.frombuffer(bin_chunk, dtype=dtype, count=cnt * cols, offset=base_off).copy()
        return arr.reshape(cnt, cols) if cols > 1 else arr
    out = np.empty((cnt, cols), dtype=dtype)
    for i in range(cnt):
        off = base_off + i * stride
        out[i] = np.frombuffer(bin_chunk, dtype=dtype, count=cols, offset=off)
    return out if cols > 1 else out[:, 0]


def strip_micro_dust_components(pos: np.ndarray, tris: np.ndarray, min_keep_tris: int = 35) -> tuple[np.ndarray, np.ndarray, int]:
    """Remove genuinely 3D-detached microscopic floating specks (< min_keep_tris).
    Welds coincident 3D positions (0.01 mm) first so UV-seam islands are never split.
    """
    n_verts = len(pos)
    n_tris = len(tris)
    if n_tris < 500:
        return np.arange(n_verts, dtype=np.int64), tris, 0

    q_pos = np.round(pos.astype(np.float64) * 100000.0).astype(np.int64)
    _, pos_id = np.unique(q_pos, axis=0, return_inverse=True)
    n_pos = int(pos_id.max()) + 1

    p_tris = pos_id[tris]
    edges_u = np.concatenate([p_tris[:, 0], p_tris[:, 1], p_tris[:, 2]])
    edges_v = np.concatenate([p_tris[:, 1], p_tris[:, 2], p_tris[:, 0]])

    parent = np.arange(n_pos, dtype=np.int64)
    while True:
        while True:
            gp = parent[parent]
            if np.array_equal(gp, parent):
                break
            parent = gp
        ru = parent[edges_u]
        rv = parent[edges_v]
        diff = ru != rv
        if not np.any(diff):
            break
        lo = np.minimum(ru[diff], rv[diff])
        hi = np.maximum(ru[diff], rv[diff])
        np.minimum.at(parent, hi, lo)

    tri_roots = parent[p_tris[:, 0]]
    uniq_roots, counts = np.unique(tri_roots, return_counts=True)
    largest = uniq_roots[np.argmax(counts)]
    keep_roots = set(uniq_roots[counts >= min_keep_tris].tolist())
    keep_roots.add(int(largest))

    keep_tri_mask = np.isin(tri_roots, list(keep_roots))
    removed_tris = int(n_tris - np.sum(keep_tri_mask))
    if removed_tris == 0:
        return np.arange(n_verts, dtype=np.int64), tris, 0

    kept_tris = tris[keep_tri_mask]
    used_verts, inv = np.unique(kept_tris.reshape(-1), return_inverse=True)
    return used_verts, inv.reshape(-1, 3).astype(np.uint32), removed_tris


def compute_smooth_normals(pos: np.ndarray, tris: np.ndarray) -> np.ndarray:
    v0 = pos[tris[:, 0]]
    v1 = pos[tris[:, 1]]
    v2 = pos[tris[:, 2]]
    fn = np.cross(v1 - v0, v2 - v0)
    vn = np.zeros_like(pos, dtype=np.float64)
    np.add.at(vn, tris[:, 0], fn)
    np.add.at(vn, tris[:, 1], fn)
    np.add.at(vn, tris[:, 2], fn)
    lengths = np.linalg.norm(vn, axis=1, keepdims=True)
    vn = np.where(lengths > 1e-12, vn / np.maximum(lengths, 1e-12), np.array([0.0, 1.0, 0.0]))
    return vn.astype(np.float32)


def measure_portal_bore(pos: np.ndarray, tris: np.ndarray) -> dict:
    """Measure exact 2D orthographic Z-ray clearance (hollow bore openness) on normalized portal geometry."""
    g = 512
    x_min, y_min, _ = pos.min(axis=0)
    x_max, y_max, _ = pos.max(axis=0)
    width_m = float(x_max - x_min)
    height_m = float(y_max - y_min)

    gx = ((pos[:, 0] - x_min) / max(width_m, 1e-6)) * (g - 1)
    gy = ((pos[:, 1] - y_min) / max(height_m, 1e-6)) * (g - 1)

    occ = np.zeros((g, g), dtype=bool)
    t0, t1, t2 = tris[:, 0], tris[:, 1], tris[:, 2]
    x0, y0 = gx[t0], gy[t0]
    x1, y1 = gx[t1], gy[t1]
    x2, y2 = gx[t2], gy[t2]

    span = np.maximum(
        np.maximum(np.maximum(x0, x1), x2) - np.minimum(np.minimum(x0, x1), x2),
        np.maximum(np.maximum(y0, y1), y2) - np.minimum(np.minimum(y0, y1), y2),
    )

    # Small triangles: dense barycentric splat
    sm = span <= 2.2
    if np.any(sm):
        si0, si1, si2 = t0[sm], t1[sm], t2[sm]
        for w0, w1, w2 in [
            (1 / 3, 1 / 3, 1 / 3),
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
            (0.5, 0.5, 0.0),
            (0.0, 0.5, 0.5),
            (0.5, 0.0, 0.5),
            (0.6, 0.2, 0.2),
            (0.2, 0.6, 0.2),
            (0.2, 0.2, 0.6),
        ]:
            ix = np.clip(np.round(w0 * gx[si0] + w1 * gx[si1] + w2 * gx[si2]).astype(np.int32), 0, g - 1)
            iy = np.clip(np.round(w0 * gy[si0] + w1 * gy[si1] + w2 * gy[si2]).astype(np.int32), 0, g - 1)
            occ[iy, ix] = True

    # Medium/large triangles: exact pixel-grid rasterization
    lg_idx = np.nonzero(~sm)[0]
    for ti in lg_idx:
        ia, ib, ic = int(t0[ti]), int(t1[ti]), int(t2[ti])
        ax, ay = float(gx[ia]), float(gy[ia])
        bx, by_p = float(gx[ib]), float(gy[ib])
        cx_t, cy_t = float(gx[ic]), float(gy[ic])
        denom = (by_p - cy_t) * (ax - cx_t) + (cx_t - bx) * (ay - cy_t)
        if abs(denom) < 1e-6:
            continue
        ix0 = max(0, int(math.floor(min(ax, bx, cx_t))))
        ix1 = min(g - 1, int(math.ceil(max(ax, bx, cx_t))))
        iy0 = max(0, int(math.floor(min(ay, by_p, cy_t))))
        iy1 = min(g - 1, int(math.ceil(max(ay, by_p, cy_t))))
        py_g, px_g = np.mgrid[iy0 : iy1 + 1, ix0 : ix1 + 1].astype(np.float32)
        inv_d = 1.0 / denom
        w0 = ((by_p - cy_t) * (px_g - cx_t) + (cx_t - bx) * (py_g - cy_t)) * inv_d
        w1 = ((cy_t - ay) * (px_g - cx_t) + (ax - cx_t) * (py_g - cy_t)) * inv_d
        w2 = 1.0 - w0 - w1
        inside = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
        occ[iy0 : iy1 + 1, ix0 : ix1 + 1] |= inside

    # Convert occupied pixels to meter coordinates
    occ_iy, occ_ix = np.nonzero(occ)
    occ_x_m = x_min + (occ_ix / (g - 1)) * width_m
    occ_y_m = y_min + (occ_iy / (g - 1)) * height_m

    # Search along centerline x=0.0, y in [0.15*H, 0.72*H] for maximum inscribed clear circle radius
    cand_ys = np.linspace(y_min + 0.15 * height_m, y_min + 0.72 * height_m, 140)
    best_r = -1.0
    best_cy = float(y_min + 0.42 * height_m)
    for cy_c in cand_ys:
        dists = np.sqrt((occ_x_m - 0.0) ** 2 + (occ_y_m - cy_c) ** 2)
        r_geom = float(dists.min()) if len(dists) > 0 else 0.0
        # Clamp by ground plane y=0 so circle stays strictly above ground threshold
        r_clear = min(r_geom, float(cy_c - y_min))
        if r_clear > best_r:
            best_r = r_clear
            best_cy = float(cy_c)

    # Measure horizontal clear span at y = best_cy
    iy_best = int(np.clip(round(((best_cy - y_min) / max(height_m, 1e-6)) * (g - 1)), 0, g - 1))
    ix_center = int(np.clip(round(((0.0 - x_min) / max(width_m, 1e-6)) * (g - 1)), 0, g - 1))
    row = occ[iy_best]
    left_ix = ix_center
    while left_ix > 0 and not row[left_ix - 1]:
        left_ix -= 1
    right_ix = ix_center
    while right_ix < g - 1 and not row[right_ix + 1]:
        right_ix += 1
    clear_span_width_m = ((right_ix - left_ix) / (g - 1)) * width_m

    # Measure vertical clear span at x = 0.0
    col = occ[:, ix_center]
    bot_iy = iy_best
    while bot_iy > 0 and not col[bot_iy - 1]:
        bot_iy -= 1
    top_iy = iy_best
    while top_iy < g - 1 and not col[top_iy + 1]:
        top_iy += 1
    clear_span_height_m = ((top_iy - bot_iy) / (g - 1)) * height_m

    # Measure unobstructed ray ratio inside central portal window around (0, best_cy)
    yy_idx, xx_idx = np.mgrid[0:g, 0:g]
    px_m = x_min + (xx_idx / (g - 1)) * width_m
    py_m = y_min + (yy_idx / (g - 1)) * height_m
    in_inscribed = ((px_m - 0.0) ** 2 + (py_m - best_cy) ** 2) <= (max(best_r * 0.92, 1e-4) ** 2)
    inscribed_open_ratio = float(1.0 - occ[in_inscribed].mean()) if np.any(in_inscribed) else 0.0

    # Central doorway window (|x| <= 0.18*W, y in [best_cy - 0.16*H, best_cy + 0.16*H])
    win_mask = (np.abs(px_m) <= 0.18 * width_m) & (np.abs(py_m - best_cy) <= 0.16 * height_m)
    central_window_open_ratio = float(1.0 - occ[win_mask].mean()) if np.any(win_mask) else 0.0

    bore_width_ratio = clear_span_width_m / max(width_m, 1e-6)
    inscribed_to_halfwidth_ratio = (2.0 * best_r) / max(width_m, 1e-6)

    return {
        "boreRatio": round(bore_width_ratio, 4),
        "inscribedDiameterToWidthRatio": round(inscribed_to_halfwidth_ratio, 4),
        "inscribedBoreRadiusM": round(best_r, 5),
        "clearSpanWidthM": round(clear_span_width_m, 5),
        "clearSpanHeightM": round(clear_span_height_m, 5),
        "centralWindowOpenRatio": round(central_window_open_ratio, 4),
        "inscribedCircleOpenRatio": round(inscribed_open_ratio, 4),
        "isCleanlyHollow": bool(bore_width_ratio >= 0.30 and inscribed_open_ratio >= 0.99),
        "portalCenterGltfM": [0.0, round(best_cy, 5), 0.0],
        "portalCenterUeCm": [0.0, 0.0, round(best_cy * 100.0, 3)],
    }


def normalize_single_glb(
    src_path: Path,
    dst_path: Path,
    mesh_name: str,
    alignment_mode: str,
    is_portal: bool,
) -> dict:
    doc, bin_chunk = load_and_verify_glb(src_path)

    nodes = doc.get("nodes", [])
    scene_idx = doc.get("scene", 0)
    root_nodes = doc.get("scenes", [{"nodes": [0]}])[scene_idx].get("nodes", [0])

    baked_parts = []

    def visit(n_idx: int, parent_mat: np.ndarray) -> None:
        node = nodes[n_idx]
        wmat = parent_mat @ node_local_matrix(node)
        if "mesh" in node:
            mesh = doc["meshes"][node["mesh"]]
            for prim in mesh.get("primitives", []):
                baked_parts.append((prim, wmat))
        for ch in node.get("children", []):
            visit(ch, wmat)

    for rn in root_nodes:
        visit(rn, np.eye(4, dtype=np.float64))

    if not baked_parts:
        for mesh in doc.get("meshes", []):
            for prim in mesh.get("primitives", []):
                baked_parts.append((prim, np.eye(4, dtype=np.float64)))

    all_pos = []
    all_norm = []
    all_uv = []
    all_tris = []
    vert_offset = 0
    has_all_uv = True

    for prim, wmat in baked_parts:
        attrs = prim["attributes"]
        pos = read_accessor_array(doc, bin_chunk, attrs["POSITION"]).astype(np.float64)
        rot_lin = wmat[:3, :3]
        trans = wmat[:3, 3]
        det = np.linalg.det(rot_lin)
        pos_w = (pos @ rot_lin.T) + trans

        if "NORMAL" in attrs:
            nrm = read_accessor_array(doc, bin_chunk, attrs["NORMAL"]).astype(np.float64)
            inv_t = np.linalg.inv(rot_lin).T if abs(det) > 1e-12 else np.eye(3)
            nrm_w = nrm @ inv_t.T
            nlen = np.linalg.norm(nrm_w, axis=1, keepdims=True)
            nrm_w = np.where(nlen > 1e-12, nrm_w / np.maximum(nlen, 1e-12), np.array([0.0, 1.0, 0.0]))
        else:
            nrm_w = None

        if "TEXCOORD_0" in attrs:
            uv = read_accessor_array(doc, bin_chunk, attrs["TEXCOORD_0"]).astype(np.float32)
        else:
            has_all_uv = False
            uv = np.zeros((len(pos), 2), dtype=np.float32)

        if "indices" in prim:
            idx = read_accessor_array(doc, bin_chunk, prim["indices"]).astype(np.uint32).reshape(-1, 3)
        else:
            idx = np.arange(len(pos), dtype=np.uint32).reshape(-1, 3)

        if det < 0:
            idx = idx[:, [0, 2, 1]]

        if nrm_w is None:
            nrm_w = compute_smooth_normals(pos_w.astype(np.float32), idx)

        all_pos.append(pos_w.astype(np.float32))
        all_norm.append(nrm_w.astype(np.float32))
        all_uv.append(uv)
        all_tris.append(idx + vert_offset)
        vert_offset += len(pos)

    pos_merged = np.vstack(all_pos)
    norm_merged = np.vstack(all_norm)
    uv_merged = np.vstack(all_uv)
    tris_merged = np.vstack(all_tris)

    used_v, clean_tris, dust_removed = strip_micro_dust_components(pos_merged, tris_merged, min_keep_tris=35)
    pos_clean = pos_merged[used_v].copy()
    norm_clean = norm_merged[used_v].copy()
    uv_clean = uv_merged[used_v].copy()

    min_xyz = pos_clean.min(axis=0)
    max_xyz = pos_clean.max(axis=0)
    cx = 0.5 * float(min_xyz[0] + max_xyz[0])
    cz = 0.5 * float(min_xyz[2] + max_xyz[2])

    if alignment_mode == "origin_xyz_center":
        cy = 0.5 * float(min_xyz[1] + max_xyz[1])
        pos_clean[:, 0] -= cx
        pos_clean[:, 1] -= cy
        pos_clean[:, 2] -= cz
    elif alignment_mode == "ground_xz_center":
        by = float(min_xyz[1])
        pos_clean[:, 0] -= cx
        pos_clean[:, 1] -= by
        pos_clean[:, 2] -= cz
    else:
        raise ValueError(f"Unknown alignment_mode: {alignment_mode}")

    bore_info = measure_portal_bore(pos_clean, clean_tris) if is_portal else None

    # Rebuild clean single-mesh GLB preserving all embedded PBR textures & extensions
    out_doc = {
        "asset": {"version": "2.0", "generator": "prepare_v2_extra.py"},
    }
    if "extensionsUsed" in doc:
        out_doc["extensionsUsed"] = doc["extensionsUsed"]

    new_bin = bytearray()
    new_bvs = []
    new_accs = []

    images_out = []
    for img in doc.get("images", []):
        img_copy = dict(img)
        if "bufferView" in img_copy:
            old_bv = doc["bufferViews"][img_copy["bufferView"]]
            off = old_bv.get("byteOffset", 0)
            length = old_bv["byteLength"]
            start = len(new_bin)
            new_bin.extend(bin_chunk[off : off + length])
            new_bin.extend(b"\x00" * ((4 - (len(new_bin) % 4)) % 4))
            img_copy["bufferView"] = len(new_bvs)
            new_bvs.append({"buffer": 0, "byteOffset": start, "byteLength": length})
        images_out.append(img_copy)

    def append_accessor(arr: np.ndarray, target: int, acc_type: str, comp_type: int, with_minmax: bool = False) -> int:
        raw = arr.tobytes()
        start = len(new_bin)
        new_bin.extend(raw)
        new_bin.extend(b"\x00" * ((4 - (len(new_bin) % 4)) % 4))
        bv_idx = len(new_bvs)
        new_bvs.append({"buffer": 0, "byteOffset": start, "byteLength": len(raw), "target": target})
        acc_entry = {
            "bufferView": bv_idx,
            "byteOffset": 0,
            "componentType": comp_type,
            "count": int(len(arr)),
            "type": acc_type,
        }
        if with_minmax:
            acc_entry["min"] = [float(x) for x in arr.min(axis=0)]
            acc_entry["max"] = [float(x) for x in arr.max(axis=0)]
        acc_idx = len(new_accs)
        new_accs.append(acc_entry)
        return acc_idx

    pos_idx = append_accessor(pos_clean.astype(np.float32), 34962, "VEC3", 5126, True)
    norm_idx = append_accessor(norm_clean.astype(np.float32), 34962, "VEC3", 5126, False)
    prim_attrs = {"POSITION": pos_idx, "NORMAL": norm_idx}
    if has_all_uv:
        uv_idx = append_accessor(uv_clean.astype(np.float32), 34962, "VEC2", 5126, False)
        prim_attrs["TEXCOORD_0"] = uv_idx
    ind_idx = append_accessor(clean_tris.reshape(-1).astype(np.uint32), 34963, "SCALAR", 5125, False)

    mats_out = json.loads(json.dumps(doc.get("materials", [{"pbrMetallicRoughness": {"baseColorFactor": [1, 1, 1, 1]}}])))
    for i, m in enumerate(mats_out):
        m["name"] = f"M_{mesh_name}" if i == 0 else f"M_{mesh_name}_{i}"
        m["doubleSided"] = True

    if images_out:
        out_doc["images"] = images_out
    if "samplers" in doc:
        out_doc["samplers"] = doc["samplers"]
    if "textures" in doc:
        out_doc["textures"] = doc["textures"]
    out_doc["materials"] = mats_out
    out_doc["meshes"] = [
        {
            "name": mesh_name,
            "primitives": [{"attributes": prim_attrs, "indices": ind_idx, "material": 0}],
        }
    ]
    out_doc["nodes"] = [{"name": mesh_name, "mesh": 0}]
    out_doc["scenes"] = [{"nodes": [0]}]
    out_doc["scene"] = 0
    out_doc["accessors"] = new_accs
    out_doc["bufferViews"] = new_bvs
    out_doc["buffers"] = [{"byteLength": len(new_bin)}]

    save_glb(dst_path, out_doc, bytes(new_bin))
    # Verify saved Ready GLB header/chunk integrity too
    load_and_verify_glb(dst_path)

    base_tex = None
    try:
        mat0 = mats_out[0]
        bct = mat0.get("pbrMetallicRoughness", {}).get("baseColorTexture")
        if bct is not None and "textures" in out_doc and "images" in out_doc:
            tex_obj = out_doc["textures"][bct["index"]]
            img_obj = out_doc["images"][tex_obj["source"]]
            bv_obj = out_doc["bufferViews"][img_obj["bufferView"]]
            raw_img = bytes(new_bin[bv_obj["byteOffset"] : bv_obj["byteOffset"] + bv_obj["byteLength"]])
            base_tex = np.asarray(Image.open(io.BytesIO(raw_img)).convert("RGB"), dtype=np.float32) / 255.0
    except Exception as exc:
        print(f"[WARN] Could not decode baseColorTexture for {mesh_name}: {exc}")

    g_min = pos_clean.min(axis=0)
    g_max = pos_clean.max(axis=0)
    g_size = g_max - g_min
    g_center = 0.5 * (g_min + g_max)

    # UE Interchange mapping: X_ue = 100 * X_gltf, Y_ue = 100 * Z_gltf, Z_ue = 100 * Y_gltf
    ue_min = [round(float(g_min[0] * 100.0), 3), round(float(g_min[2] * 100.0), 3), round(float(g_min[1] * 100.0), 3)]
    ue_max = [round(float(g_max[0] * 100.0), 3), round(float(g_max[2] * 100.0), 3), round(float(g_max[1] * 100.0), 3)]
    ue_size = [round(float(g_size[0] * 100.0), 3), round(float(g_size[2] * 100.0), 3), round(float(g_size[1] * 100.0), 3)]
    ue_center = [round(float(g_center[0] * 100.0), 3), round(float(g_center[2] * 100.0), 3), round(float(g_center[1] * 100.0), 3)]

    return {
        "pos": pos_clean,
        "norm": norm_clean,
        "uv": uv_clean,
        "tris": clean_tris,
        "base_tex": base_tex,
        "vertexCount": int(len(pos_clean)),
        "triangleCount": int(len(clean_tris)),
        "dustTrianglesRemoved": dust_removed,
        "portalBoreCheck": bore_info,
        "gltfBoundsMeters": {
            "min": [round(float(x), 5) for x in g_min],
            "max": [round(float(x), 5) for x in g_max],
            "size": [round(float(x), 5) for x in g_size],
            "center": [round(float(x), 5) for x in g_center],
        },
        "ueBoundsCm": {
            "min": ue_min,
            "max": ue_max,
            "size": ue_size,
            "center": ue_center,
        },
    }


def render_single_angle(
    pos: np.ndarray,
    norm: np.ndarray,
    uv: np.ndarray,
    tris: np.ndarray,
    base_tex: np.ndarray | None,
    yaw_deg: float,
    pitch_deg: float,
    img_size: int = 840,
) -> Image.Image:
    """Hybrid vectorized Z-buffer + barycentric UV PBR texture renderer."""
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)

    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)

    ry = np.array([[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]], dtype=np.float32)
    rx = np.array([[1.0, 0.0, 0.0], [0.0, cp, -sp], [0.0, sp, cp]], dtype=np.float32)
    rot = rx @ ry

    center = 0.5 * (pos.min(axis=0) + pos.max(axis=0))
    p_rot = (pos - center) @ rot.T
    n_rot = norm @ rot.T

    bmin = p_rot.min(axis=0)
    bmax = p_rot.max(axis=0)
    span_xy = max(float(bmax[0] - bmin[0]), float(bmax[1] - bmin[1]), 1e-5)
    span_z = max(float(bmax[2] - bmin[2]), 1e-5)
    cam_dist = max(span_xy * 2.6, span_z * 2.6)

    z_cam = cam_dist - p_rot[:, 2]
    persp = cam_dist / np.maximum(z_cam, 1e-4)
    px_proj = p_rot[:, 0] * persp
    py_proj = p_rot[:, 1] * persp

    p_span = max(float(px_proj.max() - px_proj.min()), float(py_proj.max() - py_proj.min()), 1e-5)
    scale = (img_size * 0.84) / p_span
    cx_p = 0.5 * float(px_proj.min() + px_proj.max())
    cy_p = 0.5 * float(py_proj.min() + py_proj.max())

    sx = (px_proj - cx_p) * scale + (img_size * 0.5)
    sy_scr = (img_size * 0.5) - (py_proj - cy_p) * scale

    l_key = np.array([0.42, 0.55, 0.72], dtype=np.float32)
    l_key /= np.linalg.norm(l_key)
    l_fill = np.array([-0.55, 0.20, 0.81], dtype=np.float32)
    l_fill /= np.linalg.norm(l_fill)
    l_rim = np.array([0.0, 0.80, -0.60], dtype=np.float32)
    l_rim /= np.linalg.norm(l_rim)

    n_view = np.where(n_rot[:, 2:3] < 0.0, -n_rot, n_rot)
    ndotl_key = np.clip(n_view @ l_key, 0.0, 1.0)
    ndotl_fill = np.clip(n_view @ l_fill, 0.0, 1.0)
    ndotl_rim = np.clip(n_view @ l_rim, 0.0, 1.0)

    shade_r = 0.36 + 0.56 * ndotl_key + 0.16 * ndotl_fill + 0.14 * ndotl_rim
    shade_g = 0.36 + 0.54 * ndotl_key + 0.19 * ndotl_fill + 0.14 * ndotl_rim
    shade_b = 0.38 + 0.50 * ndotl_key + 0.24 * ndotl_fill + 0.16 * ndotl_rim
    v_shade = np.stack([shade_r, shade_g, shade_b], axis=1)

    yy_bg, xx_bg = np.mgrid[0:img_size, 0:img_size].astype(np.float32)
    dist_c = np.sqrt(((xx_bg - img_size * 0.5) / (img_size * 0.7)) ** 2 + ((yy_bg - img_size * 0.5) / (img_size * 0.7)) ** 2)
    bg_val = np.clip(0.95 - 0.10 * dist_c, 0.82, 0.96)
    color_buf = np.stack([bg_val * 0.97, bg_val * 0.98, bg_val * 1.0], axis=-1)
    z_buf = np.full((img_size, img_size), np.inf, dtype=np.float32)

    t0, t1, t2 = tris[:, 0], tris[:, 1], tris[:, 2]
    x0, y0, z0 = sx[t0], sy_scr[t0], z_cam[t0]
    x1, y1, z1 = sx[t1], sy_scr[t1], z_cam[t1]
    x2, y2, z2 = sx[t2], sy_scr[t2], z_cam[t2]

    min_tx = np.minimum(np.minimum(x0, x1), x2)
    max_tx = np.maximum(np.maximum(x0, x1), x2)
    min_ty = np.minimum(np.minimum(y0, y1), y2)
    max_ty = np.maximum(np.maximum(y0, y1), y2)
    span_t = np.maximum(max_tx - min_tx, max_ty - min_ty)

    def sample_tex(u_arr: np.ndarray, v_arr: np.ndarray) -> np.ndarray:
        if base_tex is None:
            return np.full((len(u_arr), 3), 0.85, dtype=np.float32)
        th, tw, _ = base_tex.shape
        uu = np.mod(u_arr, 1.0) * (tw - 1)
        vv = np.mod(v_arr, 1.0) * (th - 1)
        x0_i = np.clip(np.floor(uu).astype(np.int32), 0, tw - 1)
        y0_i = np.clip(np.floor(vv).astype(np.int32), 0, th - 1)
        x1_i = np.clip(x0_i + 1, 0, tw - 1)
        y1_i = np.clip(y0_i + 1, 0, th - 1)
        fx = (uu - x0_i)[:, None]
        fy = (vv - y0_i)[:, None]
        c00 = base_tex[y0_i, x0_i]
        c10 = base_tex[y0_i, x1_i]
        c01 = base_tex[y1_i, x0_i]
        c11 = base_tex[y1_i, x1_i]
        return (c00 * (1.0 - fx) + c10 * fx) * (1.0 - fy) + (c01 * (1.0 - fx) + c11 * fx) * fy

    small_mask = span_t <= 2.5
    if np.any(small_mask):
        sm_idx = np.nonzero(small_mask)[0]
        bary_weights = [
            (1 / 3, 1 / 3, 1 / 3),
            (0.70, 0.15, 0.15),
            (0.15, 0.70, 0.15),
            (0.15, 0.15, 0.70),
            (0.45, 0.45, 0.10),
            (0.10, 0.45, 0.45),
            (0.45, 0.10, 0.45),
        ]
        i0, i1, i2 = t0[sm_idx], t1[sm_idx], t2[sm_idx]
        for w0, w1, w2 in bary_weights:
            px = np.round(w0 * sx[i0] + w1 * sx[i1] + w2 * sx[i2]).astype(np.int32)
            py = np.round(w0 * sy_scr[i0] + w1 * sy_scr[i1] + w2 * sy_scr[i2]).astype(np.int32)
            pz = w0 * z_cam[i0] + w1 * z_cam[i1] + w2 * z_cam[i2]
            valid = (px >= 0) & (px < img_size) & (py >= 0) & (py < img_size)
            if not np.any(valid):
                continue
            px_v, py_v, pz_v = px[valid], py[valid], pz[valid]
            order = np.argsort(-pz_v)
            px_o, py_o, pz_o = px_v[order], py_v[order], pz_v[order]
            vi0, vi1, vi2 = i0[valid][order], i1[valid][order], i2[valid][order]
            u_s = w0 * uv[vi0, 0] + w1 * uv[vi1, 0] + w2 * uv[vi2, 0]
            v_s = w0 * uv[vi0, 1] + w1 * uv[vi1, 1] + w2 * uv[vi2, 1]
            sh_s = w0 * v_shade[vi0] + w1 * v_shade[vi1] + w2 * v_shade[vi2]
            col_s = np.clip(sample_tex(u_s, v_s) * sh_s, 0.0, 1.0)

            flat = py_o * img_size + px_o
            z_cur = z_buf.reshape(-1)[flat]
            closer = pz_o <= z_cur
            flat_c = flat[closer]
            z_buf.reshape(-1)[flat_c] = pz_o[closer]
            color_buf.reshape(-1, 3)[flat_c] = col_s[closer]

    large_idx = np.nonzero(~small_mask)[0]
    for ti in large_idx:
        ia, ib, ic = int(t0[ti]), int(t1[ti]), int(t2[ti])
        ax, ay, az = float(sx[ia]), float(sy_scr[ia]), float(z_cam[ia])
        bx, by_p, bz = float(sx[ib]), float(sy_scr[ib]), float(z_cam[ib])
        cx_t, cy_t, cz_t = float(sx[ic]), float(sy_scr[ic]), float(z_cam[ic])

        denom = (by_p - cy_t) * (ax - cx_t) + (cx_t - bx) * (ay - cy_t)
        if abs(denom) < 1e-6:
            continue

        ix0 = max(0, int(math.floor(min(ax, bx, cx_t))))
        ix1 = min(img_size - 1, int(math.ceil(max(ax, bx, cx_t))))
        iy0 = max(0, int(math.floor(min(ay, by_p, cy_t))))
        iy1 = min(img_size - 1, int(math.ceil(max(ay, by_p, cy_t))))
        if ix0 > ix1 or iy0 > iy1:
            continue

        gy, gx = np.mgrid[iy0 : iy1 + 1, ix0 : ix1 + 1].astype(np.float32)
        gx += 0.5
        gy += 0.5
        inv_d = 1.0 / denom
        w0 = ((by_p - cy_t) * (gx - cx_t) + (cx_t - bx) * (gy - cy_t)) * inv_d
        w1 = ((cy_t - ay) * (gx - cx_t) + (ax - cx_t) * (gy - cy_t)) * inv_d
        w2 = 1.0 - w0 - w1

        inside = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
        if not np.any(inside):
            continue

        zz = w0 * az + w1 * bz + w2 * cz_t
        z_sub = z_buf[iy0 : iy1 + 1, ix0 : ix1 + 1]
        hit = inside & (zz < z_sub)
        if not np.any(hit):
            continue

        hw0, hw1, hw2 = w0[hit], w1[hit], w2[hit]
        u_h = hw0 * uv[ia, 0] + hw1 * uv[ib, 0] + hw2 * uv[ic, 0]
        v_h = hw0 * uv[ia, 1] + hw1 * uv[ib, 1] + hw2 * uv[ic, 1]
        sh_h = hw0[:, None] * v_shade[ia] + hw1[:, None] * v_shade[ib] + hw2[:, None] * v_shade[ic]
        col_h = np.clip(sample_tex(u_h, v_h) * sh_h, 0.0, 1.0)

        z_sub[hit] = zz[hit]
        c_sub = color_buf[iy0 : iy1 + 1, ix0 : ix1 + 1]
        c_sub[hit] = col_h

    return Image.fromarray((np.clip(color_buf, 0.0, 1.0) * 255.0).astype(np.uint8), mode="RGB")


def render_4view_sheet(
    asset_id: str,
    mesh_name: str,
    task_id: int,
    alignment_mode: str,
    info: dict,
    out_png: Path,
) -> None:
    front_pitch = 2.0 if info.get("portalBoreCheck") is not None else 8.0
    angles = [
        ("Front-3/4 Hero", 32.0, 16.0),
        ("Front Elevation", 0.0, front_pitch),
        ("Right Profile", 90.0, 10.0),
        ("Rear-Top 3/4", -142.0, 26.0),
    ]
    tile = 840
    header_h = 96
    sheet = Image.new("RGB", (tile * 2, header_h + tile * 2), (242, 245, 250))
    draw = ImageDraw.Draw(sheet)

    ue_sz = info["ueBoundsCm"]["size"]
    bore_txt = ""
    if info.get("portalBoreCheck") is not None:
        bc = info["portalBoreCheck"]
        bore_txt = f" | BoreRatio: {bc['boreRatio']:.2%} (ClearOpen: {bc['inscribedCircleOpenRatio']:.0%})"

    title_line1 = f"{asset_id} (taskId={task_id}) -> Ready/{mesh_name}.glb [{alignment_mode}]"
    title_line2 = (
        f"Tris: {info['triangleCount']:,} | Verts: {info['vertexCount']:,} | "
        f"UE Bounds (cm): {ue_sz[0]:.1f} x {ue_sz[1]:.1f} x {ue_sz[2]:.1f}{bore_txt}"
    )
    draw.rectangle([0, 0, tile * 2, header_h], fill=(22, 28, 42))
    draw.text((28, 20), title_line1, fill=(245, 226, 175))
    draw.text((28, 52), title_line2, fill=(195, 225, 255))

    for idx, (label, yaw, pitch) in enumerate(angles):
        im = render_single_angle(
            info["pos"],
            info["norm"],
            info["uv"],
            info["tris"],
            info["base_tex"],
            yaw_deg=yaw,
            pitch_deg=pitch,
            img_size=tile,
        )
        d_sub = ImageDraw.Draw(im)
        d_sub.rectangle([16, 16, 300, 52], fill=(28, 34, 48))
        d_sub.text((28, 26), f"{label} (yaw={yaw:.0f}, pitch={pitch:.0f})", fill=(240, 244, 255))
        ox = (idx % 2) * tile
        oy = header_h + (idx // 2) * tile
        sheet.paste(im, (ox, oy))

    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png, optimize=True)
    print(f"[OK] Rendered 4-view preview: {out_png.name}")


def main() -> None:
    READY_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)

    all_task_ids = [row[2] for row in ASSET_TABLE]
    overlap = sorted(set(all_task_ids) & FORBIDDEN_TASK_IDS)
    if overlap:
        raise RuntimeError(f"STRICT ISOLATION VIOLATION: forbidden taskIds encountered: {overlap}")

    manifest_assets = []
    portal_bore_summary = {}
    hero_tiles = []

    for asset_id, mesh_name, task_id, req_faces, align_mode, is_portal, scene_name, src_url, desc in ASSET_TABLE:
        raw_glb = RAW_DIR / f"{mesh_name}.glb"
        if not raw_glb.is_file():
            raise FileNotFoundError(f"Missing raw GLB: {raw_glb}")

        ready_glb = READY_DIR / f"{mesh_name}.glb"
        print(f"Processing {asset_id} ({mesh_name}.glb, taskId={task_id}, align={align_mode})...")
        info = normalize_single_glb(raw_glb, ready_glb, mesh_name, align_mode, is_portal)

        preview_png = PREVIEWS_DIR / f"{asset_id}_{mesh_name}_preview.png"
        render_4view_sheet(asset_id, mesh_name, task_id, align_mode, info, preview_png)

        full_sheet = Image.open(preview_png)
        hero_crop = full_sheet.crop((0, 96, 840, 936)).resize((560, 560), Image.Resampling.LANCZOS)
        d_hc = ImageDraw.Draw(hero_crop)
        d_hc.rectangle([0, 504, 560, 560], fill=(22, 28, 42))
        label_extra = f" | bore={info['portalBoreCheck']['boreRatio']:.0%}" if info["portalBoreCheck"] else ""
        d_hc.text((14, 514), f"{asset_id} (task {task_id})", fill=(245, 226, 175))
        d_hc.text((14, 534), f"{mesh_name}.glb | {info['triangleCount']:,} tris{label_extra}", fill=(190, 225, 255))
        hero_tiles.append(hero_crop)

        entry = {
            "assetId": asset_id,
            "readyFile": f"Ready/{mesh_name}.glb",
            "rawFile": f"raw/{mesh_name}.glb",
            "previewFile": f"previews/{preview_png.name}",
            "targetScene": scene_name,
            "description": desc,
            "pipeline": "lux3d_text_to_3d(G1)",
            "version": "G1",
            "requestedFaceCount": req_faces,
            "taskId": task_id,
            "sourceUrl": src_url,
            "alignmentMode": align_mode,
            "vertexCount": info["vertexCount"],
            "triangleCount": info["triangleCount"],
            "dustTrianglesRemoved": info["dustTrianglesRemoved"],
            "doubleSidedMaterials": True,
            "singleMeshNode": mesh_name,
            "gltfBoundsMeters": info["gltfBoundsMeters"],
            "ueBoundsCm": info["ueBoundsCm"],
            "hashes": {
                f"raw/{mesh_name}.glb": sha256_file(raw_glb),
                f"Ready/{mesh_name}.glb": sha256_file(ready_glb),
                f"previews/{preview_png.name}": sha256_file(preview_png),
            },
        }
        if info["portalBoreCheck"] is not None:
            entry["portalBoreCheck"] = info["portalBoreCheck"]
            portal_bore_summary[mesh_name] = info["portalBoreCheck"]

        manifest_assets.append(entry)
        del info
        gc.collect()

    # Save 10-asset (5x2) overview sheet
    banner_h = 84
    overview = Image.new("RGB", (560 * 5, banner_h + 560 * 2), (242, 245, 250))
    d_ov = ImageDraw.Draw(overview)
    d_ov.rectangle([0, 0, 560 * 5, banner_h], fill=(18, 24, 38))
    d_ov.text(
        (32, 28),
        "ButterflyDream V2_Extra — 10 Lux3D G1 Assets (Scenes 3-5 Landmarks, 3 Hollow Portals, 2 Dynamic Particle Meshes)",
        fill=(245, 226, 175),
    )
    for i, tile_im in enumerate(hero_tiles):
        overview.paste(tile_im, ((i % 5) * 560, banner_h + (i // 5) * 560))
    overview_path = PREVIEWS_DIR / "V2_Extra_Overview.png"
    overview.save(overview_path, optimize=True)
    print(f"[OK] Saved overview sheet -> {overview_path}")

    # Record companion spatial world files present in V2_Extra
    world_files = {}
    for wf in sorted(V2_ROOT.glob("World_*")):
        if wf.is_file():
            world_files[wf.name] = sha256_file(wf)

    manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "owner": "asset-gen",
        "project": "ButterflyDream V2_Extra (墨染云海 · 琉璃幻境 · 混沌归一 · 传送仙门 · 灵动粒子群)",
        "ueCoordinateMapping": "X_ue = 100 * X_gltf, Y_ue = 100 * Z_gltf, Z_ue = 100 * Y_gltf",
        "isolationVerified": {
            "forbiddenPreExistingTaskIds": sorted(FORBIDDEN_TASK_IDS),
            "v2ExtraTaskIds": all_task_ids,
            "overlapCount": len(overlap),
        },
        "overviewPreview": "previews/V2_Extra_Overview.png",
        "overviewHash": sha256_file(overview_path),
        "portalBoreSummary": portal_bore_summary,
        "assets": manifest_assets,
        "companionWorldFiles": world_files,
    }
    MANIFEST_JSON.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] Wrote manifest -> {MANIFEST_JSON}")


if __name__ == "__main__":
    main()
