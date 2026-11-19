import json
import struct
import pathlib
import numpy as np

root = pathlib.Path(r"e:\紫萱2版\Assets\LuxGenerated")
ready_dir = root / "Ready"
ready_dir.mkdir(parents=True, exist_ok=True)


def load_glb(path: pathlib.Path):
    data = path.read_bytes()
    jlen, _ = struct.unpack_from("<II", data, 12)
    doc = json.loads(data[20 : 20 + jlen].decode("utf-8"))
    bin_chunk = data[20 + jlen + 8 :]
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


def rename_single_mesh_glb(src: pathlib.Path, dst: pathlib.Path, mesh_name: str, translate_xyz=(0.0, 0.0, 0.0)):
    doc, bin_chunk = load_glb(src)
    bin_arr = bytearray(bin_chunk)
    tx, ty, tz = translate_xyz
    if tx != 0.0 or ty != 0.0 or tz != 0.0:
        for mesh in doc.get("meshes", []):
            for prim in mesh.get("primitives", []):
                if "POSITION" in prim.get("attributes", {}):
                    acc = doc["accessors"][prim["attributes"]["POSITION"]]
                    bv = doc["bufferViews"][acc["bufferView"]]
                    off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
                    cnt = acc["count"]
                    arr = np.frombuffer(bin_arr, dtype=np.float32, count=cnt * 3, offset=off).copy().reshape(-1, 3)
                    arr[:, 0] += tx
                    arr[:, 1] += ty
                    arr[:, 2] += tz
                    acc["min"] = arr.min(axis=0).tolist()
                    acc["max"] = arr.max(axis=0).tolist()
                    bin_arr[off : off + cnt * 12] = arr.astype(np.float32).tobytes()

    for n in doc.get("nodes", []):
        n["name"] = mesh_name
        n.pop("rotation", None)
        n.pop("matrix", None)
    for m in doc.get("meshes", []):
        m["name"] = mesh_name
    for mat in doc.get("materials", []):
        mat["name"] = f"M_{mesh_name}"
        mat["doubleSided"] = True
    save_glb(dst, doc, bytes(bin_arr))
    print(f"Saved {dst.name} ({mesh_name})")


