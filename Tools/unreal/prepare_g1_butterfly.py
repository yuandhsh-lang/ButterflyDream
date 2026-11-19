import json
import struct
import pathlib
import io
import numpy as np
from PIL import Image

ASSETS_DIR = pathlib.Path(r"E:\紫萱2版\Assets\LuxGenerated")
TEXTURES_DIR = ASSETS_DIR / "G1_Textures"
MODEL_GLB = TEXTURES_DIR / "MODEL.glb"
READY_DIR = ASSETS_DIR / "V2_Butterfly" / "Ready"
READY_DIR.mkdir(parents=True, exist_ok=True)

def load_glb(path: pathlib.Path):
    data = path.read_bytes()
    jlen, _ = struct.unpack_from("<II", data, 12)
    doc = json.loads(data[20:20+jlen].decode("utf-8"))
    bin_chunk = data[20+jlen+8:]
    return doc, bin_chunk

def save_glb(path: pathlib.Path, doc: dict, bin_chunk: bytes):
    jbytes = json.dumps(doc, separators=(",", ":")).encode("utf-8")
    jbytes += b" " * ((4 - (len(jbytes) % 4)) % 4)
    bin_padded = bin_chunk + (b"\x00" * ((4 - (len(bin_chunk) % 4)) % 4))
    total_len = 12 + 8 + len(jbytes) + 8 + len(bin_padded)
    with path.open("wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total_len))
        f.write(struct.pack("<II", len(jbytes), 0x4E4F534A))
        f.write(jbytes)
        f.write(struct.pack("<II", len(bin_padded), 0x004E4942))
        f.write(bin_padded)

def read_prim_arrays(doc: dict, bin_chunk: bytes, mesh_idx: int = 0, prim_idx: int = 0):
    prim = doc["meshes"][mesh_idx]["primitives"][prim_idx]
    pos_acc = doc["accessors"][prim["attributes"]["POSITION"]]
    pos_bv = doc["bufferViews"][pos_acc["bufferView"]]
    pos_off = pos_bv.get("byteOffset", 0) + pos_acc.get("byteOffset", 0)
    pos = np.frombuffer(bin_chunk, dtype=np.float32, count=pos_acc["count"] * 3, offset=pos_off).copy().reshape(-1, 3)

    norm = None
    if "NORMAL" in prim["attributes"]:
        n_acc = doc["accessors"][prim["attributes"]["NORMAL"]]
        n_bv = doc["bufferViews"][n_acc["bufferView"]]
        n_off = n_bv.get("byteOffset", 0) + n_acc.get("byteOffset", 0)
        norm = np.frombuffer(bin_chunk, dtype=np.float32, count=n_acc["count"] * 3, offset=n_off).copy().reshape(-1, 3)

    uv = None
    if "TEXCOORD_0" in prim["attributes"]:
        u_acc = doc["accessors"][prim["attributes"]["TEXCOORD_0"]]
        u_bv = doc["bufferViews"][u_acc["bufferView"]]
        u_off = u_bv.get("byteOffset", 0) + u_acc.get("byteOffset", 0)
        uv = np.frombuffer(bin_chunk, dtype=np.float32, count=u_acc["count"] * 2, offset=u_off).copy().reshape(-1, 2)

    idx_acc = doc["accessors"][prim["indices"]]
    idx_bv = doc["bufferViews"][idx_acc["bufferView"]]
    idx_off = idx_bv.get("byteOffset", 0) + idx_acc.get("byteOffset", 0)
    dtype = np.uint32 if idx_acc["componentType"] == 5125 else np.uint16
    tris = np.frombuffer(bin_chunk, dtype=dtype, count=idx_acc["count"], offset=idx_off).copy().reshape(-1, 3)
    return pos, norm, uv, tris.astype(np.uint32)

def compact_submesh(pos: np.ndarray, norm: np.ndarray, uv: np.ndarray, tris: np.ndarray):
    unique_v, inv = np.unique(tris.reshape(-1), return_inverse=True)
    new_pos = pos[unique_v].copy()
    new_norm = norm[unique_v].copy() if norm is not None else None
    new_uv = uv[unique_v].copy() if uv is not None else None
    new_tris = inv.reshape(-1, 3).astype(np.uint32)
    return new_pos, new_norm, new_uv, new_tris

def export_single_mesh_glb(out_path: pathlib.Path, part_name: str, pos: np.ndarray, norm: np.ndarray, uv: np.ndarray, tris: np.ndarray, base_png: bytes, mr_png: bytes, em_png: bytes):
    new_bin = bytearray()
    new_bvs = []
    new_accs = []

    def add_image_bytes(raw_bytes: bytes) -> int:
        start = len(new_bin)
        new_bin.extend(raw_bytes)
        new_bin.extend(b"\x00" * ((4 - (len(new_bin) % 4)) % 4))
        bv_idx = len(new_bvs)
        new_bvs.append({"buffer": 0, "byteOffset": start, "byteLength": len(raw_bytes)})
        return bv_idx

    bv_base = add_image_bytes(base_png)
    bv_mr = add_image_bytes(mr_png)
    bv_em = add_image_bytes(em_png)

    def add_array(arr: np.ndarray, target: int, acc_type: str, comp_type: int, with_minmax: bool = False) -> int:
        raw = arr.tobytes()
        start = len(new_bin)
        new_bin.extend(raw)
        new_bin.extend(b"\x00" * ((4 - (len(new_bin) % 4)) % 4))
        bv_idx = len(new_bvs)
        new_bvs.append({"buffer": 0, "byteOffset": start, "byteLength": len(raw), "target": target})
        acc = {"bufferView": bv_idx, "byteOffset": 0, "componentType": comp_type, "count": int(len(arr)), "type": acc_type}
        if with_minmax:
            acc["min"] = [float(x) for x in arr.min(axis=0)]
            acc["max"] = [float(x) for x in arr.max(axis=0)]
        acc_idx = len(new_accs)
        new_accs.append(acc)
        return acc_idx

    pos_idx = add_array(pos.astype(np.float32), 34962, "VEC3", 5126, True)
    attrs = {"POSITION": pos_idx}
    if norm is not None:
        attrs["NORMAL"] = add_array(norm.astype(np.float32), 34962, "VEC3", 5126, False)
    if uv is not None:
        attrs["TEXCOORD_0"] = add_array(uv.astype(np.float32), 34962, "VEC2", 5126, False)
    ind_idx = add_array(tris.reshape(-1).astype(np.uint32), 34963, "SCALAR", 5125, False)

    doc = {
        "asset": {"version": "2.0", "generator": "ButterflyDream G1 Lux3D Pipeline"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"name": part_name, "mesh": 0}],
        "meshes": [{"name": part_name, "primitives": [{"attributes": attrs, "indices": ind_idx, "material": 0}]}],
        "materials": [
            {
                "name": "M_LuxButterfly_V2",
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
                "emissiveFactor": [0.32, 0.28, 0.18],
                "extensions": {"KHR_materials_specular": {"specularFactor": 0.95}},
            }
        ],
        "textures": [{"sampler": 0, "source": 0}, {"sampler": 0, "source": 1}, {"sampler": 0, "source": 2}],
        "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}],
        "images": [
            {"bufferView": bv_base, "mimeType": "image/png", "name": "BaseColor"},
            {"bufferView": bv_mr, "mimeType": "image/png", "name": "MetallicRoughness"},
            {"bufferView": bv_em, "mimeType": "image/png", "name": "EmissiveFiligree"},
        ],
        "bufferViews": new_bvs,
        "accessors": new_accs,
        "buffers": [{"byteLength": len(new_bin)}],
        "extensionsUsed": ["KHR_materials_specular"],
    }
    save_glb(out_path, doc, bytes(new_bin))

