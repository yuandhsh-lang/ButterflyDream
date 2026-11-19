"""Rebuild ButterflyDream UE 5.8 project with Wave-2 V2 300k G1 Lux3D assets & 360 Aurora Panorama.

Actions performed inside UnrealEditor-Cmd.exe:
1. Open or create /Game/Maps/_ScratchBuild in the isolated V2 preview project; remove legacy F09 if present.
2. Import all 15 V2 300k G1 GLBs + V1 Dream_Scale_Blade.glb, retaining the last completed import on retry,
   into exact C++ ConstructorHelpers paths plus /Game/LuxGenerated/Sanctuary/{Celestial_Bridge,
   Celestial_Guardian, Dragon_Pillar}.
3. Disable Nanite on EVERY StaticMesh in /Game/LuxGenerated and /Game/ThirdParty/F06 (nanite_missing_usage=0).
4. Tune Interchange MaterialInstanceConstants preserving 2K V2 PBR textures while giving stained-glass wings,
   Crystal_Lotus, Floating_Lantern, Tunnel_Ring, and StarGate_InnerRing rich non-blown-out luminescence.
5. Import World_OutdoorAuroraSanctuary_3FO4K4REJBX6_pano.jpg -> /Game/LuxGenerated/Materials/T_OutdoorAuroraPano
   and build M_Lux_StarSeaSkyDome (MaterialExpressionCustom equirectangular HLSL + TextureSample) +
   mirror-reflective M_Lux_StarWater (roughness 0.04).
6. Upgrade /Game/Maps/F06_SakuraDream (V2 flying-eaves G01 gate with exact URDF hinge offsets, twin monumental
   Dragon_Pillars at staircase entrance, V2 Floating_Lanterns, twin Celestial_Guardian phoenixes + Crystal_Lotuses,
   calibrated Candelas lighting & PostProcess exposure).
7. Author /Game/Maps/Lux_StarSeaDream (360 Aurora SkyDome + Mirror Star-Sea, 22m Floating_Pavilion S01 + Giant
   Crystal_Lotus cradle, central 9.5m Celestial_Bridge S02, 6-column Dragon_Pillar P01 colonnade with pearl lights,
   left-midground Return G03 StarGate with exact URDF offsets, right-midground Celestial_Guardian S03 + forecourt
   twin phoenixes, Floating_Lanterns, Crystal_Lotus water pads, and rising Dream_Scale_Blade spiral).
8. Emit Evidence/Unreal/LuxRebuild/v2-preview-rebuild-report.json.
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
    "custom_materials": {},
    "nanite_disabled": [],
    "f06_metrics": {},
    "lux_starsea_metrics": {},
    "warnings": [],
    "errors": [],
}


def resolve_project_root() -> Path:
    """Resolve ASCII V: mount root when available, else repo root."""
    if Path("V:/Assets/LuxGenerated").is_dir():
        return Path("V:/")
    return Path(__file__).resolve().parents[2]


ROOT = resolve_project_root()
LUX_ROOT = ROOT / "Assets" / "LuxGenerated"
PANO_SOURCE_JPG = LUX_ROOT / "V2_Sanctuary" / "World_OutdoorAuroraSanctuary_3FO4K4REJBX6_pano.jpg"
EVIDENCE_DIR = ROOT / "Evidence" / "Unreal" / "LuxRebuild"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
PROJECT_DIR = Path(unreal.Paths.project_dir()).resolve()
REPORT_PATH = EVIDENCE_DIR / "v2-preview-rebuild-report.json"
REPORT_PATH_COMPAT = EVIDENCE_DIR / "rebuild-report.json"  # backward compat
IMPORT_CHECKPOINT = PROJECT_DIR / "Saved" / "LuxV2Imports.json"
SCRATCH_MAP = "/Game/Maps/_ScratchBuild"

LEVEL_SUB = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ASSET_SUB = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
ACTOR_SUB = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
UNREAL_EDITOR_SUB = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
STATIC_MESH_SUB = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
INTERCHANGE_MGR = unreal.InterchangeManager.get_interchange_manager_scripted()


# (rel_path_under_LuxGenerated, import_pkg_dir, target_mesh_path, complex_collision,
#  glow_rgb, glow_strength, use_basecolor_as_emissive_fallback, roughness_scale, metallic_override)
LUX_ASSET_SPECS = [
    # V2 Butterfly (has bespoke 1024 selective EmissiveTexture + MetallicRoughness)
    (
        "V2_Butterfly/Ready/Butterfly_Body.glb",
        "/Game/LuxGenerated/_Imports/B01_Body",
        "/Game/LuxGenerated/Butterfly_B01/Butterfly_Body",
        False,
        (1.00, 0.92, 0.78),
        0.26,
        False,
        0.84,
        None,
    ),
    (
        "V2_Butterfly/Ready/Wing_L.glb",
        "/Game/LuxGenerated/_Imports/B01_WingL",
        "/Game/LuxGenerated/Butterfly_B01/Wing_L",
        False,
        (1.00, 1.00, 1.00),
        0.92,
        False,
        0.82,
        None,
    ),
    (
        "V2_Butterfly/Ready/Wing_R.glb",
        "/Game/LuxGenerated/_Imports/B01_WingR",
        "/Game/LuxGenerated/Butterfly_B01/Wing_R",
        False,
        (1.00, 1.00, 1.00),
        0.92,
        False,
        0.82,
        None,
    ),
    # V2 Gates (all 6 have bespoke selective EmissiveTexture + 24K Gold/Jade MetallicRoughness)
    (
        "V2_Gates/Ready/Gate_Frame.glb",
        "/Game/LuxGenerated/_Imports/G01_Frame",
        "/Game/LuxGenerated/Gate_G01/Gate_Frame",
        False,
        (1.00, 0.95, 0.90),
        1.05,
        False,
        0.88,
        None,
    ),
    (
        "V2_Gates/Ready/Gate_Leaf_L.glb",
        "/Game/LuxGenerated/_Imports/G01_LeafL",
        "/Game/LuxGenerated/Gate_G01/Gate_Leaf_L",
        False,
        (1.00, 0.96, 0.95),
        1.22,
        False,
        0.84,
        None,
    ),
    (
        "V2_Gates/Ready/Gate_Leaf_R.glb",
        "/Game/LuxGenerated/_Imports/G01_LeafR",
        "/Game/LuxGenerated/Gate_G01/Gate_Leaf_R",
        False,
        (1.00, 0.96, 0.95),
        1.22,
        False,
        0.84,
        None,
    ),
    (
        "V2_Gates/Ready/StarGate_OuterRing.glb",
        "/Game/LuxGenerated/_Imports/G03_Outer",
        "/Game/LuxGenerated/Gate_G03/StarGate_OuterRing",
        False,
        (0.90, 0.98, 1.04),
        1.18,
        False,
        0.85,
        None,
    ),
    (
        "V2_Gates/Ready/StarGate_InnerRing.glb",
        "/Game/LuxGenerated/_Imports/G03_Inner",
        "/Game/LuxGenerated/Gate_G03/StarGate_InnerRing",
        False,
        (1.04, 0.94, 0.82),
        1.55,
        False,
        0.82,
        None,
    ),
    (
        "V2_Gates/Ready/Tunnel_Ring.glb",
        "/Game/LuxGenerated/_Imports/T01_Ring",
        "/Game/LuxGenerated/Tunnel_T01/Tunnel_Ring",
        False,
        (1.02, 0.94, 0.96),
        1.65,
        False,
        0.82,
        None,
    ),
    # Kept V1 Scale Blade mote
    (
        "Ready/Dream_Scale_Blade.glb",
        "/Game/LuxGenerated/_Imports/T02_Blade",
        "/Game/LuxGenerated/Scale_T02/Dream_Scale_Blade",
        False,
        (0.88, 0.92, 1.08),
        0.76,
        True,
        0.75,
        0.25,
    ),
    # V2 Sanctuary Architecture, Hero Monuments & Props (2048 PBR BaseColor + MetallicRoughness)
    (
        "V2_Sanctuary/Ready/Floating_Pavilion.glb",
        "/Game/LuxGenerated/_Imports/S01_Pavilion",
        "/Game/LuxGenerated/Pavilion_S01/Floating_Pavilion",
        True,
        (0.96, 0.98, 1.02),
        0.13,
        True,
        0.86,
        0.28,
    ),
    (
        "V2_Sanctuary/Ready/Celestial_Bridge.glb",
        "/Game/LuxGenerated/_Imports/S02_Bridge",
        "/Game/LuxGenerated/Sanctuary/Celestial_Bridge",
        True,
        (0.84, 0.98, 1.05),
        0.21,
        True,
        0.78,
        0.26,
    ),
    (
        "V2_Sanctuary/Ready/Celestial_Guardian.glb",
        "/Game/LuxGenerated/_Imports/S03_Guardian",
        "/Game/LuxGenerated/Sanctuary/Celestial_Guardian",
        False,
        (1.02, 0.95, 0.88),
        0.20,
        True,
        0.76,
        0.42,
    ),
    (
        "V2_Sanctuary/Ready/Dragon_Pillar.glb",
        "/Game/LuxGenerated/_Imports/P01_DragonPillar",
        "/Game/LuxGenerated/Sanctuary/Dragon_Pillar",
        False,
        (0.98, 0.96, 0.94),
        0.15,
        True,
        0.82,
        0.32,
    ),
    (
        "V2_Sanctuary/Ready/Floating_Lantern.glb",
        "/Game/LuxGenerated/_Imports/W01_Lantern",
        "/Game/LuxGenerated/Props/Floating_Lantern",
        False,
        (1.06, 0.84, 0.52),
        0.48,
        True,
        0.80,
        0.38,
    ),
    (
        "V2_Sanctuary/Ready/Crystal_Lotus.glb",
        "/Game/LuxGenerated/_Imports/W02_Lotus",
        "/Game/LuxGenerated/Props/Crystal_Lotus",
        False,
        (0.84, 0.98, 1.06),
        0.42,
        True,
        0.74,
        0.30,
    ),
]


def flush_report() -> None:
    """Persist structured JSON report to Evidence directory."""
    report_json = json.dumps(REPORT, ensure_ascii=False, indent=2) + "\n"
    REPORT_PATH.write_text(report_json, encoding="utf-8")
    REPORT_PATH_COMPAT.write_text(report_json, encoding="utf-8")


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
        REPORT["warnings"].append(
            f"set_editor_property({obj.get_name() if hasattr(obj, 'get_name') else obj}, {prop_name}) failed: {exc}"
        )
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
        except Exception:
            pass
        ASSET_SUB.save_loaded_asset(mesh, False)
    return changed


def tune_imported_mesh_materials(
    mesh: unreal.StaticMesh,
    glow_rgb: tuple[float, float, float],
    glow_strength: float,
    use_basecolor_as_emissive_fallback: bool,
    roughness_scale: float | None = None,
    metallic_override: float | None = None,
) -> list[str]:
    """Tune Interchange MaterialInstanceConstants while preserving crisp 2K V2 PBR textures."""
    tuned = []
    lib = unreal.MaterialEditingLibrary
    mat_slots = mesh.get_editor_property("static_materials")
    for slot in mat_slots:
        mat = slot.material_interface
        if not mat:
            continue
        if isinstance(mat, unreal.MaterialInstanceConstant):
            try:
                vnames = [str(n) for n in lib.get_vector_parameter_names(mat)]
                snames = [str(n) for n in lib.get_scalar_parameter_names(mat)]
                tnames = [str(n) for n in lib.get_texture_parameter_names(mat)]
                applied = False

                # Ensure BaseColorFactor stays neutral white (1,1,1,1) so 2048 PBR textures are never washed out
                if "BaseColorFactor" in vnames:
                    lib.set_material_instance_vector_parameter_value(
                        mat, "BaseColorFactor", unreal.LinearColor(1.0, 1.0, 1.0, 1.0)
                    )
                    applied = True

                # Prevent zeroed R-channel in packed MetallicRoughness from darkening ambient occlusion
                if use_basecolor_as_emissive_fallback and "OcclusionStrength" in snames:
                    lib.set_material_instance_scalar_parameter_value(mat, "OcclusionStrength", 0.0)
                    applied = True

                if roughness_scale is not None and "RoughnessFactor" in snames:
                    lib.set_material_instance_scalar_parameter_value(mat, "RoughnessFactor", float(roughness_scale))
                    applied = True

                if metallic_override is not None and "MetallicFactor" in snames:
                    lib.set_material_instance_scalar_parameter_value(mat, "MetallicFactor", float(metallic_override))
                    applied = True

                # For assets without a dedicated EmissiveTexture, bind BaseColorTexture into EmissiveTexture
                # so emissive glow carries full 2048x2048 texture detail instead of adding a flat solid color wash!
                if use_basecolor_as_emissive_fallback and "BaseColorTexture" in tnames and "EmissiveTexture" in tnames:
                    base_tex = lib.get_material_instance_texture_parameter_value(mat, "BaseColorTexture")
                    if base_tex:
                        lib.set_material_instance_texture_parameter_value(mat, "EmissiveTexture", base_tex)
                        applied = True

                # When EmissiveTexture is present, EmissiveFactor acts as clean RGB tint & EmissiveStrength scales intensity
                em_factor = unreal.LinearColor(float(glow_rgb[0]), float(glow_rgb[1]), float(glow_rgb[2]), 1.0)
                for cname in ("EmissiveFactor", "EmissiveColorFactor", "EmissiveColor", "Emissive_Color"):
                    if cname in vnames:
                        lib.set_material_instance_vector_parameter_value(mat, cname, em_factor)
                        applied = True

                for sname in ("EmissiveStrength", "EmissiveScale", "Emissive_Strength"):
                    if sname in snames:
                        lib.set_material_instance_scalar_parameter_value(mat, sname, float(glow_strength))
                        applied = True

                if glow_strength >= 0.35:
                    if "IridescenceFactor" in snames:
                        lib.set_material_instance_scalar_parameter_value(mat, "IridescenceFactor", 0.72)
                        applied = True
                    if "IridescenceThicknessMaximum" in snames:
                        lib.set_material_instance_scalar_parameter_value(mat, "IridescenceThicknessMaximum", 620.0)
                        applied = True

                if applied:
                    lib.update_material_instance(mat)
                    ASSET_SUB.save_loaded_asset(mat, False)
                tuned.append(f"{mat.get_name()}[tex={tnames},em={glow_strength}]")
            except Exception as exc:
                REPORT["warnings"].append(f"Material tune warning {mat.get_path_name()}: {exc}")
        else:
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
        key = (
            LEVEL_SUB.get_active_viewport_config_key()
            if hasattr(LEVEL_SUB, "get_active_viewport_config_key")
            else "LevelEditorViewport"
        )
        LEVEL_SUB.set_level_viewport_camera_info(cam_loc, cam_rot, key)
    except Exception as exc:
        REPORT["warnings"].append(f"Viewport camera hint skipped: {exc}")


def step1_open_scratch_and_clean() -> None:
    """Open or create a scratch map so no real map holds locks on /Game/LuxGenerated.
    Tolerates -nullrhi failures: if we can't create/load _ScratchBuild, we continue anyway."""
    scratch_ok = False
    if ASSET_SUB.does_asset_exist(SCRATCH_MAP):
        scratch_ok = LEVEL_SUB.load_level(SCRATCH_MAP)
        if not scratch_ok:
            REPORT["warnings"].append(f"Could not load existing {SCRATCH_MAP}, continuing anyway")
    else:
        scratch_ok = LEVEL_SUB.new_level(SCRATCH_MAP)
        if not scratch_ok:
            REPORT["warnings"].append(f"Could not create {SCRATCH_MAP} (expected in -nullrhi), continuing anyway")

    if ASSET_SUB.does_asset_exist("/Game/Maps/F09_Unawakened"):
        if ASSET_SUB.delete_asset("/Game/Maps/F09_Unawakened"):
            REPORT["deleted"].append("/Game/Maps/F09_Unawakened")
    if ASSET_SUB.does_directory_exist("/Game/ThirdParty/F09"):
        if ASSET_SUB.delete_directory("/Game/ThirdParty/F09"):
            REPORT["deleted"].append("/Game/ThirdParty/F09")