def build_split_butterfly():
    """
    Use official Lux3D Part-Split Butterfly (taskId 8025276 from 8024891):
    Original orientation: X = Left(-)/Right(+), Y = Tail(-)/Head(+), Z = Ventral(-)/Dorsal(+).
    Rotate -90 deg around X -> Y_gltf = +Z_orig (Dorsal UP), Z_gltf = -Y_orig (Head at -Z Forward).
    Matches UE Interchange import convention so +90 deg Yaw in AButterflyPawn faces +X Forward.
    Shift vertical (+Y_gltf) by +0.025m so thorax sits near origin Z=0 in UE.
    """
    src = root / "B01_LuxButterfly_PartSplit_8025276.glb"
    doc, bin_chunk = load_glb(src)

    wing_prim = doc["meshes"][0]["primitives"][0]
    body_prim = doc["meshes"][1]["primitives"][0]

    def read_prim_arrays(prim):
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
        indices = np.frombuffer(bin_chunk, dtype=dtype, count=idx_acc["count"], offset=idx_off).copy().reshape(-1, 3)

        # Rotate -90 deg around X: (x, y, z) -> (x, z + 0.025, -y)
        pos_rot = np.empty_like(pos)
        pos_rot[:, 0] = pos[:, 0]
        pos_rot[:, 1] = pos[:, 2] + 0.025
        pos_rot[:, 2] = -pos[:, 1]

        norm_rot = None
        if norm is not None:
            norm_rot = np.empty_like(norm)
            norm_rot[:, 0] = norm[:, 0]
            norm_rot[:, 1] = norm[:, 2]
            norm_rot[:, 2] = -norm[:, 1]

        return pos_rot, norm_rot, uv, indices

    w_pos, w_norm, w_uv, w_tris = read_prim_arrays(wing_prim)
    b_pos, b_norm, b_uv, b_tris = read_prim_arrays(body_prim)

    tri_centroids_x = w_pos[w_tris].mean(axis=1)[:, 0]
    left_tris = w_tris[tri_centroids_x < 0.0]
    right_tris = w_tris[tri_centroids_x >= 0.0]

    def compact_submesh(pos, norm, uv, tris, offset_x=0.0):
        unique_v, inv = np.unique(tris.reshape(-1), return_inverse=True)
        new_pos = pos[unique_v].copy()
        new_pos[:, 0] -= offset_x
        new_norm = norm[unique_v] if norm is not None else None
        new_uv = uv[unique_v] if uv is not None else None
        new_tris = inv.reshape(-1, 3).astype(np.uint32)
        return new_pos, new_norm, new_uv, new_tris

    # Center wing root at X=0 so wing rotation pivot works cleanly without radial translation!
    l_pos, l_norm, l_uv, l_tris = compact_submesh(w_pos, w_norm, w_uv, left_tris, offset_x=-0.011)
    r_pos, r_norm, r_uv, r_tris = compact_submesh(w_pos, w_norm, w_uv, right_tris, offset_x=+0.011)
    body_pos, body_norm, body_uv, body_tris = compact_submesh(b_pos, b_norm, b_uv, b_tris, offset_x=0.0)

    orig_doc, orig_bin = load_glb(root / "B01_LuxButterfly_8024891.glb")

    for part_name, p_pos, p_norm, p_uv, p_tris in [
        ("Butterfly_Body", body_pos, body_norm, body_uv, body_tris),
        ("Wing_L", l_pos, l_norm, l_uv, l_tris),
        ("Wing_R", r_pos, r_norm, r_uv, r_tris),
    ]:
        sub_doc = json.loads(json.dumps(orig_doc))
        new_bin = bytearray()
        new_bvs = []
        new_accs = []

        for img in sub_doc.get("images", []):
            old_bv = orig_doc["bufferViews"][img["bufferView"]]
            off = old_bv.get("byteOffset", 0)
            length = old_bv["byteLength"]
            start = len(new_bin)
            new_bin.extend(orig_bin[off : off + length])
            new_bin.extend(b"\x00" * ((4 - (len(new_bin) % 4)) % 4))
            img["bufferView"] = len(new_bvs)
            new_bvs.append({"buffer": 0, "byteOffset": start, "byteLength": length})

        def add_array(arr: np.ndarray, target: int, acc_type: str, comp_type: int, with_minmax: bool = False):
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
            if with_minmax:
                acc["min"] = arr.min(axis=0).tolist()
                acc["max"] = arr.max(axis=0).tolist()
            acc_idx = len(new_accs)
            new_accs.append(acc)
            return acc_idx

        pos_idx = add_array(p_pos.astype(np.float32), 34962, "VEC3", 5126, True)
        attrs = {"POSITION": pos_idx}
        if p_norm is not None:
            attrs["NORMAL"] = add_array(p_norm.astype(np.float32), 34962, "VEC3", 5126, False)
        if p_uv is not None:
            attrs["TEXCOORD_0"] = add_array(p_uv.astype(np.float32), 34962, "VEC2", 5126, False)
        ind_idx = add_array(p_tris.reshape(-1).astype(np.uint32), 34963, "SCALAR", 5125, False)

        sub_doc["bufferViews"] = new_bvs
        sub_doc["accessors"] = new_accs
        sub_doc["buffers"] = [{"byteLength": len(new_bin)}]
        sub_doc["meshes"] = [{"name": part_name, "primitives": [{"attributes": attrs, "indices": ind_idx, "material": 0}]}]
        sub_doc["nodes"] = [{"name": part_name, "mesh": 0}]
        sub_doc["scenes"] = [{"nodes": [0]}]
        for mat in sub_doc.get("materials", []):
            mat["name"] = "M_LuxButterfly"
            mat["doubleSided"] = True

        out_path = ready_dir / f"{part_name}.glb"
        save_glb(out_path, sub_doc, bytes(new_bin))
        print(f"Saved butterfly part {out_path.name}: verts={len(p_pos)}, tris={len(p_tris)}")


build_split_butterfly()

# Prepare Gate G01 articulated parts (from official 8025176), keep exact URDF relative origin!
g01_dir = root / "G01_Articulation_8025176" / "urdf" / "meshes"
rename_single_mesh_glb(g01_dir / "base.glb", ready_dir / "Gate_Frame.glb", "Gate_Frame")
rename_single_mesh_glb(g01_dir / "door_left.glb", ready_dir / "Gate_Leaf_L.glb", "Gate_Leaf_L")
rename_single_mesh_glb(g01_dir / "door_right.glb", ready_dir / "Gate_Leaf_R.glb", "Gate_Leaf_R")

# Prepare Gate G03 articulated parts (from official 8025399)
g03_dir = root / "G03_Articulation_8025399" / "urdf" / "meshes"
rename_single_mesh_glb(g03_dir / "base.glb", ready_dir / "StarGate_OuterRing.glb", "StarGate_OuterRing")
rename_single_mesh_glb(g03_dir / "inner_ring.glb", ready_dir / "StarGate_InnerRing.glb", "StarGate_InnerRing")

# Prepare other Lux3D assets
rename_single_mesh_glb(root / "T01_StarTunnelRing_8024910.glb", ready_dir / "Tunnel_Ring.glb", "Tunnel_Ring")
rename_single_mesh_glb(root / "S01_FloatingPavilion_8025164.glb", ready_dir / "Floating_Pavilion.glb", "Floating_Pavilion")
rename_single_mesh_glb(root / "W01_FloatingLantern_8025401.glb", ready_dir / "Floating_Lantern.glb", "Floating_Lantern")
rename_single_mesh_glb(root / "W02_CrystalLotus_8025406.glb", ready_dir / "Crystal_Lotus.glb", "Crystal_Lotus")
rename_single_mesh_glb(root / "T02_DreamScaleBlade_8025511.glb", ready_dir / "Dream_Scale_Blade.glb", "Dream_Scale_Blade")
