import json
from pathlib import Path
import unreal

ASSET_SUB = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
LIB = unreal.MaterialEditingLibrary

MESH_PATHS = [
    "/Game/LuxGenerated/Extra/Sakura_Spirit_Swirl",
    "/Game/LuxGenerated/Extra/Celestial_Spirit_Koi",
    "/Game/LuxGenerated/Scale_T02/Dream_Scale_Blade",
]

REPORT_PATH = Path(r"E:\紫萱2版\Evidence\Unreal\LuxRebuild\ism-fix-report.json")
LOCAL_MAT_DIR = "/Game/LuxGenerated/Materials"

cloned_cache: dict[str, unreal.MaterialInterface] = {}


def ensure_local_parent_with_ism(mat_iface: unreal.MaterialInterface) -> unreal.MaterialInterface:
    path = mat_iface.get_path_name()
    pkg_path = path.split(".")[0]
    if pkg_path in cloned_cache:
        return cloned_cache[pkg_path]

    if isinstance(mat_iface, unreal.Material):
        if pkg_path.startswith("/Game/"):
            target = mat_iface
        else:
            local_pkg = f"{LOCAL_MAT_DIR}/M_ISM_{mat_iface.get_name()}"
            if ASSET_SUB.does_asset_exist(local_pkg):
                target = ASSET_SUB.load_asset(local_pkg)
            else:
                target = ASSET_SUB.duplicate_asset(pkg_path, local_pkg)
        if not target:
            raise RuntimeError(f"Failed to duplicate parent material {pkg_path}")
        target.set_editor_property("used_with_instanced_static_meshes", True)
        LIB.recompile_material(target)
        ASSET_SUB.save_loaded_asset(target, False)
        cloned_cache[pkg_path] = target
        return target

    if isinstance(mat_iface, unreal.MaterialInstanceConstant):
        parent = mat_iface.get_editor_property("parent")
        new_parent = ensure_local_parent_with_ism(parent) if parent else None
        if pkg_path.startswith("/Game/"):
            target = mat_iface
        else:
            local_pkg = f"{LOCAL_MAT_DIR}/MI_ISM_{mat_iface.get_name()}"
            if ASSET_SUB.does_asset_exist(local_pkg):
                target = ASSET_SUB.load_asset(local_pkg)
            else:
                target = ASSET_SUB.duplicate_asset(pkg_path, local_pkg)
        if not target:
            raise RuntimeError(f"Failed to duplicate parent MI {pkg_path}")
        if new_parent:
            LIB.set_material_instance_parent(target, new_parent)
        LIB.update_material_instance(target)
        ASSET_SUB.save_loaded_asset(target, False)
        cloned_cache[pkg_path] = target
        return target

    return mat_iface


def main() -> None:
    results = []
    for mpath in MESH_PATHS:
        mesh = ASSET_SUB.load_asset(mpath)
        if not isinstance(mesh, unreal.StaticMesh):
            raise RuntimeError(f"Missing StaticMesh: {mpath}")
        mesh_rec = {"mesh": mpath, "slots": []}
        for idx, slot in enumerate(mesh.get_editor_property("static_materials")):
            mat = slot.material_interface
            if not mat:
                continue
            before_base = mat.get_base_material().get_path_name() if mat.get_base_material() else None
            before_parent = mat.get_editor_property("parent").get_path_name() if isinstance(mat, unreal.MaterialInstanceConstant) and mat.get_editor_property("parent") else None
            fixed = ensure_local_parent_with_ism(mat)
            if fixed != mat:
                mesh.set_material(idx, fixed)
            after_base_obj = fixed.get_base_material()
            after_flag = bool(after_base_obj.get_editor_property("used_with_instanced_static_meshes")) if after_base_obj else False
            mesh_rec["slots"].append({
                "index": idx,
                "material": fixed.get_path_name(),
                "before_parent": before_parent,
                "before_base": before_base,
                "after_base": after_base_obj.get_path_name() if after_base_obj else None,
                "used_with_instanced_static_meshes": after_flag,
            })
        ASSET_SUB.save_loaded_asset(mesh, False)
        results.append(mesh_rec)

    # Touch all 5 realms & custom HLSL materials read-only to ensure shaders warm cleanly
    for custom_mat in (
        "M_Lux_StarSeaSkyDome", "M_Lux_StarWater",
        "M_Lux_InkCloudSkyDome", "M_Lux_InkMirrorWater",
        "M_Lux_CrystalMirageSkyDome", "M_Lux_CrystalMirrorWater",
        "M_Lux_TaijiCosmosSkyDome", "M_Lux_TaijiMirrorWater",
    ):
        ASSET_SUB.load_asset(f"{LOCAL_MAT_DIR}/{custom_mat}")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps({"status": "SUCCEEDED", "meshes": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    unreal.log(f"FIX_ISM_DONE meshes={len(results)}")


if __name__ == "__main__":
    main()