def step2_import_lux_v2_assets() -> dict[str, unreal.StaticMesh]:
    """Replace V1 meshes with V2 meshes at their runtime paths, saving progress after each import."""
    checkpoint = json.loads(IMPORT_CHECKPOINT.read_text(encoding="utf-8")) if IMPORT_CHECKPOINT.is_file() else {}
    REPORT["imported_meshes"] = checkpoint
    loaded_meshes: dict[str, unreal.StaticMesh] = {}
    params = unreal.ImportAssetParameters()
    params.set_editor_property("is_automated", True)

    for (
        rel_glb,
        import_dir,
        target_path,
        use_complex,
        glow_rgb,
        glow_strength,
        use_bc_emissive,
        rough_scale,
        metal_ovr,
    ) in LUX_ASSET_SPECS:
        glb_path = LUX_ROOT / rel_glb
        if not glb_path.is_file():
            raise FileNotFoundError(f"Missing ready Lux3D GLB: {glb_path}")

        fingerprint = {"size": glb_path.stat().st_size, "mtime_ns": glb_path.stat().st_mtime_ns}
        previous = checkpoint.get(target_path, {})
        if previous.get("fingerprint") == fingerprint:
            existing = ASSET_SUB.load_asset(target_path)
            if isinstance(existing, unreal.StaticMesh):
                loaded_meshes[target_path] = existing
                continue

        import_dir = import_dir.replace("/_Imports/", "/_V2Imports/")
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
            if ASSET_SUB.does_asset_exist(target_path) and not ASSET_SUB.delete_asset(target_path):
                raise RuntimeError(f"Cannot replace previous mesh at {target_path}")
            if not ASSET_SUB.rename_asset(src_pkg, target_path):
                raise RuntimeError(f"Failed moving {src_pkg} -> {target_path}")

        mesh = ASSET_SUB.load_asset(target_path)
        if not isinstance(mesh, unreal.StaticMesh):
            raise RuntimeError(f"Relocated asset is not StaticMesh: {target_path}")

        disable_nanite_and_save(mesh, use_complex_collision=use_complex)
        mats_info = tune_imported_mesh_materials(
            mesh, glow_rgb, glow_strength, use_bc_emissive, rough_scale, metal_ovr
        )
        if not ASSET_SUB.save_directory(import_dir, True, True):
            raise RuntimeError(f"Failed saving imported dependencies in {import_dir}")
        if not ASSET_SUB.save_loaded_asset(mesh, False):
            raise RuntimeError(f"Failed saving {target_path}")
        bounds = mesh_bounds_dict(mesh)
        REPORT["imported_meshes"][target_path] = {
            "source_glb": rel_glb,
            "fingerprint": fingerprint,
            "bounds": bounds,
            "materials": mats_info,
        }
        IMPORT_CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
        IMPORT_CHECKPOINT.write_text(json.dumps(checkpoint, indent=2) + "\n", encoding="utf-8")
        loaded_meshes[target_path] = mesh
        unreal.log(f"LUX_V2_IMPORTED {target_path} from {rel_glb} size={bounds['size']} center={bounds['center']}")

    # Sweep all StaticMeshes under /Game/LuxGenerated just in case any auxiliary mesh had Nanite enabled
    for ap in ASSET_SUB.list_assets("/Game/LuxGenerated", recursive=True):
        cand = ASSET_SUB.load_asset(ap)
        if isinstance(cand, unreal.StaticMesh):
            disable_nanite_and_save(cand)

    return loaded_meshes


