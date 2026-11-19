"""Recover the StarSea map in an isolated UE 5.8 working copy.

The entry point reuses already imported Lux3D meshes and existing materials.
It does not call the legacy F09 deletion, re-import, or F06 modification steps.
For safety, it refuses to replace an existing StarSea map.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import unreal


REPORT: dict = {
    "status": "STARTED",
    "deleted": [],
    "imported_meshes": {},
    "nanite_disabled": [],
    "f06_metrics": {},
    "lux_starsea_metrics": {},
    "warnings": [],
    "errors": [],
}


def resolve_project_root() -> Path:
    """Resolve ASCII V: mount root when available, else repo root."""
    if Path("V:/Assets/LuxGenerated/Ready").is_dir():
        return Path("V:/")
    return Path(__file__).resolve().parents[2]


ROOT = resolve_project_root()
READY_DIR = ROOT / "Assets" / "LuxGenerated" / "Ready"
EVIDENCE_DIR = ROOT / "Evidence" / "Unreal" / "LuxRecovery_20261117"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = EVIDENCE_DIR / "rebuild-report.json"

LEVEL_SUB = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ASSET_SUB = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
ACTOR_SUB = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
UNREAL_EDITOR_SUB = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
STATIC_MESH_SUB = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
INTERCHANGE_MGR = unreal.InterchangeManager.get_interchange_manager_scripted()


LUX_ASSET_SPECS = [
    # (glb_filename, import_pkg_dir, target_mesh_path, complex_collision, glow_color, glow_strength)
    ("Butterfly_Body.glb", "/Game/LuxGenerated/_Imports/B01_Body", "/Game/LuxGenerated/Butterfly_B01/Butterfly_Body", False, (0.95, 0.78, 0.42), 0.12),
    ("Wing_L.glb", "/Game/LuxGenerated/_Imports/B01_WingL", "/Game/LuxGenerated/Butterfly_B01/Wing_L", False, (1.0, 0.62, 0.78), 0.32),
    ("Wing_R.glb", "/Game/LuxGenerated/_Imports/B01_WingR", "/Game/LuxGenerated/Butterfly_B01/Wing_R", False, (1.0, 0.62, 0.78), 0.32),
    ("Gate_Frame.glb", "/Game/LuxGenerated/_Imports/G01_Frame", "/Game/LuxGenerated/Gate_G01/Gate_Frame", False, (1.0, 0.65, 0.78), 0.12),
    ("Gate_Leaf_L.glb", "/Game/LuxGenerated/_Imports/G01_LeafL", "/Game/LuxGenerated/Gate_G01/Gate_Leaf_L", False, (1.0, 0.72, 0.85), 0.18),
    ("Gate_Leaf_R.glb", "/Game/LuxGenerated/_Imports/G01_LeafR", "/Game/LuxGenerated/Gate_G01/Gate_Leaf_R", False, (1.0, 0.72, 0.85), 0.18),
    ("StarGate_OuterRing.glb", "/Game/LuxGenerated/_Imports/G03_Outer", "/Game/LuxGenerated/Gate_G03/StarGate_OuterRing", False, (0.45, 0.85, 1.0), 0.25),
    ("StarGate_InnerRing.glb", "/Game/LuxGenerated/_Imports/G03_Inner", "/Game/LuxGenerated/Gate_G03/StarGate_InnerRing", False, (0.62, 0.92, 1.0), 0.55),
    ("Tunnel_Ring.glb", "/Game/LuxGenerated/_Imports/T01_Ring", "/Game/LuxGenerated/Tunnel_T01/Tunnel_Ring", False, (0.72, 0.88, 1.0), 0.65),
    ("Dream_Scale_Blade.glb", "/Game/LuxGenerated/_Imports/T02_Blade", "/Game/LuxGenerated/Scale_T02/Dream_Scale_Blade", False, (0.95, 0.80, 1.0), 0.85),
    ("Floating_Pavilion.glb", "/Game/LuxGenerated/_Imports/S01_Pavilion", "/Game/LuxGenerated/Pavilion_S01/Floating_Pavilion", True, (0.78, 0.90, 1.0), 0.14),
    ("Floating_Lantern.glb", "/Game/LuxGenerated/_Imports/W01_Lantern", "/Game/LuxGenerated/Props/Floating_Lantern", False, (1.0, 0.68, 0.30), 0.65),
    ("Crystal_Lotus.glb", "/Game/LuxGenerated/_Imports/W02_Lotus", "/Game/LuxGenerated/Props/Crystal_Lotus", False, (0.55, 0.90, 1.0), 0.45),
]


def flush_report() -> None:
    """Persist structured JSON report to Evidence directory."""
    REPORT_PATH.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_rot(pitch: float, yaw: float, roll: float = 0.0) -> unreal.Rotator:
    """Construct unreal.Rotator safely without positional (roll, pitch, yaw) ambiguity."""
    rot = unreal.Rotator()
    rot.pitch = float(pitch)
    rot.yaw = float(yaw)
    rot.roll = float(roll)
    return rot


def vec_to_list(v: unreal.Vector) -> list[float]:
    return [round(float(v.x), 3), round(float(v.y), 3), round(float(v.z), 3)]


def mesh_bounds_dict(mesh: unreal.StaticMesh) -> dict:
    box = mesh.get_bounding_box()
    size = box.max - box.min
    center = (box.min + box.max) * 0.5
    return {
        "min": vec_to_list(box.min),
        "max": vec_to_list(box.max),
        "size": vec_to_list(size),
        "center": vec_to_list(center),
    }


def safe_set_prop(obj: object, prop_name: str, value: object) -> bool:
    try:
        obj.set_editor_property(prop_name, value)
        return True
    except Exception as exc:
        REPORT["warnings"].append(f"set_editor_property({obj.get_name() if hasattr(obj, 'get_name') else obj}, {prop_name}) failed: {exc}")
        return False


def disable_nanite_and_save(mesh: unreal.StaticMesh, use_complex_collision: bool | None = None) -> bool:
    """Turn off Nanite on StaticMesh so -game never flags missing Nanite shader usage."""
    changed = False
    try:
        ns = mesh.get_editor_property("nanite_settings")
        if ns and ns.get_editor_property("enabled"):
            ns.set_editor_property("enabled", False)
            mesh.set_editor_property("nanite_settings", ns)
            changed = True
            REPORT["nanite_disabled"].append(mesh.get_path_name())
    except Exception as exc:
        REPORT["warnings"].append(f"Nanite check failed on {mesh.get_path_name()}: {exc}")

    if use_complex_collision is not None:
        try:
            if not use_complex_collision and hasattr(STATIC_MESH_SUB, "remove_collisions"):
                STATIC_MESH_SUB.remove_collisions(mesh)
            bs = mesh.get_editor_property("body_setup")
            if bs:
                if use_complex_collision:
                    bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
                else:
                    bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_DEFAULT)
                changed = True
        except Exception as exc:
            REPORT["warnings"].append(f"Collision setup note on {mesh.get_path_name()}: {exc}")

    if changed:
        try:
            mesh.modify()
            mesh.post_edit_change()
        except Exception:
            pass
        ASSET_SUB.save_loaded_asset(mesh, False)
    return changed


def tune_imported_mesh_materials(mesh: unreal.StaticMesh, glow_rgb: tuple[float, float, float], glow_strength: float) -> list[str]:
    """Boost subtle emissive glow on Interchange MaterialInstanceConstants when supported."""
    tuned = []
    lib = unreal.MaterialEditingLibrary
    mat_slots = mesh.get_editor_property("static_materials")
    for idx, slot in enumerate(mat_slots):
        mat = slot.material_interface
        if not mat:
            continue
        if isinstance(mat, unreal.MaterialInstanceConstant):
            try:
                vnames = [str(n) for n in lib.get_vector_parameter_names(mat)]
                snames = [str(n) for n in lib.get_scalar_parameter_names(mat)]
                em_color = unreal.LinearColor(glow_rgb[0] * glow_strength, glow_rgb[1] * glow_strength, glow_rgb[2] * glow_strength, 1.0)
                applied = False
                for cname in ("EmissiveColorFactor", "EmissiveColor", "Emissive_Color", "EmissiveFactor"):
                    if cname in vnames:
                        lib.set_material_instance_vector_parameter_value(mat, cname, em_color)
                        applied = True
                for sname in ("EmissiveStrength", "EmissiveScale", "Emissive_Strength"):
                    if sname in snames:
                        lib.set_material_instance_scalar_parameter_value(mat, sname, glow_strength)
                        applied = True
                if glow_strength >= 0.30:
                    if "IridescenceFactor" in snames:
                        lib.set_material_instance_scalar_parameter_value(mat, "IridescenceFactor", 0.78)
                        applied = True
                    if "IridescenceThicknessMaximum" in snames:
                        lib.set_material_instance_scalar_parameter_value(mat, "IridescenceThicknessMaximum", 620.0)
                        applied = True
                if not applied and glow_strength > 0.0:
                    # Fallback: slight BaseColorFactor lift for clean visibility
                    for bname in ("BaseColorFactor", "BaseColorTint"):
                        if bname in vnames:
                            cur = lib.get_material_instance_vector_parameter_value(mat, bname)
                            lift = 1.0 + min(glow_strength * 0.25, 0.2)
                            lib.set_material_instance_vector_parameter_value(
                                mat, bname, unreal.LinearColor(min(cur.r * lift, 1.5), min(cur.g * lift, 1.5), min(cur.b * lift, 1.5), cur.a)
                            )
                if applied:
                    lib.update_material_instance(mat)
                    ASSET_SUB.save_loaded_asset(mat, False)
                tuned.append(f"{mat.get_name()}[v={vnames},s={snames}]")
            except Exception as exc:
                REPORT["warnings"].append(f"Material tune warning {mat.get_path_name()}: {exc}")
        elif not glow_strength <= 0.0:
            tuned.append(f"{mat.get_name()}({type(mat).__name__})")
    return tuned


def set_viewport_camera(cam_loc: unreal.Vector, cam_rot: unreal.Rotator) -> None:
    """Set editor level viewport camera safely across UE5.8 subsystems."""
    try:
        UNREAL_EDITOR_SUB.set_level_viewport_camera_info(cam_loc, cam_rot)
        return
    except Exception:
        pass
    try:
        key = LEVEL_SUB.get_active_viewport_config_key() if hasattr(LEVEL_SUB, "get_active_viewport_config_key") else "LevelEditorViewport"
        LEVEL_SUB.set_level_viewport_camera_info(cam_loc, cam_rot, key)
    except Exception as exc:
        REPORT["warnings"].append(f"Viewport camera hint skipped: {exc}")


def step1_delete_f09() -> None:
    """Cut cheap F09 map and ThirdParty/F09 assets cleanly."""
    has_f09 = ASSET_SUB.does_asset_exist("/Game/Maps/F09_Unawakened") or ASSET_SUB.does_directory_exist("/Game/ThirdParty/F09")
    if has_f09:
        if ASSET_SUB.does_asset_exist("/Game/Maps/_ScratchBuild"):
            ASSET_SUB.delete_asset("/Game/Maps/_ScratchBuild")
        LEVEL_SUB.new_level("/Game/Maps/_ScratchBuild")
    if ASSET_SUB.does_asset_exist("/Game/Maps/F09_Unawakened"):
        if ASSET_SUB.delete_asset("/Game/Maps/F09_Unawakened"):
            REPORT["deleted"].append("/Game/Maps/F09_Unawakened")
        else:
            REPORT["warnings"].append("Could not delete /Game/Maps/F09_Unawakened")
    if ASSET_SUB.does_directory_exist("/Game/ThirdParty/F09"):
        if ASSET_SUB.delete_directory("/Game/ThirdParty/F09"):
            REPORT["deleted"].append("/Game/ThirdParty/F09")
        else:
            REPORT["warnings"].append("Could not delete /Game/ThirdParty/F09")


def step2_import_lux_assets() -> dict[str, unreal.StaticMesh]:
    """Import all 13 Lux3D GLBs and relocate meshes to exact C++ asset paths."""
    force_reimport = os.environ.get("LUX_FORCE_REIMPORT", "0") == "1"
    loaded_meshes: dict[str, unreal.StaticMesh] = {}

    if force_reimport and ASSET_SUB.does_directory_exist("/Game/LuxGenerated"):
        # Clear previous generated assets cleanly while _ScratchBuild is active
        ASSET_SUB.delete_directory("/Game/LuxGenerated")

    params = unreal.ImportAssetParameters()
    params.set_editor_property("is_automated", True)

    for glb_name, import_dir, target_path, use_complex, glow_rgb, glow_strength in LUX_ASSET_SPECS:
        glb_path = READY_DIR / glb_name
        if not glb_path.is_file():
            raise FileNotFoundError(f"Missing ready Lux3D GLB: {glb_path}")

        mesh: unreal.StaticMesh | None = None
        if ASSET_SUB.does_asset_exist(target_path):
            existing = ASSET_SUB.load_asset(target_path)
            if isinstance(existing, unreal.StaticMesh):
                mesh = existing

        if mesh is None:
            if ASSET_SUB.does_directory_exist(import_dir):
                ASSET_SUB.delete_directory(import_dir)
            src_data = INTERCHANGE_MGR.create_source_data(str(glb_path))
            if not src_data or not INTERCHANGE_MGR.can_translate_source_data(src_data):
                raise RuntimeError(f"Interchange cannot translate {glb_path}")
            imported_objs = INTERCHANGE_MGR.import_asset(import_dir, src_data, params) or []
            found_meshes = [o for o in imported_objs if isinstance(o, unreal.StaticMesh)]
            if not found_meshes:
                for p in ASSET_SUB.list_assets(import_dir, recursive=True):
                    cand = ASSET_SUB.load_asset(p)
                    if isinstance(cand, unreal.StaticMesh):
                        found_meshes.append(cand)
            if not found_meshes:
                raise RuntimeError(f"No StaticMesh produced from {glb_path} in {import_dir}")
            src_mesh = found_meshes[0]
            src_pkg = src_mesh.get_path_name().split(".")[0]
            if src_pkg != target_path:
                if ASSET_SUB.does_asset_exist(target_path):
                    ASSET_SUB.delete_asset(target_path)
                if not ASSET_SUB.rename_asset(src_pkg, target_path):
                    raise RuntimeError(f"Failed moving {src_pkg} -> {target_path}")
            mesh = ASSET_SUB.load_asset(target_path)
            if not isinstance(mesh, unreal.StaticMesh):
                raise RuntimeError(f"Relocated asset is not StaticMesh: {target_path}")

        disable_nanite_and_save(mesh, use_complex_collision=use_complex)
        mats_info = tune_imported_mesh_materials(mesh, glow_rgb, glow_strength)
        ASSET_SUB.save_loaded_asset(mesh, False)
        bounds = mesh_bounds_dict(mesh)
        REPORT["imported_meshes"][target_path] = {
            "source_glb": glb_name,
            "bounds": bounds,
            "materials": mats_info,
        }
        loaded_meshes[target_path] = mesh
        unreal.log(f"LUX_IMPORTED {target_path} size={bounds['size']} center={bounds['center']}")

    return loaded_meshes


def ensure_lux_custom_materials() -> dict[str, unreal.Material]:
    """Create procedural starry twilight sky dome + mirror obsidian star sea water materials."""
    mat_dir = "/Game/LuxGenerated/Materials"
    lib = unreal.MaterialEditingLibrary
    created: dict[str, unreal.Material] = {}

    def fresh_material(name: str) -> unreal.Material:
        pkg_path = f"{mat_dir}/{name}"
        if ASSET_SUB.does_asset_exist(pkg_path):
            ASSET_SUB.delete_asset(pkg_path)
        factory = unreal.MaterialFactoryNew()
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        mat = tools.create_asset(name, mat_dir, unreal.Material, factory)
        if not mat:
            raise RuntimeError(f"Failed to create material {pkg_path}")
        return mat

    # 1) M_Lux_StarSeaSkyDome: Unlit deep cosmic twilight gradient with shimmering star specks
    sky = fresh_material("M_Lux_StarSeaSkyDome")
    sky.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    sky.set_editor_property("two_sided", True)

    world_pos = lib.create_material_expression(sky, unreal.MaterialExpressionWorldPosition, -950, 0)
    norm_wp = lib.create_material_expression(sky, unreal.MaterialExpressionNormalize, -760, 0)
    lib.connect_material_expressions(world_pos, "", norm_wp, "VectorInput")

    mask_z = lib.create_material_expression(sky, unreal.MaterialExpressionComponentMask, -560, -140)
    mask_z.set_editor_property("r", False)
    mask_z.set_editor_property("g", False)
    mask_z.set_editor_property("b", True)
    lib.connect_material_expressions(norm_wp, "", mask_z, "")

    sat_z = lib.create_material_expression(sky, unreal.MaterialExpressionSaturate, -380, -140)
    lib.connect_material_expressions(mask_z, "", sat_z, "")

    pow_z = lib.create_material_expression(sky, unreal.MaterialExpressionPower, -220, -140)
    const_exp = lib.create_material_expression(sky, unreal.MaterialExpressionConstant, -380, -40)
    const_exp.set_editor_property("r", 0.58)
    lib.connect_material_expressions(sat_z, "", pow_z, "Base")
    lib.connect_material_expressions(const_exp, "", pow_z, "Exp")

    horizon_col = lib.create_material_expression(sky, unreal.MaterialExpressionVectorParameter, -420, -340)
    horizon_col.set_editor_property("parameter_name", "HorizonColor")
    horizon_col.set_editor_property("default_value", unreal.LinearColor(0.11, 0.06, 0.19, 1.0))

    zenith_col = lib.create_material_expression(sky, unreal.MaterialExpressionVectorParameter, -420, -220)
    zenith_col.set_editor_property("parameter_name", "ZenithColor")
    zenith_col.set_editor_property("default_value", unreal.LinearColor(0.012, 0.018, 0.065, 1.0))

    sky_lerp = lib.create_material_expression(sky, unreal.MaterialExpressionLinearInterpolate, -60, -240)
    lib.connect_material_expressions(horizon_col, "", sky_lerp, "A")
    lib.connect_material_expressions(zenith_col, "", sky_lerp, "B")
    lib.connect_material_expressions(pow_z, "", sky_lerp, "Alpha")

    # Star field via high-frequency VectorNoise on normalized sky direction
    mul_freq = lib.create_material_expression(sky, unreal.MaterialExpressionMultiply, -580, 140)
    star_freq = lib.create_material_expression(sky, unreal.MaterialExpressionConstant, -740, 220)
    star_freq.set_editor_property("r", 150.0)
    lib.connect_material_expressions(norm_wp, "", mul_freq, "A")
    lib.connect_material_expressions(star_freq, "", mul_freq, "B")

    noise = lib.create_material_expression(sky, unreal.MaterialExpressionNoise, -400, 140)
    noise.set_editor_property("noise_function", unreal.NoiseFunction.NOISEFUNCTION_VALUE_ALU)
    noise.set_editor_property("scale", 1.0)
    noise.set_editor_property("turbulence", False)
    lib.connect_material_expressions(mul_freq, "", noise, "Position")

    sat_star = lib.create_material_expression(sky, unreal.MaterialExpressionSaturate, -240, 140)
    lib.connect_material_expressions(noise, "", sat_star, "")

    pow_star = lib.create_material_expression(sky, unreal.MaterialExpressionPower, -90, 140)
    star_sharp = lib.create_material_expression(sky, unreal.MaterialExpressionConstant, -240, 240)
    star_sharp.set_editor_property("r", 34.0)
    lib.connect_material_expressions(sat_star, "", pow_star, "Base")
    lib.connect_material_expressions(star_sharp, "", pow_star, "Exp")

    mul_star = lib.create_material_expression(sky, unreal.MaterialExpressionMultiply, 80, 140)
    star_tint = lib.create_material_expression(sky, unreal.MaterialExpressionConstant3Vector, -80, 260)
    star_tint.set_editor_property("constant", unreal.LinearColor(1.4, 1.55, 2.2, 1.0))
    lib.connect_material_expressions(pow_star, "", mul_star, "A")
    lib.connect_material_expressions(star_tint, "", mul_star, "B")

    # Gate stars to upper hemisphere above horizon
    star_gate = lib.create_material_expression(sky, unreal.MaterialExpressionMultiply, 210, 60)
    lib.connect_material_expressions(mul_star, "", star_gate, "A")
    lib.connect_material_expressions(sat_z, "", star_gate, "B")

    sky_add = lib.create_material_expression(sky, unreal.MaterialExpressionAdd, 340, -60)
    lib.connect_material_expressions(sky_lerp, "", sky_add, "A")
    lib.connect_material_expressions(star_gate, "", sky_add, "B")
    lib.connect_material_property(sky_add, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.recompile_material(sky)
    ASSET_SUB.save_loaded_asset(sky, False)
    created["sky"] = sky

    # 2) M_Lux_StarWater: Mirror obsidian star-sea with gentle glowing aurora ripples
    water = fresh_material("M_Lux_StarWater")
    water.set_editor_property("two_sided", True)

    w_base = lib.create_material_expression(water, unreal.MaterialExpressionConstant3Vector, -280, -240)
    w_base.set_editor_property("constant", unreal.LinearColor(0.006, 0.012, 0.032, 1.0))
    lib.connect_material_property(w_base, "", unreal.MaterialProperty.MP_BASE_COLOR)

    w_metal = lib.create_material_expression(water, unreal.MaterialExpressionConstant, -280, -140)
    w_metal.set_editor_property("r", 0.35)
    lib.connect_material_property(w_metal, "", unreal.MaterialProperty.MP_METALLIC)

    w_spec = lib.create_material_expression(water, unreal.MaterialExpressionConstant, -280, -60)
    w_spec.set_editor_property("r", 0.92)
    lib.connect_material_property(w_spec, "", unreal.MaterialProperty.MP_SPECULAR)

    w_rough = lib.create_material_expression(water, unreal.MaterialExpressionConstant, -280, 20)
    w_rough.set_editor_property("r", 0.055)
    lib.connect_material_property(w_rough, "", unreal.MaterialProperty.MP_ROUGHNESS)

    # Soft time-animated bioluminescent starlight ripple in EmissiveColor
    w_wp = lib.create_material_expression(water, unreal.MaterialExpressionWorldPosition, -800, 180)
    w_time = lib.create_material_expression(water, unreal.MaterialExpressionTime, -800, 300)
    w_speed = lib.create_material_expression(water, unreal.MaterialExpressionConstant3Vector, -800, 380)
    w_speed.set_editor_property("constant", unreal.LinearColor(12.0, 9.0, 0.0, 1.0))
    w_pan = lib.create_material_expression(water, unreal.MaterialExpressionMultiply, -640, 300)
    lib.connect_material_expressions(w_time, "", w_pan, "A")
    lib.connect_material_expressions(w_speed, "", w_pan, "B")

    w_scroll = lib.create_material_expression(water, unreal.MaterialExpressionAdd, -480, 200)
    lib.connect_material_expressions(w_wp, "", w_scroll, "A")
    lib.connect_material_expressions(w_pan, "", w_scroll, "B")

    w_scale = lib.create_material_expression(water, unreal.MaterialExpressionMultiply, -340, 200)
    w_freq = lib.create_material_expression(water, unreal.MaterialExpressionConstant, -480, 290)
    w_freq.set_editor_property("r", 0.0028)
    lib.connect_material_expressions(w_scroll, "", w_scale, "A")
    lib.connect_material_expressions(w_freq, "", w_scale, "B")

    w_noise = lib.create_material_expression(water, unreal.MaterialExpressionNoise, -200, 200)
    w_noise.set_editor_property("noise_function", unreal.NoiseFunction.NOISEFUNCTION_VALUE_ALU)
    w_noise.set_editor_property("levels", 3)
    lib.connect_material_expressions(w_scale, "", w_noise, "Position")

    w_sat = lib.create_material_expression(water, unreal.MaterialExpressionSaturate, -40, 200)
    lib.connect_material_expressions(w_noise, "", w_sat, "")

    w_pow = lib.create_material_expression(water, unreal.MaterialExpressionPower, 100, 200)
    w_pexp = lib.create_material_expression(water, unreal.MaterialExpressionConstant, -40, 290)
    w_pexp.set_editor_property("r", 5.0)
    lib.connect_material_expressions(w_sat, "", w_pow, "Base")
    lib.connect_material_expressions(w_pexp, "", w_pow, "Exp")

    w_em = lib.create_material_expression(water, unreal.MaterialExpressionMultiply, 250, 200)
    w_glow = lib.create_material_expression(water, unreal.MaterialExpressionConstant3Vector, 90, 310)
    w_glow.set_editor_property("constant", unreal.LinearColor(0.06, 0.14, 0.28, 1.0))
    lib.connect_material_expressions(w_pow, "", w_em, "A")
    lib.connect_material_expressions(w_glow, "", w_em, "B")
    lib.connect_material_property(w_em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.recompile_material(water)
    ASSET_SUB.save_loaded_asset(water, False)
    created["water"] = water
    return created


def audit_and_normalize_gate(gate_actor: unreal.ButterflyDreamGateActor, target_floor_z: float, target_height_cm: float) -> dict:
    """Measure assembled gate frame bounds, normalize scale to target height, disable blocking collision."""
    comps = gate_actor.get_components_by_class(unreal.StaticMeshComponent)
    comp_records = []
    frame_unit_height = None
    frame_unit_min_z = 0.0

    for c in comps:
        c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        sm = c.static_mesh
        rel_loc = c.get_editor_property("relative_location")
        rel_rot = c.get_editor_property("relative_rotation")
        rel_scale = c.get_editor_property("relative_scale3d")
        rec = {
            "name": c.get_name(),
            "mesh": sm.get_path_name() if sm else None,
            "rel_loc": vec_to_list(rel_loc),
            "rel_rot": [round(float(rel_rot.pitch), 2), round(float(rel_rot.yaw), 2), round(float(rel_rot.roll), 2)],
            "rel_scale": vec_to_list(rel_scale),
        }
        if sm and ("GateFrame" in c.get_name() or frame_unit_height is None):
            box = sm.get_bounding_box()
            unit_h = float(box.max.z - box.min.z) * abs(float(rel_scale.z))
            if "GateFrame" in c.get_name() or unit_h > 10.0:
                frame_unit_height = unit_h
                frame_unit_min_z = float(box.min.z) * float(rel_scale.z) + float(rel_loc.z)
        comp_records.append(rec)

    scale_factor = float(target_height_cm) / max(frame_unit_height or 250.0, 1.0)
    gate_actor.set_actor_scale3d(unreal.Vector(scale_factor, scale_factor, scale_factor))
    loc = gate_actor.get_actor_location()
    loc.z = float(target_floor_z) - frame_unit_min_z * scale_factor
    gate_actor.set_actor_location(loc, False, False)
    return {"scale": round(scale_factor, 4), "location": vec_to_list(loc), "components": comp_records}


def step3_upgrade_f06(meshes: dict[str, unreal.StaticMesh]) -> None:
    """Clean, relight, and enhance F06_SakuraDream with Lux3D Sakura Gate & Lanterns."""
    map_path = "/Game/Maps/F06_SakuraDream"
    if not LEVEL_SUB.load_level(map_path):
        raise RuntimeError(f"Failed loading {map_path}")

    # Disable Nanite across ALL F06 static meshes so -game prints 0 Nanite missing-usage warnings
    if ASSET_SUB.does_directory_exist("/Game/ThirdParty/F06"):
        for ap in ASSET_SUB.list_assets("/Game/ThirdParty/F06", recursive=True):
            asset = ASSET_SUB.load_asset(ap)
            if isinstance(asset, unreal.StaticMesh):
                disable_nanite_and_save(asset)

    # Remove previous Lux spawns, broken PlayerStarts, and ugly Daisy spots
    all_actors = ACTOR_SUB.get_all_level_actors()
    daisy_removed = 0
    lantern_locs: list[unreal.Vector] = []
    stone_lantern_locs: list[unreal.Vector] = []
    pagoda_box: tuple[unreal.Vector, unreal.Vector] | None = None
    stairs_boxes: list[tuple[unreal.Vector, unreal.Vector]] = []

    for actor in all_actors:
        name = actor.get_name()
        label = actor.get_actor_label()
        if label.startswith("Lux_") or isinstance(actor, (unreal.PlayerStart, unreal.ButterflyDreamGateActor, unreal.ButterflyDreamPropActor)):
            ACTOR_SUB.destroy_actor(actor)
            continue

        if isinstance(actor, unreal.StaticMeshActor):
            smc = actor.static_mesh_component
            sm = smc.static_mesh if smc else None
            sm_path = sm.get_path_name() if sm else ""
            if "Daisy" in label or "Daisy" in name or "/Daisy" in sm_path:
                ACTOR_SUB.destroy_actor(actor)
                daisy_removed += 1
                continue
            origin, ext = actor.get_actor_bounds(False)
            bmin, bmax = origin - ext, origin + ext
            if "pagoda" in sm_path.lower() or "pagoda" in label.lower():
                if pagoda_box is None:
                    pagoda_box = (bmin, bmax)
                else:
                    pagoda_box = (
                        unreal.Vector(min(pagoda_box[0].x, bmin.x), min(pagoda_box[0].y, bmin.y), min(pagoda_box[0].z, bmin.z)),
                        unreal.Vector(max(pagoda_box[1].x, bmax.x), max(pagoda_box[1].y, bmax.y), max(pagoda_box[1].z, bmax.z)),
                    )
            if "01-stairs" in sm_path.lower() or "stair" in label.lower():
                stairs_boxes.append((bmin, bmax))

        elif isinstance(actor, unreal.PointLight):
            plc = actor.point_light_component
            loc = actor.get_actor_location()
            if "Lantern_point" in label or "Lantern_point" in name:
                lantern_locs.append(loc)
                plc.set_editor_property("intensity", 3800.0)
                plc.set_editor_property("attenuation_radius", 920.0)
                plc.set_editor_property("light_color", unreal.Color(255, 190, 112, 255))
                safe_set_prop(plc, "use_inverse_squared_falloff", False)
                safe_set_prop(plc, "light_falloff_exponent", 2.2)
            elif "Stone_lantern" in label or "Stone_lantern" in name:
                stone_lantern_locs.append(loc)
                plc.set_editor_property("intensity", 5200.0)
                plc.set_editor_property("attenuation_radius", 1250.0)
                plc.set_editor_property("light_color", unreal.Color(255, 206, 138, 255))
                safe_set_prop(plc, "use_inverse_squared_falloff", False)
            else:
                # Subtle Pagoda tier lights / ambient lanterns
                cur_int = plc.get_editor_property("intensity")
                plc.set_editor_property("intensity", max(cur_int * 8.0, 2600.0))
                plc.set_editor_property("attenuation_radius", max(plc.get_editor_property("attenuation_radius") * 2.5, 1100.0))
                plc.set_editor_property("light_color", unreal.Color(255, 182, 128, 255))
                safe_set_prop(plc, "use_inverse_squared_falloff", False)

        elif isinstance(actor, unreal.DirectionalLight):
            dlc = actor.light_component
            dlc.set_editor_property("intensity", 2.4)
            dlc.set_editor_property("light_color", unreal.Color(204, 212, 255, 255))

        elif isinstance(actor, unreal.SkyLight):
            slc = actor.light_component
            slc.set_editor_property("intensity", 1.8)
            slc.set_editor_property("light_color", unreal.Color(218, 204, 245, 255))

    # Enhance F06 Sakura petals & twilight sky material instances softly
    lib = unreal.MaterialEditingLibrary
    petal_mi = ASSET_SUB.load_asset("/Game/ThirdParty/F06/02-foliage/01-foliage/Materials/Material_001")
    if isinstance(petal_mi, unreal.MaterialInstanceConstant):
        vnames = [str(n) for n in lib.get_vector_parameter_names(petal_mi)]
        snames = [str(n) for n in lib.get_scalar_parameter_names(petal_mi)]
        if "BaseColorTint" in vnames:
            lib.set_material_instance_vector_parameter_value(petal_mi, "BaseColorTint", unreal.LinearColor(1.0, 0.72, 0.84, 1.0))
        if "EmissiveColor" in vnames:
            lib.set_material_instance_vector_parameter_value(petal_mi, "EmissiveColor", unreal.LinearColor(0.28, 0.14, 0.21, 1.0))
        elif "EmissiveColorFactor" in vnames:
            lib.set_material_instance_vector_parameter_value(petal_mi, "EmissiveColorFactor", unreal.LinearColor(0.24, 0.12, 0.19, 1.0))
        if "EmissiveStrength" in snames:
            lib.set_material_instance_scalar_parameter_value(petal_mi, "EmissiveStrength", 0.28)
        lib.update_material_instance(petal_mi)
        ASSET_SUB.save_loaded_asset(petal_mi, False)

    sky_mat = ASSET_SUB.load_asset("/Game/ThirdParty/F06/Custom/M_F06_SkyDome")
    if isinstance(sky_mat, (unreal.Material, unreal.MaterialInstanceConstant)):
        if isinstance(sky_mat, unreal.MaterialInstanceConstant):
            vnames = [str(n) for n in lib.get_vector_parameter_names(sky_mat)]
            if "ZenithColor" in vnames:
                lib.set_material_instance_vector_parameter_value(sky_mat, "ZenithColor", unreal.LinearColor(0.035, 0.045, 0.14, 1.0))
            if "HorizonColor" in vnames:
                lib.set_material_instance_vector_parameter_value(sky_mat, "HorizonColor", unreal.LinearColor(0.24, 0.15, 0.30, 1.0))
            lib.update_material_instance(sky_mat)
            ASSET_SUB.save_loaded_asset(sky_mat, False)

    # Derive staircase centerline & slope directly from Lantern_point / Stone_lantern world coordinates
    lantern_locs.sort(key=lambda v: v.y)
    stone_lantern_locs.sort(key=lambda v: v.y)
    if lantern_locs:
        x_mid = sum(v.x for v in lantern_locs) / len(lantern_locs)
        low_lanterns = lantern_locs[:2]
        high_lanterns = lantern_locs[-2:]
        low_y = sum(v.y for v in low_lanterns) / len(low_lanterns)
        low_z = sum(v.z for v in low_lanterns) / len(low_lanterns)
        high_y = sum(v.y for v in high_lanterns) / len(high_lanterns)
        high_z = sum(v.z for v in high_lanterns) / len(high_lanterns)
    else:
        x_mid, low_y, low_z, high_y, high_z = 0.0, -2400.0, -180.0, -400.0, 260.0

    terrace_y = sum(v.y for v in stone_lantern_locs) / len(stone_lantern_locs) if stone_lantern_locs else (high_y + 240.0)
    terrace_z = sum(v.z for v in stone_lantern_locs) / len(stone_lantern_locs) if stone_lantern_locs else (high_z + 40.0)

    # Note: Lantern_point height sits ~170 cm above step surface (from visual inspection of author-ue-round4.png)
    # Use helper linear interpolation along stairs for placing PlayerStart and flanking Floating Lanterns
    def stair_surface_z(y_val: float) -> float:
        denom = max(high_y - low_y, 1.0)
        alpha = max(0.0, min(1.2, (y_val - low_y) / denom))
        lantern_z = low_z + alpha * (high_z - low_z)
        return lantern_z - 155.0

    # Place clean PlayerStart at lower staircase facing +Y toward Pagoda & Moon
    spawn_y = low_y - 260.0
    spawn_z = stair_surface_z(spawn_y) + 150.0
    ps = ACTOR_SUB.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(x_mid, spawn_y, spawn_z), make_rot(0.0, 90.0, 0.0))
    ps.set_actor_label("Lux_F06_PlayerStart")

    # Compute exact Gate scale & placement on upper terrace before Pagoda so doors rest near terrace floor
    gate_frame_mesh = meshes["/Game/LuxGenerated/Gate_G01/Gate_Frame"]
    leaf_l_mesh = meshes["/Game/LuxGenerated/Gate_G01/Gate_Leaf_L"]
    leaf_r_mesh = meshes["/Game/LuxGenerated/Gate_G01/Gate_Leaf_R"]
    gf_box = gate_frame_mesh.get_bounding_box()

    # Check stone terrace floor near terrace_y (Stone_lantern Z - ~120 cm)
    gate_y = terrace_y + 80.0
    if pagoda_box:
        # Leave generous breathing room between Gate and Pagoda entrance
        gate_y = min(gate_y, pagoda_box[0].y - 320.0)
    gate_floor_z = terrace_z - 125.0
    gate_scale = 1.65  # ~418cm tall monument frame (~346cm wide) proportional to wide terrace & tall pagoda
    gate_z = gate_floor_z - gf_box.min.z * gate_scale

    gate_actor = ACTOR_SUB.spawn_actor_from_class(
        unreal.ButterflyDreamGateActor,
        unreal.Vector(x_mid, gate_y, gate_floor_z),
        make_rot(0.0, 90.0, 0.0),
    )
    gate_actor.set_actor_label("Lux_F06_SakuraDreamGate")
    gate_actor.apply_gate_preset(False)
    safe_set_prop(gate_actor, "TargetMapPackageName", "/Game/Maps/Lux_StarSeaDream")
    safe_set_prop(gate_actor, "ResonanceDistance", 2200.0)
    safe_set_prop(gate_actor, "TriggerTeleportDistance", 310.0)
    safe_set_prop(gate_actor, "PortalCenterLocalOffset", unreal.Vector(0.0, 0.0, (gf_box.min.z + gf_box.max.z) * 0.5))
    f06_gate_info = audit_and_normalize_gate(gate_actor, gate_floor_z, 420.0)

    # Flanking Lux3D W01 Floating Lanterns along the staircase edges
    lantern_mesh = meshes["/Game/LuxGenerated/Props/Floating_Lantern"]
    lotus_mesh = meshes["/Game/LuxGenerated/Props/Crystal_Lotus"]
    for idx in range(4):
        alpha = (idx + 0.5) / 4.0
        ly = low_y + alpha * (high_y - low_y)
        lz = stair_surface_z(ly) + 210.0
        for side in (-1.0, 1.0):
            lx = x_mid + side * 310.0
            prop = ACTOR_SUB.spawn_actor_from_class(unreal.ButterflyDreamPropActor, unreal.Vector(lx, ly, lz), make_rot(0.0, 0.0, 0.0))
            prop.set_actor_label(f"Lux_F06_FloatingLantern_{idx}_{'L' if side < 0 else 'R'}")
            prop.configure_prop(lantern_mesh, 1.45, True, unreal.LinearColor(1.0, 0.65, 0.28, 1.0), 3400.0, 820.0)
            safe_set_prop(prop, "PhaseOffset", float(idx) * 0.8 + (1.57 if side > 0 else 0.0))

    # Pair of Crystal Lotuses flanking the Lux3D Sakura Dream Gate on the upper terrace
    for side in (-1.0, 1.0):
        lotus = ACTOR_SUB.spawn_actor_from_class(
            unreal.ButterflyDreamPropActor,
            unreal.Vector(x_mid + side * 290.0, gate_y - 140.0, gate_floor_z + 32.0),
            make_rot(0.0, 0.0, 0.0),
        )
        lotus.set_actor_label(f"Lux_F06_CrystalLotus_{'L' if side < 0 else 'R'}")
        lotus.configure_prop(lotus_mesh, 5.5, True, unreal.LinearColor(0.55, 0.88, 1.0, 1.0), 2600.0, 750.0)
        safe_set_prop(lotus, "BobAmplitude", 10.0)
        safe_set_prop(lotus, "SpinSpeedYaw", 14.0)

    # Ensure WorldSettings uses ButterflyGameMode
    world = UNREAL_EDITOR_SUB.get_editor_world()
    if world:
        ws = world.get_world_settings()
        safe_set_prop(ws, "default_game_mode", unreal.ButterflyGameMode)

    # Set clean Editor Viewport Camera overlooking staircase, player butterfly spawn, gate & Pagoda + Moon
    cam_loc = unreal.Vector(x_mid, spawn_y - 380.0, spawn_z + 85.0)
    cam_rot = make_rot(7.5, 90.0, 0.0)
    set_viewport_camera(cam_loc, cam_rot)

    # Also ensure PPV / ExponentialHeightFog exist cleanly with non-crushed exposure
    ppvs = [a for a in ACTOR_SUB.get_all_level_actors() if isinstance(a, unreal.PostProcessVolume)]
    if not ppvs:
        ppv = ACTOR_SUB.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0), make_rot(0, 0, 0))
        ppv.set_actor_label("Lux_F06_PostProcess")
        safe_set_prop(ppv, "unbound", True)
        ppvs = [ppv]
    pp_settings = ppvs[0].get_editor_property("settings")
    safe_set_prop(pp_settings, "override_auto_exposure_min_brightness", True)
    safe_set_prop(pp_settings, "auto_exposure_min_brightness", 0.35)
    safe_set_prop(pp_settings, "override_auto_exposure_max_brightness", True)
    safe_set_prop(pp_settings, "auto_exposure_max_brightness", 1.8)
    safe_set_prop(pp_settings, "override_bloom_intensity", True)
    safe_set_prop(pp_settings, "bloom_intensity", 0.55)
    ppvs[0].set_editor_property("settings", pp_settings)

    if not LEVEL_SUB.save_current_level():
        raise RuntimeError("Failed saving upgraded F06_SakuraDream")

    REPORT["f06_metrics"] = {
        "daisy_removed": daisy_removed,
        "lantern_count": len(lantern_locs),
        "stone_lantern_count": len(stone_lantern_locs),
        "pagoda_box": [vec_to_list(pagoda_box[0]), vec_to_list(pagoda_box[1])] if pagoda_box else None,
        "player_start": vec_to_list(ps.get_actor_location()),
        "gate_info": f06_gate_info,
        "gate_frame_bounds": mesh_bounds_dict(gate_frame_mesh),
        "gate_leaf_l_bounds": mesh_bounds_dict(leaf_l_mesh),
        "gate_leaf_r_bounds": mesh_bounds_dict(leaf_r_mesh),
        "viewport_camera": {"location": vec_to_list(cam_loc), "rotation": [cam_rot.pitch, cam_rot.yaw, cam_rot.roll]},
    }


def step4_build_lux_starsea_dream(meshes: dict[str, unreal.StaticMesh], custom_mats: dict[str, unreal.Material]) -> None:
    """Create a StarSea prototype using Lux3D meshes and Unreal-authored effects."""
    map_path = "/Game/Maps/Lux_StarSeaDream"
    if ASSET_SUB.does_asset_exist(map_path):
        raise RuntimeError(f"Refusing to replace existing map {map_path}; preserve it and use an isolated working copy")
    if not LEVEL_SUB.new_level(map_path):
        raise RuntimeError(f"Failed creating {map_path}")

    sphere_mesh = ASSET_SUB.load_asset("/Engine/BasicShapes/Sphere")
    plane_mesh = ASSET_SUB.load_asset("/Engine/BasicShapes/Plane")

    # 1. Cosmic Twilight Starry SkyDome
    sky_actor = ACTOR_SUB.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0), make_rot(0, 0, 0))
    sky_actor.set_actor_label("Lux_StarSea_SkyDome")
    sky_smc = sky_actor.static_mesh_component
    sky_smc.set_static_mesh(sphere_mesh)
    sky_smc.set_material(0, custom_mats["sky"])
    sky_smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    sky_smc.set_cast_shadow(False)
    sky_actor.set_actor_scale3d(unreal.Vector(900.0, 900.0, 900.0))

    # 2. Obsidian Mirror Star Sea at Z = -140 cm
    sea_z = -140.0
    sea_actor = ACTOR_SUB.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 1200.0, sea_z), make_rot(0, 0, 0))
    sea_actor.set_actor_label("Lux_StarSea_Water")
    sea_smc = sea_actor.static_mesh_component
    sea_smc.set_static_mesh(plane_mesh)
    sea_smc.set_material(0, custom_mats["water"])
    sea_smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    sea_actor.set_actor_scale3d(unreal.Vector(700.0, 700.0, 1.0))

    # 3. Soft Moonlit Atmosphere & PostProcess
    dir_light = ACTOR_SUB.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 1200.0), make_rot(-28.0, 38.0, 0.0))
    dir_light.set_actor_label("Lux_StarSea_MoonKeyLight")
    dlc = dir_light.light_component
    dlc.set_editor_property("intensity", 2.6)
    dlc.set_editor_property("light_color", unreal.Color(198, 224, 255, 255))

    sky_light = ACTOR_SUB.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 1200.0), make_rot(0, 0, 0))
    sky_light.set_actor_label("Lux_StarSea_SkyLight")
    slc = sky_light.light_component
    slc.set_editor_property("intensity", 2.0)
    slc.set_editor_property("light_color", unreal.Color(175, 198, 255, 255))
    safe_set_prop(slc, "real_time_capture", True)

    fog = ACTOR_SUB.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, -80.0), make_rot(0, 0, 0))
    fog.set_actor_label("Lux_StarSea_Fog")
    fc = fog.component
    fc.set_editor_property("fog_density", 0.0045)
    fc.set_editor_property("fog_inscattering_luminance", unreal.LinearColor(0.075, 0.10, 0.24, 1.0))
    fc.set_editor_property("start_distance", 750.0)

    ppv = ACTOR_SUB.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0), make_rot(0, 0, 0))
    ppv.set_actor_label("Lux_StarSea_PostProcess")
    safe_set_prop(ppv, "unbound", True)
    pp = ppv.get_editor_property("settings")
    safe_set_prop(pp, "override_auto_exposure_min_brightness", True)
    safe_set_prop(pp, "auto_exposure_min_brightness", 0.35)
    safe_set_prop(pp, "override_auto_exposure_max_brightness", True)
    safe_set_prop(pp, "auto_exposure_max_brightness", 1.8)
    safe_set_prop(pp, "override_bloom_intensity", True)
    safe_set_prop(pp, "bloom_intensity", 0.65)
    ppv.set_editor_property("settings", pp)

    # 4. Hero Centerpiece: Floating Pavilion (S01) towering softly at the heart of the Star Sea
    pav_mesh = meshes["/Game/LuxGenerated/Pavilion_S01/Floating_Pavilion"]
    pav_box = pav_mesh.get_bounding_box()
    pav_size = pav_box.max - pav_box.min
    pav_scale = 2200.0 / max(pav_size.z, 1.0)  # Normalize to ~22 meters tall floating sanctuary!
    pav_y = 2600.0
    pav_z = sea_z + 180.0 - pav_box.min.z * pav_scale
    pav_actor = ACTOR_SUB.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0.0, pav_y, pav_z), make_rot(0.0, 90.0, 0.0))
    pav_actor.set_actor_label("Lux_StarSea_FloatingPavilion")
    pav_actor.static_mesh_component.set_static_mesh(pav_mesh)
    pav_actor.set_actor_scale3d(unreal.Vector(pav_scale, pav_scale, pav_scale))

    # Sanctuary inner/under glow lights illuminating Floating Pavilion
    pav_core_light = ACTOR_SUB.spawn_actor_from_class(unreal.PointLight, unreal.Vector(0.0, pav_y, sea_z + 650.0), make_rot(0, 0, 0))
    pav_core_light.set_actor_label("Lux_StarSea_PavilionCoreLight")
    pcl = pav_core_light.point_light_component
    pcl.set_editor_property("intensity", 24000.0)
    pcl.set_editor_property("attenuation_radius", 3800.0)
    pcl.set_editor_property("light_color", unreal.Color(150, 226, 255, 255))
    safe_set_prop(pcl, "use_inverse_squared_falloff", False)

    pav_eave_light = ACTOR_SUB.spawn_actor_from_class(unreal.PointLight, unreal.Vector(0.0, pav_y - 450.0, sea_z + 1250.0), make_rot(0, 0, 0))
    pav_eave_light.set_actor_label("Lux_StarSea_PavilionGoldRim")
    pel = pav_eave_light.point_light_component
    pel.set_editor_property("intensity", 16000.0)
    pel.set_editor_property("attenuation_radius", 3400.0)
    pel.set_editor_property("light_color", unreal.Color(255, 200, 145, 255))
    safe_set_prop(pel, "use_inverse_squared_falloff", False)

    # 5. Arrival PlayerStart overlooking the Floating Pavilion across lotus corridor
    spawn_loc = unreal.Vector(0.0, -1450.0, 140.0)
    ps = ACTOR_SUB.spawn_actor_from_class(unreal.PlayerStart, spawn_loc, make_rot(0.0, 90.0, 0.0))
    ps.set_actor_label("Lux_StarSea_PlayerStart")

    # 6. Return Rotary Star Gate (G03) positioned asymmetrically in left-midground so it frames cleanly
    outer_mesh = meshes["/Game/LuxGenerated/Gate_G03/StarGate_OuterRing"]
    star_gate = ACTOR_SUB.spawn_actor_from_class(unreal.ButterflyDreamGateActor, unreal.Vector(-520.0, -280.0, sea_z + 140.0), make_rot(0.0, 62.0, 0.0))
    star_gate.set_actor_label("Lux_StarSea_ReturnStarGate")
    star_gate.apply_gate_preset(True)
    safe_set_prop(star_gate, "TargetMapPackageName", "/Game/Maps/F06_SakuraDream")
    safe_set_prop(star_gate, "ResonanceDistance", 2200.0)
    safe_set_prop(star_gate, "TriggerTeleportDistance", 320.0)
    starsea_gate_info = audit_and_normalize_gate(star_gate, sea_z + 140.0, 480.0)

    # 7. Crystal Lotuses (W02) & Floating Lanterns (W01) & Orbiting Scale Blades (T02)
    lotus_mesh = meshes["/Game/LuxGenerated/Props/Crystal_Lotus"]
    lantern_mesh = meshes["/Game/LuxGenerated/Props/Floating_Lantern"]
    blade_mesh = meshes["/Game/LuxGenerated/Scale_T02/Dream_Scale_Blade"]

    lotus_scale = 120.0 / max((lotus_mesh.get_bounding_box().max - lotus_mesh.get_bounding_box().min).z, 1.0)
    lantern_scale = 115.0 / max((lantern_mesh.get_bounding_box().max - lantern_mesh.get_bounding_box().min).z, 1.0)
    blade_scale = 36.0 / max((blade_mesh.get_bounding_box().max - blade_mesh.get_bounding_box().min).z, 1.0)

    # Giant Lotus cradle directly beneath Floating Pavilion + stepping lotuses along corridor
    cradle = ACTOR_SUB.spawn_actor_from_class(unreal.ButterflyDreamPropActor, unreal.Vector(0.0, pav_y, sea_z + 20.0), make_rot(0, 0, 0))
    cradle.set_actor_label("Lux_StarSea_GiantPavilionLotus")
    cradle.configure_prop(lotus_mesh, lotus_scale * 4.2, True, unreal.LinearColor(0.45, 0.88, 1.0, 1.0), 8500.0, 1800.0)
    safe_set_prop(cradle, "BobAmplitude", 8.0)
    safe_set_prop(cradle, "SpinSpeedYaw", 4.5)

    for idx in range(6):
        t = idx / 5.0
        angle = t * 1.45 * math.pi
        for side in (-1.0, 1.0):
            x = side * (360.0 + 260.0 * math.sin(angle * 0.7))
            y = -850.0 + t * 2700.0
            lotus = ACTOR_SUB.spawn_actor_from_class(
                unreal.ButterflyDreamPropActor,
                unreal.Vector(x, y, sea_z + 32.0 + (idx % 2) * 26.0),
                make_rot(0.0, float(idx) * 35.0, 0.0),
            )
            lotus.set_actor_label(f"Lux_StarSea_Lotus_{idx}_{'L' if side < 0 else 'R'}")
            lotus.configure_prop(
                lotus_mesh,
                lotus_scale * (1.1 + 0.15 * (idx % 3)),
                True,
                unreal.LinearColor(0.55, 0.88, 1.0, 1.0) if idx % 2 == 0 else unreal.LinearColor(0.95, 0.65, 0.90, 1.0),
                2400.0,
                750.0,
            )
            safe_set_prop(lotus, "PhaseOffset", float(idx) * 0.6 + (1.2 if side > 0 else 0.0))

            lantern = ACTOR_SUB.spawn_actor_from_class(
                unreal.ButterflyDreamPropActor,
                unreal.Vector(x * 1.18, y + 180.0, sea_z + 340.0 + 95.0 * math.sin(idx * 1.1)),
                make_rot(0.0, 0.0, 0.0),
            )
            lantern.set_actor_label(f"Lux_StarSea_Lantern_{idx}_{'L' if side < 0 else 'R'}")
            lantern.configure_prop(lantern_mesh, lantern_scale, True, unreal.LinearColor(1.0, 0.72, 0.38, 1.0), 3200.0, 880.0)
            safe_set_prop(lantern, "BobAmplitude", 28.0)
            safe_set_prop(lantern, "PhaseOffset", float(idx) * 0.9 + (0.7 if side > 0 else 0.0))

    # Spiral stream of Dream Scale Blades rising toward Floating Pavilion
    for idx in range(18):
        u = idx / 17.0
        theta = u * 3.5 * math.pi
        rad = 420.0 + 380.0 * math.sin(u * math.pi)
        bx = math.cos(theta) * rad
        by = -400.0 + u * 2800.0
        bz = 120.0 + u * 620.0 + 80.0 * math.sin(theta * 2.0)
        blade = ACTOR_SUB.spawn_actor_from_class(
            unreal.ButterflyDreamPropActor,
            unreal.Vector(bx, by, bz),
            make_rot(15.0 * math.sin(theta), theta * 57.3, 18.0),
        )
        blade.set_actor_label(f"Lux_StarSea_ScaleBlade_{idx}")
        blade.configure_prop(blade_mesh, blade_scale, False, unreal.LinearColor(0.85, 0.92, 1.0, 1.0), 0.0, 0.0)
        safe_set_prop(blade, "BobAmplitude", 36.0)
        safe_set_prop(blade, "SpinSpeedYaw", 65.0)
        safe_set_prop(blade, "PhaseOffset", float(idx) * 0.5)

    world = UNREAL_EDITOR_SUB.get_editor_world()
    if world:
        safe_set_prop(world.get_world_settings(), "default_game_mode", unreal.ButterflyGameMode)

    cam_loc = unreal.Vector(-180.0, -1820.0, 260.0)
    cam_rot = make_rot(6.0, 82.0, 0.0)
    set_viewport_camera(cam_loc, cam_rot)

    if not LEVEL_SUB.save_current_level():
        raise RuntimeError(f"Failed saving {map_path}")

    REPORT["lux_starsea_metrics"] = {
        "pavilion_bounds": mesh_bounds_dict(pav_mesh),
        "pavilion_scale": round(pav_scale, 3),
        "pavilion_location": vec_to_list(pav_actor.get_actor_location()),
        "star_gate_outer_bounds": mesh_bounds_dict(outer_mesh),
        "star_gate_info": starsea_gate_info,
        "player_start": vec_to_list(ps.get_actor_location()),
        "viewport_camera": {"location": vec_to_list(cam_loc), "rotation": [cam_rot.pitch, cam_rot.yaw, cam_rot.roll]},
    }



def main() -> None:
    try:
        project_dir = Path(unreal.Paths.project_dir()).resolve()
        expected_dir = (ROOT / "Unreal" / "ButterflyDream_LuxWork").resolve()
        if project_dir != expected_dir:
            raise RuntimeError(f"Refusing to run outside the isolated working copy: {project_dir}")
        meshes = {}
        for _, _, path, _, _, _ in LUX_ASSET_SPECS:
            obj = ASSET_SUB.load_asset(path)
            if not isinstance(obj, unreal.StaticMesh):
                raise RuntimeError(f"Missing imported official asset: {path}")
            meshes[path] = obj
        custom_mats = {
            "sky": ASSET_SUB.load_asset("/Game/LuxGenerated/Materials/M_Lux_StarSeaSkyDome"),
            "water": ASSET_SUB.load_asset("/Game/LuxGenerated/Materials/M_Lux_StarWater"),
        }
        if not all(custom_mats.values()):
            raise RuntimeError("Missing existing star sea materials")
        step4_build_lux_starsea_dream(meshes, custom_mats)
        REPORT["status"] = "SUCCEEDED"
    except Exception as exc:
        import traceback
        REPORT["status"] = "FAILED"
        REPORT["errors"].append(f"{exc}\n{traceback.format_exc()}")
        unreal.log_error(f"LUX_RECOVERY_FAILED: {exc}\n{traceback.format_exc()}")
    finally:
        flush_report()
        unreal.log(f"LUX_RECOVERY_DONE status={REPORT['status']} report={REPORT_PATH}")
        unreal.SystemLibrary.quit_editor()

main()