def main():
    print("Loading G1 MODEL.glb...")
    doc, bin_chunk = load_glb(MODEL_GLB)
    pos, norm, uv, tris = read_prim_arrays(doc, bin_chunk)
    print(f"Loaded {len(pos)} verts, {len(tris)} tris")

    # Load textures
    diff_img = Image.open(TEXTURES_DIR / "RawDiffuseFilter.png").convert("RGB")
    gloss_img = Image.open(TEXTURES_DIR / "RawReflectGlossFilter.png").convert("L")
    refl_img = Image.open(TEXTURES_DIR / "RawReflectFilter.png").convert("L")
    
    diff_arr = np.array(diff_img, dtype=np.float32) / 255.0
    gloss_arr = np.array(gloss_img, dtype=np.float32) / 255.0
    refl_arr = np.array(refl_img, dtype=np.float32) / 255.0

    # Build midnight sapphire blue base with golden vein contrast
    lum = 0.299 * diff_arr[:, :, 0] + 0.587 * diff_arr[:, :, 1] + 0.114 * diff_arr[:, :, 2]
    # Gold veins: warm yellow-gold highlights
    is_gold = (diff_arr[:, :, 0] > diff_arr[:, :, 2] + 0.08) & (diff_arr[:, :, 1] > diff_arr[:, :, 2] + 0.04) & (lum > 0.35)
    gold_mask = np.clip((diff_arr[:, :, 0] - diff_arr[:, :, 2] - 0.05) * 4.0, 0.0, 1.0) * np.clip((lum - 0.25) * 3.0, 0.0, 1.0)

    # Deep sapphire wing membrane:
    sapphire_blue = np.array([0.04, 0.10, 0.28], dtype=np.float32)
    cyan_glow = np.array([0.15, 0.65, 0.95], dtype=np.float32)
    wing_base = diff_arr * 0.85 + sapphire_blue[None, None, :] * 0.35

    # Composite baseColor:
    base_rgb = wing_base * (1.0 - gold_mask[:, :, None] * 0.7) + diff_arr * (gold_mask[:, :, None] * 0.7)
    base_rgb = np.clip(base_rgb, 0.0, 1.0)

    # Metallic Roughness:
    # R = AO (1.0), G = Roughness (inverse gloss), B = Metallic
    roughness = np.clip(1.0 - gloss_arr * 0.85, 0.12, 0.90)
    metallic = np.clip(refl_arr * 0.6 + gold_mask * 0.85, 0.0, 1.0)
    ao = np.ones_like(roughness)
    mr_arr = np.stack([ao, roughness, metallic], axis=2)

    # Emissive:
    # Gold veins glow warm imperial gold, wing edges have gentle cyan celestial bioluminescence
    gold_em = np.clip((diff_arr[:, :, 0] - 0.25) * 2.2, 0.0, 1.0) * gold_mask
    emissive_rgb = (
        np.array([1.0, 0.82, 0.40], dtype=np.float32)[None, None, :] * gold_em[:, :, None] * 0.85
        + cyan_glow[None, None, :] * np.clip((lum - 0.50) * 1.5, 0.0, 1.0)[:, :, None] * 0.25
    )
    emissive_rgb = np.clip(emissive_rgb, 0.0, 1.0)

    def encode_png(float_rgb: np.ndarray, size=(1024, 1024)) -> bytes:
        im = Image.fromarray((np.clip(float_rgb, 0.0, 1.0) * 255.0).astype(np.uint8))
        if size is not None and im.size != size:
            im = im.resize(size, Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=False)
        return buf.getvalue()

    base_png = encode_png(base_rgb, (1024, 1024))
    mr_png = encode_png(mr_arr, (1024, 1024))
    em_png = encode_png(emissive_rgb, (1024, 1024))

    # Split into Body, Wing_L, Wing_R
    # Coordinate system in MODEL.glb:
    # X: Left(-)/Right(+), Y: Head(+)/Tail(-), Z: Up(+)/Down(-)
    tri_cent = pos[tris].mean(axis=1)
    cx = tri_cent[:, 0]
    cy = tri_cent[:, 1]

    # Body thorax width:
    body_width = 0.0078
    is_body = np.abs(cx) <= body_width

    body_tris = tris[is_body]
    wl_tris = tris[(~is_body) & (cx < 0.0)]
    wr_tris = tris[(~is_body) & (cx > 0.0)]

    raw_body_p, raw_body_n, raw_body_u, raw_body_t = compact_submesh(pos, norm, uv, body_tris)
    raw_wl_p, raw_wl_n, raw_wl_u, raw_wl_t = compact_submesh(pos, norm, uv, wl_tris)
    raw_wr_p, raw_wr_n, raw_wr_u, raw_wr_t = compact_submesh(pos, norm, uv, wr_tris)

    # Target wingspan: 0.38m (38 cm)
    raw_wingspan = float(pos[:, 0].max() - pos[:, 0].min())
    scale = 0.380 / raw_wingspan

    # In UE glTF: X is Left(-)/Right(+), Y is Dorsal (+Y_gltf = +Z_ue Up), Z is Tail(+)/Head(-)
    def to_ue_gltf(p: np.ndarray, n: np.ndarray):
        out_p = np.empty_like(p)
        out_p[:, 0] = p[:, 0] * scale
        out_p[:, 1] = p[:, 2] * scale
        out_p[:, 2] = -p[:, 1] * scale

        out_n = np.empty_like(n)
        out_n[:, 0] = n[:, 0]
        out_n[:, 1] = n[:, 2]
        out_n[:, 2] = -n[:, 1]
        nl = np.linalg.norm(out_n, axis=1, keepdims=True)
        out_n = out_n / np.maximum(nl, 1e-6)
        return out_p, out_n

    body_p, body_n = to_ue_gltf(raw_body_p, raw_body_n)
    wl_p, wl_n = to_ue_gltf(raw_wl_p, raw_wl_n)
    wr_p, wr_n = to_ue_gltf(raw_wr_p, raw_wr_n)

    # Shift wing hinge to X = 0.0
    hinge_l = float(wl_p[:, 0].max())
    hinge_r = float(wr_p[:, 0].min())
    wl_p[:, 0] -= hinge_l
    wr_p[:, 0] -= hinge_r
    wl_p[:, 0] = np.minimum(wl_p[:, 0], 0.0)
    wr_p[:, 0] = np.maximum(wr_p[:, 0], 0.0)

    # Export Ready GLBs
    body_out = READY_DIR / "Butterfly_Body.glb"
    wl_out = READY_DIR / "Wing_L.glb"
    wr_out = READY_DIR / "Wing_R.glb"

    export_single_mesh_glb(body_out, "Butterfly_Body", body_p, body_n, raw_body_u, raw_body_t, base_png, mr_png, em_png)
    export_single_mesh_glb(wl_out, "Wing_L", wl_p, wl_n, raw_wl_u, raw_wl_t, base_png, mr_png, em_png)
    export_single_mesh_glb(wr_out, "Wing_R", wr_p, wr_n, raw_wr_u, raw_wr_t, base_png, mr_png, em_png)

    print(f"SUCCESS: Exported G1 Ready GLBs to {READY_DIR}")
    print(f"  Body: {len(body_p)} verts, {len(raw_body_t)} tris")
    print(f"  Wing_L: {len(wl_p)} verts, {len(raw_wl_t)} tris, X range [{wl_p[:,0].min():.4f}, {wl_p[:,0].max():.4f}]")
    print(f"  Wing_R: {len(wr_p)} verts, {len(raw_wr_t)} tris, X range [{wr_p[:,0].min():.4f}, {wr_p[:,0].max():.4f}]")

if __name__ == "__main__":
    main()