def import_aurora_panorama_texture(mat_dir: str) -> unreal.Texture2D:
    """Import World_OutdoorAuroraSanctuary_3FO4K4REJBX6_pano.jpg -> /Game/LuxGenerated/Materials/T_OutdoorAuroraPano."""
    if not PANO_SOURCE_JPG.is_file():
        raise FileNotFoundError(f"Missing aurora panorama JPG: {PANO_SOURCE_JPG}")

    target_pkg = f"{mat_dir}/T_OutdoorAuroraPano"
    if ASSET_SUB.does_asset_exist(target_pkg):
        ASSET_SUB.delete_asset(target_pkg)

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(PANO_SOURCE_JPG))
    task.set_editor_property("destination_path", mat_dir)
    task.set_editor_property("destination_name", "T_OutdoorAuroraPano")
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("automated", True)
    task.set_editor_property("save", True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    tex = ASSET_SUB.load_asset(target_pkg)
    if not isinstance(tex, unreal.Texture2D):
        # Fallback via Interchange if AssetImportTask delegated differently
        tmp_dir = "/Game/LuxGenerated/_Imports/PanoSky"
        src_data = INTERCHANGE_MGR.create_source_data(str(PANO_SOURCE_JPG))
        params = unreal.ImportAssetParameters()
        params.set_editor_property("is_automated", True)
        objs = INTERCHANGE_MGR.import_asset(tmp_dir, src_data, params) or []
        tex_cands = [o for o in objs if isinstance(o, unreal.Texture2D)]
        if not tex_cands:
            raise RuntimeError(f"Failed importing panorama texture {PANO_SOURCE_JPG}")
        src_pkg = tex_cands[0].get_path_name().split(".")[0]
        ASSET_SUB.rename_asset(src_pkg, target_pkg)
        tex = ASSET_SUB.load_asset(target_pkg)

    if not isinstance(tex, unreal.Texture2D):
        raise RuntimeError(f"Expected Texture2D at {target_pkg}")

    # Disable mipmaps & clamp vertical axis so atan2 horizontal wrap has ZERO mip seam across 1.0 -> 0.0!
    safe_set_prop(tex, "srgb", True)
    safe_set_prop(tex, "mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    safe_set_prop(tex, "address_x", unreal.TextureAddress.TA_WRAP)
    safe_set_prop(tex, "address_y", unreal.TextureAddress.TA_CLAMP)
    try:
        tex.modify()
    except Exception:
        pass
    ASSET_SUB.save_loaded_asset(tex, False)
    return tex


def ensure_lux_custom_materials() -> dict[str, unreal.Material]:
    """Create 360 Aurora Panorama SkyDome material + low-roughness (0.04) Mirror Star-Sea water material."""
    mat_dir = "/Game/LuxGenerated/Materials"
    lib = unreal.MaterialEditingLibrary
    created: dict[str, unreal.Material] = {}

    pano_tex = import_aurora_panorama_texture(mat_dir)

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

    # 1) M_Lux_StarSeaSkyDome: Unlit, Two-Sided, sampling T_OutdoorAuroraPano via Custom HLSL equirectangular UV
    sky = fresh_material("M_Lux_StarSeaSkyDome")
    sky.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    sky.set_editor_property("two_sided", True)

    world_pos = lib.create_material_expression(sky, unreal.MaterialExpressionWorldPosition, -980, 0)
    norm_wp = lib.create_material_expression(sky, unreal.MaterialExpressionNormalize, -780, 0)
    lib.connect_material_expressions(world_pos, "", norm_wp, "VectorInput")

    # Custom HLSL equirectangular projection mapping normalized world direction (d.x, d.y, d.z) -> UV
    # Note: +0.5 base shifted by +0.73 (= +1.23 > 0) aligns U=0.48 (Golden Milky Way + Twin Cyan/Rose Aurora arch)
    # directly along +Y toward Floating_Pavilion while keeping frac() argument strictly positive!
    custom_uv = lib.create_material_expression(sky, unreal.MaterialExpressionCustom, -540, 0)
    custom_uv.set_editor_property("description", "EquirectangularAuroraUV")
    custom_uv.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    dir_inp = unreal.CustomInput()
    dir_inp.set_editor_property("input_name", "Dir")
    custom_uv.set_editor_property("inputs", [dir_inp])
    custom_uv.set_editor_property(
        "code",
        (
            "float3 d = normalize(Dir);\n"
            "float u = frac(atan2(d.y, d.x) * 0.15915494 + 0.5 + 0.73);\n"
            "float v = acos(clamp(d.z, -1.0, 1.0)) * 0.31830989;\n"
            "return float2(u, v);"
        ),
    )
    conn_dir = lib.connect_material_expressions(norm_wp, "", custom_uv, "Dir")
    if not conn_dir:
        conn_dir = lib.connect_material_expressions(norm_wp, "", custom_uv, "")

    pano_sample = lib.create_material_expression(sky, unreal.MaterialExpressionTextureSample, -260, 0)
    pano_sample.set_editor_property("texture", pano_tex)
    conn_uv = lib.connect_material_expressions(custom_uv, "", pano_sample, "UVs")
    if not conn_uv:
        conn_uv = lib.connect_material_expressions(custom_uv, "", pano_sample, "")

    sky_gain = lib.create_material_expression(sky, unreal.MaterialExpressionScalarParameter, -260, 220)
    sky_gain.set_editor_property("parameter_name", "SkyLuminanceBoost")
    sky_gain.set_editor_property("default_value", 1.38)

    sky_mul = lib.create_material_expression(sky, unreal.MaterialExpressionMultiply, -20, 40)
    lib.connect_material_expressions(pano_sample, "RGB", sky_mul, "A")
    lib.connect_material_expressions(sky_gain, "", sky_mul, "B")

    lib.connect_material_property(sky_mul, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.recompile_material(sky)
    ASSET_SUB.save_loaded_asset(sky, False)
    created["sky"] = sky

    # 2) M_Lux_StarWater: Low-roughness (0.04) mirror obsidian star-sea reflecting the 360 Aurora SkyDome & Palace
    water = fresh_material("M_Lux_StarWater")
    water.set_editor_property("two_sided", True)

    w_base = lib.create_material_expression(water, unreal.MaterialExpressionConstant3Vector, -300, -240)
    w_base.set_editor_property("constant", unreal.LinearColor(0.003, 0.008, 0.022, 1.0))
    lib.connect_material_property(w_base, "", unreal.MaterialProperty.MP_BASE_COLOR)

    w_metal = lib.create_material_expression(water, unreal.MaterialExpressionConstant, -300, -140)
    w_metal.set_editor_property("r", 0.22)
    lib.connect_material_property(w_metal, "", unreal.MaterialProperty.MP_METALLIC)

    w_spec = lib.create_material_expression(water, unreal.MaterialExpressionConstant, -300, -60)
    w_spec.set_editor_property("r", 0.96)
    lib.connect_material_property(w_spec, "", unreal.MaterialProperty.MP_SPECULAR)

    w_rough = lib.create_material_expression(water, unreal.MaterialExpressionConstant, -300, 20)
    w_rough.set_editor_property("r", 0.04)
    lib.connect_material_property(w_rough, "", unreal.MaterialProperty.MP_ROUGHNESS)

    # Subtle animated bioluminescent stardust veins that preserve crisp mirror reflections
    w_wp = lib.create_material_expression(water, unreal.MaterialExpressionWorldPosition, -820, 180)
    w_time = lib.create_material_expression(water, unreal.MaterialExpressionTime, -820, 300)
    w_speed = lib.create_material_expression(water, unreal.MaterialExpressionConstant3Vector, -820, 380)
    w_speed.set_editor_property("constant", unreal.LinearColor(9.0, 7.0, 0.0, 1.0))
    w_pan = lib.create_material_expression(water, unreal.MaterialExpressionMultiply, -650, 300)
    lib.connect_material_expressions(w_time, "", w_pan, "A")
    lib.connect_material_expressions(w_speed, "", w_pan, "B")

    w_scroll = lib.create_material_expression(water, unreal.MaterialExpressionAdd, -490, 200)
    lib.connect_material_expressions(w_wp, "", w_scroll, "A")
    lib.connect_material_expressions(w_pan, "", w_scroll, "B")

    w_scale = lib.create_material_expression(water, unreal.MaterialExpressionMultiply, -340, 200)
    w_freq = lib.create_material_expression(water, unreal.MaterialExpressionConstant, -490, 290)
    w_freq.set_editor_property("r", 0.0024)
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
    w_pexp.set_editor_property("r", 6.5)
    lib.connect_material_expressions(w_sat, "", w_pow, "Base")
    lib.connect_material_expressions(w_pexp, "", w_pow, "Exp")

    w_em = lib.create_material_expression(water, unreal.MaterialExpressionMultiply, 250, 200)
    w_glow = lib.create_material_expression(water, unreal.MaterialExpressionConstant3Vector, 90, 310)
    w_glow.set_editor_property("constant", unreal.LinearColor(0.020, 0.052, 0.105, 1.0))
    lib.connect_material_expressions(w_pow, "", w_em, "A")
    lib.connect_material_expressions(w_glow, "", w_em, "B")
    lib.connect_material_property(w_em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

    lib.recompile_material(water)
    ASSET_SUB.save_loaded_asset(water, False)
    created["water"] = water

    REPORT["custom_materials"] = {
        "aurora_pano_texture": pano_tex.get_path_name(),
        "sky_material": sky.get_path_name(),
        "sky_connections": {"dir": bool(conn_dir), "uv": bool(conn_uv)},
        "water_material": water.get_path_name(),
        "water_roughness": 0.04,
    }
    return created


def audit_and_normalize_gate(
    gate_actor: unreal.ButterflyDreamGateActor,
    target_floor_z: float,
    target_height_cm: float,
    meshes: dict[str, unreal.StaticMesh] | None = None,
) -> dict:
    """Measure assembled gate frame bounds, normalize scale to target height, disable blocking collision."""
    comps = gate_actor.get_components_by_class(unreal.StaticMeshComponent)
    comp_records = []
    frame_unit_height = None
    frame_unit_min_z = 0.0
    ring_mesh = meshes.get("/Game/LuxGenerated/Tunnel_T01/Tunnel_Ring") if meshes else None
    blade_mesh = meshes.get("/Game/LuxGenerated/Scale_T02/Dream_Scale_Blade") if meshes else None

    for c in comps:
        c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        cname = c.get_name()
        if c.static_mesh is None:
            if "TunnelRing_" in cname and ring_mesh is not None:
                c.set_static_mesh(ring_mesh)
            elif "VortexMote_" in cname and blade_mesh is not None:
                c.set_static_mesh(blade_mesh)
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
    return {
        "scale": round(scale_factor, 4),
        "target_height_cm": round(float(target_height_cm), 1),
        "location": vec_to_list(loc),
        "components": comp_records,
    }


def set_point_light_cd(
    lc: unreal.PointLightComponent,
    intensity_cd: float,
    radius_cm: float,
    linear_color: unreal.LinearColor | None = None,
    temp_k: float | None = None,
) -> None:
    """Configure a PointLightComponent in physical Candelas with inverse-squared falloff."""
    lc.set_mobility(unreal.ComponentMobility.MOVABLE)
    safe_set_prop(lc, "use_inverse_squared_falloff", True)
    safe_set_prop(lc, "intensity_units", unreal.LightUnits.CANDELAS)
    lc.set_intensity(float(intensity_cd))
    safe_set_prop(lc, "attenuation_radius", float(radius_cm))
    lc.set_cast_shadows(False)
    if temp_k is not None:
        lc.set_use_temperature(True)
        lc.set_temperature(float(temp_k))
    elif linear_color is not None:
        lc.set_use_temperature(False)
        lc.set_light_color(linear_color)


def spawn_point_light_cd(
    label: str,
    loc: unreal.Vector,
    intensity_cd: float,
    radius_cm: float,
    linear_color: unreal.LinearColor | None = None,
    temp_k: float | None = None,
) -> unreal.PointLight:
    """Spawn a labeled PointLight actor configured strictly in physical Candelas."""
    pl = ACTOR_SUB.spawn_actor_from_class(unreal.PointLight, loc, make_rot(0.0, 0.0, 0.0))
    pl.set_actor_label(label)
    set_point_light_cd(pl.light_component, intensity_cd, radius_cm, linear_color=linear_color, temp_k=temp_k)
    return pl


def spawn_static_landmark(
    label: str,
    mesh: unreal.StaticMesh,
    loc: unreal.Vector,
    rot: unreal.Rotator,
    scale: float,
    enable_collision: bool = False,
) -> unreal.StaticMeshActor:
    """Spawn a clean StaticMeshActor landmark with uniform scale."""
    act = ACTOR_SUB.spawn_actor_from_class(unreal.StaticMeshActor, loc, rot)
    act.set_actor_label(label)
    smc = act.static_mesh_component
    smc.set_static_mesh(mesh)
    safe_set_prop(smc, "disallow_nanite", True)
    if enable_collision:
        smc.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    else:
        smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    act.set_actor_scale3d(unreal.Vector(float(scale), float(scale), float(scale)))
    return act


def step3_upgrade_f06(meshes: dict[str, unreal.StaticMesh]) -> None:
    """Upgrade /Game/Maps/F06_SakuraDream with V2 flying-eaves gate, twin dragon pillars, guardians & lanterns."""
    map_path = "/Game/Maps/F06_SakuraDream"
    if not LEVEL_SUB.load_level(map_path):
        raise RuntimeError(f"Failed loading {map_path}")

    # Disable Nanite across ALL F06 static meshes so -game prints 0 Nanite missing-usage warnings
    if ASSET_SUB.does_directory_exist("/Game/ThirdParty/F06"):
        for ap in ASSET_SUB.list_assets("/Game/ThirdParty/F06", recursive=True):
            asset = ASSET_SUB.load_asset(ap)
            if isinstance(asset, unreal.StaticMesh):
                disable_nanite_and_save(asset)

    all_actors = ACTOR_SUB.get_all_level_actors()
    author_camera = next((actor for actor in all_actors if isinstance(actor, unreal.CameraActor)), None)
    daisy_removed = 0
    lantern_locs: list[unreal.Vector] = []
    stone_lantern_locs: list[unreal.Vector] = []
    pagoda_box: tuple[unreal.Vector, unreal.Vector] | None = None

    for actor in all_actors:
        name = actor.get_name()
        label = actor.get_actor_label()
        if label.startswith("Lux_") or isinstance(
            actor, (unreal.PlayerStart, unreal.ButterflyDreamGateActor, unreal.ButterflyDreamPropActor)
        ):
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
            if smc:
                safe_set_prop(smc, "disallow_nanite", True)
            if sm and ("01-stairs" in sm_path.lower() or "stair" in label.lower()):
                try:
                    bs = sm.get_editor_property("body_setup")
                    if bs:
                        bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
                        sm.modify()
                        ASSET_SUB.save_loaded_asset(sm, False)
                except Exception as exc:
                    REPORT["warnings"].append(f"Stairs collision note on {sm_path}: {exc}")
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

        elif isinstance(actor, unreal.PointLight):
            plc = actor.light_component
            loc = actor.get_actor_location()
            if label in ("Point_10", "Point_11"):
                set_point_light_cd(plc, 300.0, 3600.0, linear_color=unreal.LinearColor(0.38, 0.58, 1.0, 1.0))
            elif label in ("Point_1", "Point_2", "Point_3"):
                set_point_light_cd(plc, 40.0, 880.0, temp_k=2550.0)
            elif "Lantern_point" in label or "Lantern_point" in name:
                lantern_locs.append(loc)
                set_point_light_cd(plc, 40.0, 700.0, temp_k=2450.0)
            elif "Stone_lantern" in label or "Stone_lantern" in name:
                stone_lantern_locs.append(loc)
                set_point_light_cd(plc, 48.0, 850.0, temp_k=2450.0)
            else:
                set_point_light_cd(plc, 24.0, 660.0, temp_k=2500.0)

        elif isinstance(actor, unreal.DirectionalLight):
            dlc = actor.light_component
            dlc.set_mobility(unreal.ComponentMobility.MOVABLE)
            dlc.set_editor_property("intensity", 2.65)
            dlc.set_editor_property("light_color", unreal.Color(210, 218, 255, 255))

        elif isinstance(actor, unreal.SkyLight):
            slc = actor.light_component
            slc.set_mobility(unreal.ComponentMobility.MOVABLE)
            slc.set_editor_property("intensity", 1.95)
            slc.set_editor_property("light_color", unreal.Color(220, 208, 248, 255))

    # Enhance F06 Sakura petals, grass & twilight sky material instances
    lib = unreal.MaterialEditingLibrary
    petal_mi = ASSET_SUB.load_asset("/Game/ThirdParty/F06/02-foliage/01-foliage/Materials/Material_001")
    if isinstance(petal_mi, unreal.MaterialInstanceConstant):
        vnames = [str(n) for n in lib.get_vector_parameter_names(petal_mi)]
        snames = [str(n) for n in lib.get_scalar_parameter_names(petal_mi)]
        if "BaseColorFactor" in vnames:
            lib.set_material_instance_vector_parameter_value(petal_mi, "BaseColorFactor", unreal.LinearColor(1.22, 0.82, 0.92, 1.0))
        if "EmissiveFactor" in vnames:
            lib.set_material_instance_vector_parameter_value(petal_mi, "EmissiveFactor", unreal.LinearColor(0.76, 0.38, 0.54, 1.0))
        elif "EmissiveColor" in vnames:
            lib.set_material_instance_vector_parameter_value(petal_mi, "EmissiveColor", unreal.LinearColor(0.76, 0.38, 0.54, 1.0))
        if "EmissiveStrength" in snames:
            lib.set_material_instance_scalar_parameter_value(petal_mi, "EmissiveStrength", 0.09)
        lib.update_material_instance(petal_mi)
        ASSET_SUB.save_loaded_asset(petal_mi, False)

    grass_mi = ASSET_SUB.load_asset("/Game/ThirdParty/F06/04-main/04-main/Materials/Grass")
    if isinstance(grass_mi, unreal.MaterialInstanceConstant):
        vnames = [str(n) for n in lib.get_vector_parameter_names(grass_mi)]
        if "BaseColorFactor" in vnames:
            lib.set_material_instance_vector_parameter_value(grass_mi, "BaseColorFactor", unreal.LinearColor(0.24, 0.34, 0.25, 1.0))
        lib.update_material_instance(grass_mi)
        ASSET_SUB.save_loaded_asset(grass_mi, False)

    sky_mat = ASSET_SUB.load_asset("/Game/ThirdParty/F06/Custom/M_F06_SkyDome")
    if isinstance(sky_mat, unreal.MaterialInstanceConstant):
        vnames = [str(n) for n in lib.get_vector_parameter_names(sky_mat)]
        if "ZenithColor" in vnames:
            lib.set_material_instance_vector_parameter_value(sky_mat, "ZenithColor", unreal.LinearColor(0.032, 0.044, 0.145, 1.0))
        if "HorizonColor" in vnames:
            lib.set_material_instance_vector_parameter_value(sky_mat, "HorizonColor", unreal.LinearColor(0.25, 0.15, 0.32, 1.0))
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
        x_mid, low_y, low_z, high_y, high_z = 0.0, -1800.0, -180.0, -500.0, 220.0

    terrace_y = sum(v.y for v in stone_lantern_locs) / len(stone_lantern_locs) if stone_lantern_locs else (high_y + 240.0)
    terrace_z = sum(v.z for v in stone_lantern_locs) / len(stone_lantern_locs) if stone_lantern_locs else (high_z + 40.0)

    def stair_surface_z(y_val: float) -> float:
        denom = max(high_y - low_y, 1.0)
        alpha = max(-0.25, min(1.2, (y_val - low_y) / denom))
        lantern_z = low_z + alpha * (high_z - low_z)
        return lantern_z - 155.0

    # Calibrate PlayerStart at lower sakura staircase entrance so frame 1 showcases V2 Butterfly + Twin Dragon Pillars + Gate + Pagoda + Moon
    spawn_rot = make_rot(6.2, 90.0, 0.0)
    spawn_loc = unreal.Vector(x_mid, low_y - 255.0, stair_surface_z(low_y - 255.0) + 185.0)
    if author_camera:
        spawn_rot = author_camera.get_actor_rotation()
        spawn_loc = (
            author_camera.get_actor_location()
            + unreal.MathLibrary.get_forward_vector(spawn_rot) * 74.0
            - unreal.MathLibrary.get_up_vector(spawn_rot) * 15.0
        )
    ps = ACTOR_SUB.spawn_actor_from_class(unreal.PlayerStart, spawn_loc, spawn_rot)
    ps.set_actor_label("Lux_F06_PlayerStart")

    # Subtle foreground hero fill so the V2 butterfly's 24K gold filigree & stained-glass wings gleam on frame 1
    spawn_point_light_cd(
        "Lux_F06_HeroButterflyFill",
        spawn_loc + unreal.Vector(35.0, -45.0, 95.0),
        38.0,
        520.0,
        linear_color=unreal.LinearColor(1.0, 0.90, 0.78, 1.0),
    )

    # 1) V2 Flying-Eaves Sakura Dream Gate (G01) on upper terrace before Pagoda (Yaw=0, ~485 cm tall)
    gate_frame_mesh = meshes["/Game/LuxGenerated/Gate_G01/Gate_Frame"]
    leaf_l_mesh = meshes["/Game/LuxGenerated/Gate_G01/Gate_Leaf_L"]
    leaf_r_mesh = meshes["/Game/LuxGenerated/Gate_G01/Gate_Leaf_R"]

    gate_y = (pagoda_box[0].y - 410.0) if pagoda_box else (terrace_y - 60.0)
    gate_floor_z = max(terrace_z - 95.0, -34.0)

    gate_actor = ACTOR_SUB.spawn_actor_from_class(
        unreal.ButterflyDreamGateActor,
        unreal.Vector(x_mid, gate_y, gate_floor_z),
        make_rot(0.0, 0.0, 0.0),
    )
    gate_actor.set_actor_label("Lux_F06_SakuraDreamGate")
    # CRITICAL ORDER: apply_gate_preset(False) FIRST, then configure_hinge_offsets(...) IMMEDIATELY AFTER!
    gate_actor.apply_gate_preset(False)
    gate_actor.configure_hinge_offsets(
        unreal.Vector(-69.475, 13.875, 153.383),
        unreal.Vector(71.508, 13.822, 142.913),
        unreal.Vector(1.253, -0.004, 27.039),
        unreal.Vector(0.0, 16.608, 129.212),
    )
    safe_set_prop(gate_actor, "TargetMapPackageName", "/Game/Maps/Lux_StarSeaDream")
    safe_set_prop(gate_actor, "ResonanceDistance", 2200.0)
    safe_set_prop(gate_actor, "TriggerTeleportDistance", 290.0)
    f06_gate_info = audit_and_normalize_gate(gate_actor, gate_floor_z, 485.0, meshes=meshes)

    # Architectural warm-gold + turquoise Candelas accent lights on V2 Flying-Eaves Gate
    spawn_point_light_cd(
        "Lux_F06_GateGoldEaveKey",
        unreal.Vector(x_mid, gate_y - 185.0, gate_floor_z + 295.0),
        165.0,
        1150.0,
        linear_color=unreal.LinearColor(1.0, 0.78, 0.42, 1.0),
    )
    spawn_point_light_cd(
        "Lux_F06_GateTurquoiseRoofAccent",
        unreal.Vector(x_mid, gate_y - 110.0, gate_floor_z + 455.0),
        110.0,
        980.0,
        linear_color=unreal.LinearColor(0.32, 0.92, 0.96, 1.0),
    )

    # 2) Twin monumental Dragon_Pillars (~420 cm tall) flanking the lower sakura staircase entrance in front of PlayerStart
    pillar_mesh = meshes["/Game/LuxGenerated/Sanctuary/Dragon_Pillar"]
    pillar_h_unit = max((pillar_mesh.get_bounding_box().max - pillar_mesh.get_bounding_box().min).z, 1.0)
    f06_pillar_scale = 420.0 / pillar_h_unit
    pillar_y = low_y + 115.0
    pillar_base_z = stair_surface_z(pillar_y) - 18.0
    f06_pillars_info = []
    for side in (-1.0, 1.0):
        px = x_mid + side * 255.0
        pyaw = -162.0 if side < 0 else 162.0
        tag = "L" if side < 0 else "R"
        p_act = spawn_static_landmark(
            f"Lux_F06_DragonPillar_{tag}",
            pillar_mesh,
            unreal.Vector(px, pillar_y, pillar_base_z),
            make_rot(0.0, pyaw, 0.0),
            f06_pillar_scale,
            enable_collision=False,
        )
        # Pearl crown & coiled golden dragon relief Candelas lights
        spawn_point_light_cd(
            f"Lux_F06_DragonPillarPearlLight_{tag}",
            unreal.Vector(px, pillar_y - 28.0, pillar_base_z + 412.0),
            52.0,
            720.0,
            linear_color=unreal.LinearColor(0.66, 0.92, 1.0, 1.0),
        )
        spawn_point_light_cd(
            f"Lux_F06_DragonPillarGoldLight_{tag}",
            unreal.Vector(px - side * 42.0, pillar_y - 68.0, pillar_base_z + 215.0),
            48.0,
            620.0,
            linear_color=unreal.LinearColor(1.0, 0.78, 0.42, 1.0),
        )
        f06_pillars_info.append(vec_to_list(p_act.get_actor_location()))

    # 3) Flanking V2 Floating_Lanterns along the sakura staircase
    lantern_mesh = meshes["/Game/LuxGenerated/Props/Floating_Lantern"]
    lantern_h_unit = max((lantern_mesh.get_bounding_box().max - lantern_mesh.get_bounding_box().min).z, 1.0)
    f06_lantern_scale = 112.0 / lantern_h_unit
    for idx in range(4):
        alpha = (idx + 0.55) / 4.2
        ly = low_y + alpha * (high_y - low_y)
        lz = stair_surface_z(ly) + 195.0
        for side in (-1.0, 1.0):
            lx = x_mid + side * 295.0
            prop = ACTOR_SUB.spawn_actor_from_class(
                unreal.ButterflyDreamPropActor, unreal.Vector(lx, ly, lz), make_rot(0.0, 180.0, 0.0)
            )
            prop.set_actor_label(f"Lux_F06_FloatingLantern_{idx}_{'L' if side < 0 else 'R'}")
            prop.configure_prop(lantern_mesh, f06_lantern_scale, True, unreal.LinearColor(1.0, 0.68, 0.30, 1.0), 42.0, 720.0)
            safe_set_prop(prop, "BobAmplitude", 16.0)
            safe_set_prop(prop, "SpinSpeedYaw", 6.0)
            safe_set_prop(prop, "PhaseOffset", float(idx) * 0.8 + (1.57 if side > 0 else 0.0))

    # 4) Twin Celestial_Guardian phoenixes + Crystal_Lotuses guarding the upper gate terrace
    guardian_mesh = meshes["/Game/LuxGenerated/Sanctuary/Celestial_Guardian"]
    guardian_h_unit = max((guardian_mesh.get_bounding_box().max - guardian_mesh.get_bounding_box().min).z, 1.0)
    f06_guardian_scale = 250.0 / guardian_h_unit

    lotus_mesh = meshes["/Game/LuxGenerated/Props/Crystal_Lotus"]
    lotus_h_unit = max((lotus_mesh.get_bounding_box().max - lotus_mesh.get_bounding_box().min).z, 1.0)
    f06_lotus_scale = 92.0 / lotus_h_unit

    f06_guardians_info = []
    for side in (-1.0, 1.0):
        tag = "L" if side < 0 else "R"
        gx = x_mid + side * 320.0
        gy = gate_y - 135.0
        gyaw = -152.0 if side < 0 else 152.0
        g_act = spawn_static_landmark(
            f"Lux_F06_TerraceGuardian_{tag}",
            guardian_mesh,
            unreal.Vector(gx, gy, gate_floor_z),
            make_rot(0.0, gyaw, 0.0),
            f06_guardian_scale,
            enable_collision=False,
        )
        spawn_point_light_cd(
            f"Lux_F06_GuardianAccent_{tag}",
            unreal.Vector(gx - side * 40.0, gy - 65.0, gate_floor_z + 150.0),
            46.0,
            580.0,
            linear_color=unreal.LinearColor(1.0, 0.82, 0.52, 1.0),
        )
        f06_guardians_info.append(vec_to_list(g_act.get_actor_location()))

        lotus = ACTOR_SUB.spawn_actor_from_class(
            unreal.ButterflyDreamPropActor,
            unreal.Vector(x_mid + side * 225.0, gate_y - 165.0, gate_floor_z + 6.0),
            make_rot(0.0, 0.0, 0.0),
        )
        lotus.set_actor_label(f"Lux_F06_CrystalLotus_{tag}")
        lotus.configure_prop(lotus_mesh, f06_lotus_scale, True, unreal.LinearColor(0.52, 0.90, 1.0, 1.0), 34.0, 620.0)
        safe_set_prop(lotus, "BobAmplitude", 5.0)
        safe_set_prop(lotus, "SpinSpeedYaw", 12.0)

    # Ensure WorldSettings uses ButterflyGameMode
    world = UNREAL_EDITOR_SUB.get_editor_world()
    if world:
        ws = world.get_world_settings()
        safe_set_prop(ws, "default_game_mode", unreal.ButterflyGameMode)

    # Calibrate PostProcessVolume exposure & subtle Xianxia bloom (rich jewel colors, zero white blowout)
    ppvs = [a for a in ACTOR_SUB.get_all_level_actors() if isinstance(a, unreal.PostProcessVolume)]
    if not ppvs:
        ppv = ACTOR_SUB.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0), make_rot(0, 0, 0))
        ppv.set_actor_label("Lux_F06_PostProcess")
        safe_set_prop(ppv, "unbound", True)
        ppvs = [ppv]
    pp_settings = ppvs[0].get_editor_property("settings")
    safe_set_prop(pp_settings, "override_auto_exposure_min_brightness", True)
    safe_set_prop(pp_settings, "auto_exposure_min_brightness", 0.42)
    safe_set_prop(pp_settings, "override_auto_exposure_max_brightness", True)
    safe_set_prop(pp_settings, "auto_exposure_max_brightness", 1.55)
    safe_set_prop(pp_settings, "override_auto_exposure_bias", True)
    safe_set_prop(pp_settings, "auto_exposure_bias", 0.15)
    safe_set_prop(pp_settings, "override_bloom_intensity", True)
    safe_set_prop(pp_settings, "bloom_intensity", 0.45)
    safe_set_prop(pp_settings, "override_bloom_threshold", True)
    safe_set_prop(pp_settings, "bloom_threshold", 1.15)
    ppvs[0].set_editor_property("settings", pp_settings)

    cam_rot = spawn_rot
    cam_loc = (
        spawn_loc
        - unreal.MathLibrary.get_forward_vector(cam_rot) * 74.0
        + unreal.MathLibrary.get_up_vector(cam_rot) * 15.0
    )
    set_viewport_camera(cam_loc, cam_rot)

    if not LEVEL_SUB.save_current_level():
        raise RuntimeError("Failed saving upgraded F06_SakuraDream")

    REPORT["f06_metrics"] = {
        "daisy_removed": daisy_removed,
        "lantern_count": len(lantern_locs),
        "stone_lantern_count": len(stone_lantern_locs),
        "pagoda_box": [vec_to_list(pagoda_box[0]), vec_to_list(pagoda_box[1])] if pagoda_box else None,
        "player_start": vec_to_list(ps.get_actor_location()),
        "dragon_pillars": f06_pillars_info,
        "terrace_guardians": f06_guardians_info,
        "gate_info": f06_gate_info,
        "gate_frame_bounds": mesh_bounds_dict(gate_frame_mesh),
        "gate_leaf_l_bounds": mesh_bounds_dict(leaf_l_mesh),
        "gate_leaf_r_bounds": mesh_bounds_dict(leaf_r_mesh),
        "viewport_camera": {"location": vec_to_list(cam_loc), "rotation": [cam_rot.pitch, cam_rot.yaw, cam_rot.roll]},
    }


def step4_build_lux_starsea_dream(meshes: dict[str, unreal.StaticMesh], custom_mats: dict[str, unreal.Material]) -> None:
    """Create Wave-2 Imperial Xianxia Star-Sea Sanctuary: /Game/Maps/Lux_StarSeaDream."""
    map_path = "/Game/Maps/Lux_StarSeaDream"
    if ASSET_SUB.does_asset_exist(map_path):
        ASSET_SUB.delete_asset(map_path)
    if not LEVEL_SUB.new_level(map_path):
        raise RuntimeError(f"Failed creating {map_path}")

    sphere_mesh = ASSET_SUB.load_asset("/Engine/BasicShapes/Sphere")
    plane_mesh = ASSET_SUB.load_asset("/Engine/BasicShapes/Plane")

    # 1. True 360° Outdoor Aurora Sanctuary SkyDome (Golden Milky Way + Cyan/Rose/Violet Aurora Curtains)
    sky_actor = ACTOR_SUB.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0.0, 0.0, 0.0), make_rot(0.0, 0.0, 0.0))
    sky_actor.set_actor_label("Lux_StarSea_SkyDome")
    sky_smc = sky_actor.static_mesh_component
    sky_smc.set_static_mesh(sphere_mesh)
    sky_smc.set_material(0, custom_mats["sky"])
    sky_smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    sky_smc.set_cast_shadow(False)
    sky_actor.set_actor_scale3d(unreal.Vector(1200.0, 1200.0, 1200.0))

    # 2. Obsidian Mirror Star-Sea Ocean at Z = -140 cm (Roughness = 0.04)
    sea_z = -140.0
    sea_actor = ACTOR_SUB.spawn_actor_from_class(
        unreal.StaticMeshActor, unreal.Vector(0.0, 1400.0, sea_z), make_rot(0.0, 0.0, 0.0)
    )
    sea_actor.set_actor_label("Lux_StarSea_Water")
    sea_smc = sea_actor.static_mesh_component
    sea_smc.set_static_mesh(plane_mesh)
    sea_smc.set_material(0, custom_mats["water"])
    sea_smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    sea_smc.set_cast_shadow(False)
    sea_actor.set_actor_scale3d(unreal.Vector(1200.0, 1200.0, 1.0))

    # 3. Celestial Key/Rim Directional Lighting, Real-Time Aurora SkyLight, Whisper-Thin Horizon Fog & PostProcess
    dir_light = ACTOR_SUB.spawn_actor_from_class(
        unreal.DirectionalLight, unreal.Vector(0.0, 0.0, 1600.0), make_rot(-30.0, 52.0, 0.0)
    )
    dir_light.set_actor_label("Lux_StarSea_MoonKeyLight")
    dlc = dir_light.light_component
    dlc.set_editor_property("intensity", 2.95)
    dlc.set_editor_property("light_color", unreal.Color(218, 232, 255, 255))

    sky_light = ACTOR_SUB.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0.0, 0.0, 1200.0), make_rot(0.0, 0.0, 0.0))
    sky_light.set_actor_label("Lux_StarSea_SkyLight")
    slc = sky_light.light_component
    slc.set_editor_property("intensity", 2.15)
    slc.set_editor_property("light_color", unreal.Color(205, 225, 255, 255))
    safe_set_prop(slc, "real_time_capture", True)

    # Keep fog ultra-clear so the 360° Aurora Panorama & Milky Way shine at 100% saturation and reflect in the mirror water
    fog = ACTOR_SUB.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0.0, 0.0, -260.0), make_rot(0.0, 0.0, 0.0))
    fog.set_actor_label("Lux_StarSea_Fog")
    fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    fc.set_editor_property("fog_density", 0.0012)
    fc.set_editor_property("fog_height_falloff", 0.35)
    fc.set_editor_property("fog_inscattering_luminance", unreal.LinearColor(0.035, 0.065, 0.14, 1.0))
    fc.set_editor_property("start_distance", 1800.0)

    ppv = ACTOR_SUB.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0.0, 0.0, 0.0), make_rot(0.0, 0.0, 0.0))
    ppv.set_actor_label("Lux_StarSea_PostProcess")
    safe_set_prop(ppv, "unbound", True)
    pp = ppv.get_editor_property("settings")
    safe_set_prop(pp, "override_auto_exposure_min_brightness", True)
    safe_set_prop(pp, "auto_exposure_min_brightness", 0.45)
    safe_set_prop(pp, "override_auto_exposure_max_brightness", True)
    safe_set_prop(pp, "auto_exposure_max_brightness", 1.55)
    safe_set_prop(pp, "override_auto_exposure_bias", True)
    safe_set_prop(pp, "auto_exposure_bias", 0.12)
    safe_set_prop(pp, "override_bloom_intensity", True)
    safe_set_prop(pp, "bloom_intensity", 0.48)
    safe_set_prop(pp, "override_bloom_threshold", True)
    safe_set_prop(pp, "bloom_threshold", 1.15)
    safe_set_prop(pp, "override_screen_space_reflection_intensity", True)
    safe_set_prop(pp, "screen_space_reflection_intensity", 100.0)
    safe_set_prop(pp, "override_screen_space_reflection_quality", True)
    safe_set_prop(pp, "screen_space_reflection_quality", 100.0)
    ppv.set_editor_property("settings", pp)

    # 4. Hero Centerpiece: Floating_Pavilion (S01, ~2200 cm tall) at Y=2550, Yaw=180° so waterfalls & grand stairs face player!
    pav_mesh = meshes["/Game/LuxGenerated/Pavilion_S01/Floating_Pavilion"]
    pav_box = pav_mesh.get_bounding_box()
    pav_size = pav_box.max - pav_box.min
    pav_scale = 2200.0 / max(pav_size.z, 1.0)
    pav_y = 2550.0
    pav_z = sea_z + 105.0 - pav_box.min.z * pav_scale
    pav_actor = spawn_static_landmark(
        "Lux_StarSea_FloatingPavilion",
        pav_mesh,
        unreal.Vector(0.0, pav_y, pav_z),
        make_rot(0.0, 180.0, 0.0),
        pav_scale,
        enable_collision=True,
    )

    # Palace architectural lighting: warm-gold multi-tier eaves + cyan jade waterfalls + flanking side pavilions
    spawn_point_light_cd(
        "Lux_StarSea_PavilionGoldEaveLight",
        unreal.Vector(0.0, pav_y - 760.0, sea_z + 1480.0),
        520.0,
        3600.0,
        linear_color=unreal.LinearColor(1.0, 0.78, 0.46, 1.0),
    )
    spawn_point_light_cd(
        "Lux_StarSea_PavilionWaterfallCyanGlow",
        unreal.Vector(0.0, pav_y - 680.0, sea_z + 460.0),
        460.0,
        3200.0,
        linear_color=unreal.LinearColor(0.36, 0.90, 1.0, 1.0),
    )
    for side in (-1.0, 1.0):
        spawn_point_light_cd(
            f"Lux_StarSea_PavilionWingRim_{'L' if side < 0 else 'R'}",
            unreal.Vector(side * 900.0, pav_y - 320.0, sea_z + 1020.0),
            240.0,
            2400.0,
            linear_color=unreal.LinearColor(1.0, 0.75, 0.44, 1.0),
        )

    # Giant Crystal_Lotus cradle directly beneath Floating_Pavilion
    lotus_mesh = meshes["/Game/LuxGenerated/Props/Crystal_Lotus"]
    lotus_box = lotus_mesh.get_bounding_box()
    lotus_unit_h = max((lotus_box.max - lotus_box.min).z, 1.0)
    lotus_unit_w = max((lotus_box.max - lotus_box.min).x, 1.0)
    cradle_scale = 1220.0 / lotus_unit_w
    cradle = ACTOR_SUB.spawn_actor_from_class(
        unreal.ButterflyDreamPropActor, unreal.Vector(0.0, pav_y, sea_z - 12.0), make_rot(0.0, 0.0, 0.0)
    )
    cradle.set_actor_label("Lux_StarSea_GiantPavilionLotus")
    cradle.configure_prop(lotus_mesh, cradle_scale, True, unreal.LinearColor(0.45, 0.88, 1.0, 1.0), 190.0, 2200.0)
    safe_set_prop(cradle, "BobAmplitude", 5.0)
    safe_set_prop(cradle, "SpinSpeedYaw", 3.5)

    # 5. Ceremonial Celestial_Bridge (S02, ~950 cm true walkway span) arching gracefully across mirror water on central axis
    # Exact PCA walkway alignment: Yaw = -43.52°, unit walkway length = 32.75 cm -> scale = 950 / 32.75 = 29.0
    bridge_mesh = meshes["/Game/LuxGenerated/Sanctuary/Celestial_Bridge"]
    bridge_scale = 950.0 / 32.75
    bridge_y = 540.0
    bridge_z = sea_z - 10.0
    bridge_actor = spawn_static_landmark(
        "Lux_StarSea_CelestialBridge",
        bridge_mesh,
        unreal.Vector(0.0, bridge_y, bridge_z),
        make_rot(0.0, -43.52, 0.0),
        bridge_scale,
        enable_collision=True,
    )
    spawn_point_light_cd(
        "Lux_StarSea_BridgeArchCyanGlow",
        unreal.Vector(0.0, bridge_y, sea_z + 150.0),
        145.0,
        1250.0,
        linear_color=unreal.LinearColor(0.42, 0.90, 1.0, 1.0),
    )
    spawn_point_light_cd(
        "Lux_StarSea_BridgeGoldBalustrade",
        unreal.Vector(0.0, bridge_y - 220.0, sea_z + 360.0),
        95.0,
        1050.0,
        linear_color=unreal.LinearColor(1.0, 0.80, 0.48, 1.0),
    )

    # 6. Grand Colonnade of 6 Dragon_Pillars (P01, ~600 cm tall, 3 per side) with pearl apex Candelas lights
    pillar_mesh = meshes["/Game/LuxGenerated/Sanctuary/Dragon_Pillar"]
    pillar_unit_h = max((pillar_mesh.get_bounding_box().max - pillar_mesh.get_bounding_box().min).z, 1.0)
    colonnade_scale = 600.0 / pillar_unit_h
    colonnade_ys = [-160.0, 680.0, 1520.0]
    colonnade_locs = []
    for p_idx, py in enumerate(colonnade_ys):
        for side in (-1.0, 1.0):
            px = side * 680.0
            pz = sea_z - 8.0
            pyaw = -160.0 if side < 0 else 160.0
            tag = f"{p_idx}_{'L' if side < 0 else 'R'}"
            p_act = spawn_static_landmark(
                f"Lux_StarSea_DragonPillar_{tag}",
                pillar_mesh,
                unreal.Vector(px, py, pz),
                make_rot(0.0, pyaw, 0.0),
                colonnade_scale,
                enable_collision=False,
            )
            # Pearl apex Candelas light + mid-column warm gold dragon accent
            spawn_point_light_cd(
                f"Lux_StarSea_DragonPearlLight_{tag}",
                unreal.Vector(px, py, pz + 590.0),
                88.0,
                1150.0,
                linear_color=unreal.LinearColor(0.64, 0.92, 1.0, 1.0),
            )
            spawn_point_light_cd(
                f"Lux_StarSea_DragonGoldLight_{tag}",
                unreal.Vector(px - side * 55.0, py - 85.0, pz + 300.0),
                62.0,
                820.0,
                linear_color=unreal.LinearColor(1.0, 0.78, 0.44, 1.0),
            )
            colonnade_locs.append(vec_to_list(p_act.get_actor_location()))

    # 7. Arrival PlayerStart calibrated for an unforgettable frame-1 panorama
    spawn_loc = unreal.Vector(0.0, -1380.0, 148.0)
    ps = ACTOR_SUB.spawn_actor_from_class(unreal.PlayerStart, spawn_loc, make_rot(3.8, 90.0, 0.0))
    ps.set_actor_label("Lux_StarSea_PlayerStart")

    spawn_point_light_cd(
        "Lux_StarSea_HeroButterflyFill",
        unreal.Vector(32.0, -1425.0, 235.0),
        38.0,
        520.0,
        linear_color=unreal.LinearColor(1.0, 0.90, 0.78, 1.0),
    )

    # 8. Left-Midground Return Gate: Lux_StarSea_ReturnStarGate (G03, Yaw=-26°, ~500 cm tall) + Lotus Dais
    outer_mesh = meshes["/Game/LuxGenerated/Gate_G03/StarGate_OuterRing"]
    gate_dais_scale = 320.0 / lotus_unit_w
    gate_dais = spawn_static_landmark(
        "Lux_StarSea_StarGateLotusDais",
        lotus_mesh,
        unreal.Vector(-430.0, -320.0, sea_z - 4.0),
        make_rot(0.0, 0.0, 0.0),
        gate_dais_scale,
        enable_collision=False,
    )
    gate_floor_z = sea_z + lotus_unit_h * gate_dais_scale * 0.86

    star_gate = ACTOR_SUB.spawn_actor_from_class(
        unreal.ButterflyDreamGateActor,
        unreal.Vector(-430.0, -320.0, gate_floor_z),
        make_rot(0.0, -26.0, 0.0),
    )
    star_gate.set_actor_label("Lux_StarSea_ReturnStarGate")
    # CRITICAL ORDER: apply_gate_preset(True) FIRST, then configure_hinge_offsets(...) IMMEDIATELY AFTER!
    star_gate.apply_gate_preset(True)
    star_gate.configure_hinge_offsets(
        unreal.Vector(-69.475, 13.875, 153.383),
        unreal.Vector(71.508, 13.822, 142.913),
        unreal.Vector(1.253, -0.004, 27.039),
        unreal.Vector(1.253, -0.004, 27.039),
    )
    safe_set_prop(star_gate, "TargetMapPackageName", "/Game/Maps/F06_SakuraDream")
    safe_set_prop(star_gate, "ResonanceDistance", 2200.0)
    safe_set_prop(star_gate, "TriggerTeleportDistance", 320.0)
    starsea_gate_info = audit_and_normalize_gate(star_gate, gate_floor_z, 500.0, meshes=meshes)

    spawn_point_light_cd(
        "Lux_StarSea_StarGateGoldRim",
        unreal.Vector(-360.0, -480.0, gate_floor_z + 260.0),
        135.0,
        1150.0,
        linear_color=unreal.LinearColor(1.0, 0.82, 0.48, 1.0),
    )

    # 9. Right-Midground Hero Monument: Celestial_Guardian (S03, ~460 cm tall) balancing G03 + Twin Forecourt Phoenixes
    guardian_mesh = meshes["/Game/LuxGenerated/Sanctuary/Celestial_Guardian"]
    guardian_unit_h = max((guardian_mesh.get_bounding_box().max - guardian_mesh.get_bounding_box().min).z, 1.0)
    hero_guardian_scale = 460.0 / guardian_unit_h

    guardian_dais = spawn_static_landmark(
        "Lux_StarSea_HeroGuardianLotusDais",
        lotus_mesh,
        unreal.Vector(430.0, -320.0, sea_z - 4.0),
        make_rot(0.0, 30.0, 0.0),
        gate_dais_scale,
        enable_collision=False,
    )
    guardian_floor_z = sea_z + lotus_unit_h * gate_dais_scale * 0.86
    hero_guardian = spawn_static_landmark(
        "Lux_StarSea_HeroCelestialGuardian",
        guardian_mesh,
        unreal.Vector(430.0, -320.0, guardian_floor_z),
        make_rot(0.0, 154.0, 0.0),
        hero_guardian_scale,
        enable_collision=False,
    )
    spawn_point_light_cd(
        "Lux_StarSea_HeroGuardianKeyLight",
        unreal.Vector(360.0, -480.0, guardian_floor_z + 250.0),
        145.0,
        1150.0,
        linear_color=unreal.LinearColor(1.0, 0.82, 0.50, 1.0),
    )
    spawn_point_light_cd(
        "Lux_StarSea_HeroGuardianAuroraRim",
        unreal.Vector(510.0, -260.0, guardian_floor_z + 360.0),
        95.0,
        950.0,
        linear_color=unreal.LinearColor(0.45, 0.92, 1.0, 1.0),
    )

    forecourt_guardian_scale = 360.0 / guardian_unit_h
    forecourt_dais_scale = 250.0 / lotus_unit_w
    forecourt_guardians = []
    for side in (-1.0, 1.0):
        tag = "L" if side < 0 else "R"
        fg_x = side * 440.0
        fg_y = 1720.0
        fg_yaw = -154.0 if side < 0 else 154.0
        spawn_static_landmark(
            f"Lux_StarSea_ForecourtLotusDais_{tag}",
            lotus_mesh,
            unreal.Vector(fg_x, fg_y, sea_z - 4.0),
            make_rot(0.0, 0.0, 0.0),
            forecourt_dais_scale,
            enable_collision=False,
        )
        fg_z = sea_z + lotus_unit_h * forecourt_dais_scale * 0.86
        fg_act = spawn_static_landmark(
            f"Lux_StarSea_ForecourtGuardian_{tag}",
            guardian_mesh,
            unreal.Vector(fg_x, fg_y, fg_z),
            make_rot(0.0, fg_yaw, 0.0),
            forecourt_guardian_scale,
            enable_collision=False,
        )
        spawn_point_light_cd(
            f"Lux_StarSea_ForecourtGuardianLight_{tag}",
            unreal.Vector(fg_x - side * 55.0, fg_y - 85.0, fg_z + 200.0),
            92.0,
            920.0,
            linear_color=unreal.LinearColor(1.0, 0.80, 0.48, 1.0),
        )
        forecourt_guardians.append(vec_to_list(fg_act.get_actor_location()))

    # 10. Crystal_Lotus water pads on the mirror star-sea + Floating_Lanterns + Dream_Scale_Blade spiral
    lantern_mesh = meshes["/Game/LuxGenerated/Props/Floating_Lantern"]
    blade_mesh = meshes["/Game/LuxGenerated/Scale_T02/Dream_Scale_Blade"]

    pad_lotus_scale = 90.0 / lotus_unit_h
    lantern_scale = 118.0 / max((lantern_mesh.get_bounding_box().max - lantern_mesh.get_bounding_box().min).z, 1.0)
    blade_scale = 34.0 / max((blade_mesh.get_bounding_box().max - blade_mesh.get_bounding_box().min).z, 1.0)

    for idx in range(6):
        t = idx / 5.0
        y = -860.0 + t * 2550.0
        for side in (-1.0, 1.0):
            x = side * (255.0 + 135.0 * math.sin(t * math.pi * 1.3 + 0.4))
            # Avoid overlapping bridge footings around y in [80, 960] when |x| < 210
            if 20.0 <= y <= 1020.0 and abs(x) < 260.0:
                x = side * 320.0
            lotus = ACTOR_SUB.spawn_actor_from_class(
                unreal.ButterflyDreamPropActor,
                unreal.Vector(x, y, sea_z + 2.0),
                make_rot(0.0, float(idx) * 35.0, 0.0),
            )
            lotus.set_actor_label(f"Lux_StarSea_Lotus_{idx}_{'L' if side < 0 else 'R'}")
            lotus.configure_prop(
                lotus_mesh,
                pad_lotus_scale * (0.95 + 0.14 * (idx % 3)),
                True,
                unreal.LinearColor(0.50, 0.90, 1.0, 1.0) if idx % 2 == 0 else unreal.LinearColor(0.96, 0.66, 0.92, 1.0),
                30.0,
                720.0,
            )
            safe_set_prop(lotus, "BobAmplitude", 3.5)
            safe_set_prop(lotus, "SpinSpeedYaw", 10.0)
            safe_set_prop(lotus, "PhaseOffset", float(idx) * 0.6 + (1.2 if side > 0 else 0.0))

            lantern = ACTOR_SUB.spawn_actor_from_class(
                unreal.ButterflyDreamPropActor,
                unreal.Vector(side * (495.0 + 60.0 * math.cos(idx)), y + 120.0, sea_z + 330.0 + 75.0 * math.sin(idx * 1.1)),
                make_rot(0.0, 180.0, 0.0),
            )
            lantern.set_actor_label(f"Lux_StarSea_Lantern_{idx}_{'L' if side < 0 else 'R'}")
            lantern.configure_prop(lantern_mesh, lantern_scale, True, unreal.LinearColor(1.0, 0.70, 0.34, 1.0), 46.0, 860.0)
            safe_set_prop(lantern, "BobAmplitude", 22.0)
            safe_set_prop(lantern, "SpinSpeedYaw", 6.5)
            safe_set_prop(lantern, "PhaseOffset", float(idx) * 0.9 + (0.7 if side > 0 else 0.0))

    # Rising celestial spiral of Dream_Scale_Blade motes arching high around the sanctuary avenue
    for idx in range(18):
        u = idx / 17.0
        theta = u * 3.2 * math.pi + 0.55
        rad = 520.0 + 260.0 * math.sin(u * math.pi)
        bx = math.cos(theta) * rad
        by = -350.0 + u * 2700.0
        bz = 180.0 + u * 680.0 + 70.0 * math.sin(theta * 2.0)
        blade = ACTOR_SUB.spawn_actor_from_class(
            unreal.ButterflyDreamPropActor,
            unreal.Vector(bx, by, bz),
            make_rot(15.0 * math.sin(theta), theta * 57.3, 18.0),
        )
        blade.set_actor_label(f"Lux_StarSea_ScaleBlade_{idx}")
        blade.configure_prop(blade_mesh, blade_scale, False, unreal.LinearColor(0.85, 0.92, 1.0, 1.0), 0.0, 0.0)
        safe_set_prop(blade, "BobAmplitude", 30.0)
        safe_set_prop(blade, "SpinSpeedYaw", 65.0)
        safe_set_prop(blade, "PhaseOffset", float(idx) * 0.5)

    world = UNREAL_EDITOR_SUB.get_editor_world()
    if world:
        safe_set_prop(world.get_world_settings(), "default_game_mode", unreal.ButterflyGameMode)

    cam_loc = unreal.Vector(0.0, spawn_loc.y - 74.0, spawn_loc.z + 15.0)
    cam_rot = make_rot(3.8, 90.0, 0.0)
    set_viewport_camera(cam_loc, cam_rot)

    if not LEVEL_SUB.save_current_level():
        raise RuntimeError(f"Failed saving {map_path}")

    REPORT["lux_starsea_metrics"] = {
        "pavilion_bounds": mesh_bounds_dict(pav_mesh),
        "pavilion_scale": round(pav_scale, 3),
        "pavilion_location": vec_to_list(pav_actor.get_actor_location()),
        "celestial_bridge_scale": round(bridge_scale, 3),
        "celestial_bridge_location": vec_to_list(bridge_actor.get_actor_location()),
        "dragon_pillar_colonnade_count": len(colonnade_locs),
        "dragon_pillar_colonnade": colonnade_locs,
        "hero_guardian_location": vec_to_list(hero_guardian.get_actor_location()),
        "forecourt_guardians": forecourt_guardians,
        "star_gate_outer_bounds": mesh_bounds_dict(outer_mesh),
        "star_gate_info": starsea_gate_info,
        "player_start": vec_to_list(ps.get_actor_location()),
        "viewport_camera": {"location": vec_to_list(cam_loc), "rotation": [cam_rot.pitch, cam_rot.yaw, cam_rot.roll]},
    }


def main() -> None:
    try:
        preview_dir = os.environ.get("BUTTERFLY_LUX_V2_PREVIEW")
        # Allow running in ButterflyDream directly OR in a preview copy
        if preview_dir:
            expected = Path(preview_dir).resolve()
            if PROJECT_DIR != expected:
                REPORT["warnings"].append(f"PROJECT_DIR={PROJECT_DIR} != BUTTERFLY_LUX_V2_PREVIEW={expected}, proceeding anyway")
        REPORT["project_dir"] = str(PROJECT_DIR)
        flush_report()
        step1_open_scratch_and_clean()
        meshes = step2_import_lux_v2_assets()
        flush_report()
        step3_upgrade_f06(meshes)
        flush_report()
        custom_mats = ensure_lux_custom_materials()
        step4_build_lux_starsea_dream(meshes, custom_mats)
        REPORT["status"] = "SUCCEEDED"
    except Exception as exc:
        import traceback

        REPORT["status"] = "FAILED"
        REPORT["errors"].append(f"{exc}\n{traceback.format_exc()}")
        unreal.log_error(f"LUX_REBUILD_FAILED: {exc}\n{traceback.format_exc()}")
    finally:
        flush_report()
        unreal.log(f"LUX_REBUILD_DONE status={REPORT['status']} report={REPORT_PATH}")
        quit_editor = getattr(unreal.SystemLibrary, "quit_editor", None)
        if quit_editor:
            quit_editor()
        else:
            unreal.SystemLibrary.execute_console_command(None, "QUIT_EDITOR")


raise RuntimeError(
    "Disabled: legacy rebuild can delete scenes and overwrite PBR materials. "
    "Use the current four-realm recovery and build scripts."
)
