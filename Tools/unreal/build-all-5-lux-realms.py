"""Build all 5 Beyond-100/100 Xianxia Realms in UE 5.8 for Zhuangzi's Butterfly Dream (庄周梦蝶).

Imports all 26 official Lux3D G1 high-poly PBR GLB assets (Wave-1 + Wave-2 V2_Extra) + 360° Outdoor Aurora
Panorama, builds 4 bespoke HLSL 360° SkyDome materials + 4 Mirror Ocean materials, disables Nanite on all
StaticMeshes (nanite_missing_usage=0), and assembles all 5 interconnected realms with custom Lux3D portals,
GPU-instanced 3D animated particle swarms (AButterflyParticleSwarmActor), and automatic 35-verse 3D Chinese
brush calligraphy flight corridors (UButterflyStorySubsystem + AButterflyStoryTextActor):

  1. /Game/Maps/F06_SakuraDream          — 第一境 ｜ 梦之始 ｜ 绯樱云阶金阙  (-> Lux_StarSeaDream)
  2. /Game/Maps/Lux_StarSeaDream         — 第二境 ｜ 梦之境 ｜ 太虚瑶池星海  (-> Lux_InkCloudDream)
  3. /Game/Maps/Lux_InkCloudDream        — 第三境 ｜ 梦之悟 ｜ 墨染云海琴台  (-> Lux_CrystalMirageDream)
  4. /Game/Maps/Lux_CrystalMirageDream   — 第四境 ｜ 梦之幻 ｜ 七宝琉璃幻境  (-> Lux_TaijiAwakeningDream)
  5. /Game/Maps/Lux_TaijiAwakeningDream  — 第五境 ｜ 梦之醒 ｜ 混沌太极归一  (-> F06_SakuraDream)
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import unreal


REPORT: dict = {
    "status": "STARTED",
    "imported_meshes": {},
    "custom_materials": {},
    "nanite_disabled_count": 0,
    "realms": {},
    "warnings": [],
    "errors": [],
}


def resolve_project_root() -> Path:
    if Path("V:/Assets/LuxGenerated").is_dir():
        return Path("V:/")
    return Path(__file__).resolve().parents[2]


ROOT = resolve_project_root()
LUX_ROOT = ROOT / "Assets" / "LuxGenerated"
PANO_SOURCE_JPG = LUX_ROOT / "V2_Sanctuary" / "World_OutdoorAuroraSanctuary_3FO4K4REJBX6_pano.jpg"
EVIDENCE_DIR = ROOT / "Evidence" / "Unreal" / "LuxRebuild"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
PROJECT_DIR = Path(unreal.Paths.project_dir()).resolve()
REPORT_PATH = EVIDENCE_DIR / "v3-five-realms-rebuild-report.json"
REPORT_PATH_COMPAT = EVIDENCE_DIR / "rebuild-report.json"
IMPORT_CHECKPOINT = PROJECT_DIR / "Saved" / "LuxV3Imports.json"
SCRATCH_MAP = "/Game/Maps/_ScratchBuild"

LEVEL_SUB = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ASSET_SUB = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
ACTOR_SUB = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
UNREAL_EDITOR_SUB = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
STATIC_MESH_SUB = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
INTERCHANGE_MGR = unreal.InterchangeManager.get_interchange_manager_scripted()


# (rel_glb, import_pkg_dir, target_mesh_path, complex_collision,
#  glow_rgb, glow_strength, use_basecolor_as_emissive_fallback, roughness_scale, metallic_override)
LUX_ASSET_SPECS = [
    # --- Wave 1: Hero Butterfly ---
    ("V2_Butterfly/Ready/Butterfly_Body.glb", "/Game/LuxGenerated/_V3Imp/B01_Body", "/Game/LuxGenerated/Butterfly_B01/Butterfly_Body", False, (0.85, 0.75, 0.40), 0.18, False, 0.84, None),
    ("V2_Butterfly/Ready/Wing_L.glb", "/Game/LuxGenerated/_V3Imp/B01_WingL", "/Game/LuxGenerated/Butterfly_B01/Wing_L", False, (0.25, 0.55, 0.95), 0.28, False, 0.80, None),
    ("V2_Butterfly/Ready/Wing_R.glb", "/Game/LuxGenerated/_V3Imp/B01_WingR", "/Game/LuxGenerated/Butterfly_B01/Wing_R", False, (0.25, 0.55, 0.95), 0.28, False, 0.80, None),
    # --- Wave 1: Articulated Gates & Scale Blade ---
    ("V2_Gates/Ready/Gate_Frame.glb", "/Game/LuxGenerated/_V3Imp/G01_Frame", "/Game/LuxGenerated/Gate_G01/Gate_Frame", False, (1.00, 0.95, 0.90), 0.25, False, 0.88, None),
    ("V2_Gates/Ready/Gate_Leaf_L.glb", "/Game/LuxGenerated/_V3Imp/G01_LeafL", "/Game/LuxGenerated/Gate_G01/Gate_Leaf_L", False, (1.00, 0.96, 0.95), 0.28, False, 0.84, None),
    ("V2_Gates/Ready/Gate_Leaf_R.glb", "/Game/LuxGenerated/_V3Imp/G01_LeafR", "/Game/LuxGenerated/Gate_G01/Gate_Leaf_R", False, (1.00, 0.96, 0.95), 0.28, False, 0.84, None),
    ("V2_Gates/Ready/StarGate_OuterRing.glb", "/Game/LuxGenerated/_V3Imp/G03_Outer", "/Game/LuxGenerated/Gate_G03/StarGate_OuterRing", False, (0.90, 0.98, 1.04), 0.28, False, 0.85, None),
    ("V2_Gates/Ready/StarGate_InnerRing.glb", "/Game/LuxGenerated/_V3Imp/G03_Inner", "/Game/LuxGenerated/Gate_G03/StarGate_InnerRing", False, (1.04, 0.94, 0.82), 0.35, False, 0.82, None),
    ("V2_Gates/Ready/Tunnel_Ring.glb", "/Game/LuxGenerated/_V3Imp/T01_Ring", "/Game/LuxGenerated/Tunnel_T01/Tunnel_Ring", False, (1.02, 0.94, 0.96), 0.35, False, 0.82, None),
    ("Ready/Dream_Scale_Blade.glb", "/Game/LuxGenerated/_V3Imp/T02_Blade", "/Game/LuxGenerated/Scale_T02/Dream_Scale_Blade", False, (0.92, 0.95, 1.08), 0.22, True, 0.72, 0.28),
    # --- Wave 1: Sanctuary Landmarks ---
    ("V2_Sanctuary/Ready/Floating_Pavilion.glb", "/Game/LuxGenerated/_V3Imp/S01_Pavilion", "/Game/LuxGenerated/Pavilion_S01/Floating_Pavilion", True, (0.96, 0.98, 1.02), 0.02, True, 0.85, 0.28),
    ("V2_Sanctuary/Ready/Celestial_Bridge.glb", "/Game/LuxGenerated/_V3Imp/S02_Bridge", "/Game/LuxGenerated/Sanctuary/Celestial_Bridge", True, (0.84, 0.98, 1.05), 0.02, True, 0.78, 0.26),
    ("V2_Sanctuary/Ready/Celestial_Guardian.glb", "/Game/LuxGenerated/_V3Imp/S03_Guardian", "/Game/LuxGenerated/Sanctuary/Celestial_Guardian", False, (1.02, 0.95, 0.88), 0.02, True, 0.75, 0.42),
    ("V2_Sanctuary/Ready/Dragon_Pillar.glb", "/Game/LuxGenerated/_V3Imp/P01_Pillar", "/Game/LuxGenerated/Sanctuary/Dragon_Pillar", False, (0.98, 0.96, 0.94), 0.02, True, 0.82, 0.32),
    ("V2_Sanctuary/Ready/Floating_Lantern.glb", "/Game/LuxGenerated/_V3Imp/W01_Lantern", "/Game/LuxGenerated/Props/Floating_Lantern", False, (1.08, 0.84, 0.50), 0.22, True, 0.78, 0.38),
    ("V2_Sanctuary/Ready/Crystal_Lotus.glb", "/Game/LuxGenerated/_V3Imp/W02_Lotus", "/Game/LuxGenerated/Props/Crystal_Lotus", False, (0.86, 0.98, 1.08), 0.15, True, 0.72, 0.30),
    # --- Wave 2 Extra: Multi-Realm Hero Architecture, Portals & 3D Animated Particle Models ---
    ("V2_Extra/Ready/Ink_Cloud_Mountain_Complex.glb", "/Game/LuxGenerated/_V3Imp/E01_InkMtn", "/Game/LuxGenerated/Extra/Ink_Cloud_Mountain_Complex", True, (0.12, 0.16, 0.22), 0.02, True, 0.84, 0.26),
    ("V2_Extra/Ready/Luminous_Guqin_Bridge.glb", "/Game/LuxGenerated/_V3Imp/E02_Guqin", "/Game/LuxGenerated/Extra/Luminous_Guqin_Bridge", True, (1.02, 0.96, 0.84), 0.04, True, 0.76, 0.34),
    ("V2_Extra/Ready/Seven_Tier_Crystal_Pagoda.glb", "/Game/LuxGenerated/_V3Imp/E03_Pagoda", "/Game/LuxGenerated/Extra/Seven_Tier_Crystal_Pagoda", True, (1.04, 0.96, 1.08), 0.08, True, 0.64, 0.22),
    ("V2_Extra/Ready/Floating_Crystal_Garden.glb", "/Game/LuxGenerated/_V3Imp/E04_Garden", "/Game/LuxGenerated/Extra/Floating_Crystal_Garden", True, (1.02, 0.94, 1.06), 0.04, True, 0.68, 0.24),
    ("V2_Extra/Ready/Taiji_Star_Sphere.glb", "/Game/LuxGenerated/_V3Imp/E05_Taiji", "/Game/LuxGenerated/Extra/Taiji_Star_Sphere", False, (1.04, 0.98, 0.90), 0.08, True, 0.72, 0.45),
    ("V2_Extra/Ready/Celestial_Scroll_Gate.glb", "/Game/LuxGenerated/_V3Imp/E06_ScrollGate", "/Game/LuxGenerated/Extra/Celestial_Scroll_Gate", False, (1.05, 0.96, 0.82), 0.08, True, 0.78, 0.38),
    ("V2_Extra/Ready/Ink_Ripple_Portal.glb", "/Game/LuxGenerated/_V3Imp/E07_InkPortal", "/Game/LuxGenerated/Extra/Ink_Ripple_Portal", False, (0.84, 0.98, 1.04), 0.08, True, 0.74, 0.32),
    ("V2_Extra/Ready/Crystal_Prism_Portal.glb", "/Game/LuxGenerated/_V3Imp/E08_PrismPortal", "/Game/LuxGenerated/Extra/Crystal_Prism_Portal", False, (1.02, 0.96, 1.10), 0.08, True, 0.58, 0.26),
    ("V2_Extra/Ready/Celestial_Spirit_Koi.glb", "/Game/LuxGenerated/_V3Imp/E09_SpiritKoi", "/Game/LuxGenerated/Extra/Celestial_Spirit_Koi", False, (0.96, 1.02, 1.08), 0.32, True, 0.68, 0.32),
    ("V2_Extra/Ready/Sakura_Spirit_Swirl.glb", "/Game/LuxGenerated/_V3Imp/E10_SakuraSwirl", "/Game/LuxGenerated/Extra/Sakura_Spirit_Swirl", False, (1.08, 0.88, 0.98), 0.30, True, 0.70, 0.28),
]


def flush_report() -> None:
    txt = json.dumps(REPORT, ensure_ascii=False, indent=2) + "\n"
    REPORT_PATH.write_text(txt, encoding="utf-8")
    REPORT_PATH_COMPAT.write_text(txt, encoding="utf-8")


def make_rot(pitch: float, yaw: float, roll: float = 0.0) -> unreal.Rotator:
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
        REPORT["warnings"].append(f"set_editor_property({prop_name}) failed: {exc}")
        return False


def disable_nanite_and_save(mesh: unreal.StaticMesh, use_complex_collision: bool | None = None) -> bool:
    changed = False
    try:
        ns = mesh.get_editor_property("nanite_settings")
        if ns and ns.get_editor_property("enabled"):
            ns.set_editor_property("enabled", False)
            mesh.set_editor_property("nanite_settings", ns)
            changed = True
            REPORT["nanite_disabled_count"] += 1
    except Exception as exc:
        REPORT["warnings"].append(f"Nanite disable note on {mesh.get_path_name()}: {exc}")

    if use_complex_collision is not None:
        try:
            if not use_complex_collision and hasattr(STATIC_MESH_SUB, "remove_collisions"):
                STATIC_MESH_SUB.remove_collisions(mesh)
            bs = mesh.get_editor_property("body_setup")
            if bs:
                bs.set_editor_property(
                    "collision_trace_flag",
                    unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
                    if use_complex_collision
                    else unreal.CollisionTraceFlag.CTF_USE_DEFAULT,
                )
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
    tuned = []
    lib = unreal.MaterialEditingLibrary
    for slot in mesh.get_editor_property("static_materials"):
        mat = slot.material_interface
        if not mat:
            continue
        if isinstance(mat, unreal.MaterialInstanceConstant):
            try:
                vnames = [str(n) for n in lib.get_vector_parameter_names(mat)]
                snames = [str(n) for n in lib.get_scalar_parameter_names(mat)]
                tnames = [str(n) for n in lib.get_texture_parameter_names(mat)]
                applied = False
                if "BaseColorFactor" in vnames:
                    lib.set_material_instance_vector_parameter_value(mat, "BaseColorFactor", unreal.LinearColor(1.0, 1.0, 1.0, 1.0))
                    applied = True
                if use_basecolor_as_emissive_fallback and "OcclusionStrength" in snames:
                    lib.set_material_instance_scalar_parameter_value(mat, "OcclusionStrength", 0.0)
                    applied = True
                if roughness_scale is not None and "RoughnessFactor" in snames:
                    lib.set_material_instance_scalar_parameter_value(mat, "RoughnessFactor", float(roughness_scale))
                    applied = True
                if metallic_override is not None and "MetallicFactor" in snames:
                    lib.set_material_instance_scalar_parameter_value(mat, "MetallicFactor", float(metallic_override))
                    applied = True
                if use_basecolor_as_emissive_fallback and "BaseColorTexture" in tnames and "EmissiveTexture" in tnames:
                    base_tex = lib.get_material_instance_texture_parameter_value(mat, "BaseColorTexture")
                    if base_tex:
                        lib.set_material_instance_texture_parameter_value(mat, "EmissiveTexture", base_tex)
                        applied = True
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
                tuned.append(f"{mat.get_name()}[em={glow_strength}]")
            except Exception as exc:
                REPORT["warnings"].append(f"Material tune warning {mat.get_path_name()}: {exc}")
        else:
            tuned.append(mat.get_name())
    return tuned


def set_viewport_camera(cam_loc: unreal.Vector, cam_rot: unreal.Rotator) -> None:
    try:
        UNREAL_EDITOR_SUB.set_level_viewport_camera_info(cam_loc, cam_rot)
        return
    except Exception:
        pass
    try:
        key = LEVEL_SUB.get_active_viewport_config_key() if hasattr(LEVEL_SUB, "get_active_viewport_config_key") else "LevelEditorViewport"
        LEVEL_SUB.set_level_viewport_camera_info(cam_loc, cam_rot, key)
    except Exception:
        pass


def step1_open_scratch_and_clean() -> None:
    if ASSET_SUB.does_asset_exist(SCRATCH_MAP):
        LEVEL_SUB.load_level(SCRATCH_MAP)
    else:
        try:
            LEVEL_SUB.new_level(SCRATCH_MAP)
        except Exception as exc:
            REPORT["warnings"].append(f"Scratch map creation skipped ({exc}); continuing directly")
    if ASSET_SUB.does_asset_exist("/Game/Maps/F09_Unawakened"):
        ASSET_SUB.delete_asset("/Game/Maps/F09_Unawakened")
    if ASSET_SUB.does_directory_exist("/Game/ThirdParty/F09"):
        ASSET_SUB.delete_directory("/Game/ThirdParty/F09")


def step2_import_all_26_lux_assets() -> dict[str, unreal.StaticMesh]:
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
        if previous.get("fingerprint") == fingerprint and ASSET_SUB.does_asset_exist(target_path):
            existing = ASSET_SUB.load_asset(target_path)
            if isinstance(existing, unreal.StaticMesh):
                disable_nanite_and_save(existing, use_complex_collision=use_complex)
                loaded_meshes[target_path] = existing
                continue

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
        ASSET_SUB.save_directory(import_dir, True, True)
        ASSET_SUB.save_loaded_asset(src_mesh, False)
        src_pkg = src_mesh.get_path_name().split(".")[0]
        if src_pkg != target_path:
            if ASSET_SUB.does_asset_exist(target_path):
                ASSET_SUB.delete_asset(target_path)
            moved = ASSET_SUB.rename_asset(src_pkg, target_path)
            if not moved:
                dup = ASSET_SUB.duplicate_asset(src_pkg, target_path)
                if not dup:
                    raise RuntimeError(f"Failed relocating {src_pkg} -> {target_path}")

        mesh = ASSET_SUB.load_asset(target_path)
        if not isinstance(mesh, unreal.StaticMesh):
            raise RuntimeError(f"Relocated asset is not StaticMesh: {target_path}")

        disable_nanite_and_save(mesh, use_complex_collision=use_complex)
        mats_info = tune_imported_mesh_materials(mesh, glow_rgb, glow_strength, use_bc_emissive, rough_scale, metal_ovr)
        ASSET_SUB.save_directory(import_dir, True, True)
        ASSET_SUB.save_loaded_asset(mesh, False)

        bounds = mesh_bounds_dict(mesh)
        checkpoint[target_path] = {
            "source_glb": rel_glb,
            "fingerprint": fingerprint,
            "bounds": bounds,
            "materials": mats_info,
        }
        REPORT["imported_meshes"] = checkpoint
        IMPORT_CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
        IMPORT_CHECKPOINT.write_text(json.dumps(checkpoint, indent=2) + "\n", encoding="utf-8")
        loaded_meshes[target_path] = mesh
        unreal.log(f"LUX_V3_IMPORTED {target_path} size={bounds['size']}")

    for ap in ASSET_SUB.list_assets("/Game/LuxGenerated", recursive=True):
        cand = ASSET_SUB.load_asset(ap)
        if isinstance(cand, unreal.StaticMesh):
            disable_nanite_and_save(cand)

    # Ensure GPU-instanced swarm particle meshes have bUsedWithInstancedStaticMeshes on /Game parent materials
    ism_mat_dir = "/Game/LuxGenerated/Materials"
    lib = unreal.MaterialEditingLibrary
    cloned_ism_parents: dict[str, unreal.MaterialInterface] = {}

    def _ensure_ism_parent(m_iface: unreal.MaterialInterface) -> unreal.MaterialInterface:
        pkg = m_iface.get_path_name().split(".")[0]
        if pkg in cloned_ism_parents:
            return cloned_ism_parents[pkg]
        if isinstance(m_iface, unreal.Material):
            tgt = m_iface if pkg.startswith("/Game/") else (
                ASSET_SUB.load_asset(f"{ism_mat_dir}/M_ISM_{m_iface.get_name()}")
                if ASSET_SUB.does_asset_exist(f"{ism_mat_dir}/M_ISM_{m_iface.get_name()}")
                else ASSET_SUB.duplicate_asset(pkg, f"{ism_mat_dir}/M_ISM_{m_iface.get_name()}")
            )
            tgt.set_editor_property("used_with_instanced_static_meshes", True)
            lib.recompile_material(tgt)
            ASSET_SUB.save_loaded_asset(tgt, False)
            cloned_ism_parents[pkg] = tgt
            return tgt
        if isinstance(m_iface, unreal.MaterialInstanceConstant):
            par = m_iface.get_editor_property("parent")
            new_par = _ensure_ism_parent(par) if par else None
            tgt = m_iface if pkg.startswith("/Game/") else (
                ASSET_SUB.load_asset(f"{ism_mat_dir}/MI_ISM_{m_iface.get_name()}")
                if ASSET_SUB.does_asset_exist(f"{ism_mat_dir}/MI_ISM_{m_iface.get_name()}")
                else ASSET_SUB.duplicate_asset(pkg, f"{ism_mat_dir}/MI_ISM_{m_iface.get_name()}")
            )
            if new_par:
                lib.set_material_instance_parent(tgt, new_par)
            lib.update_material_instance(tgt)
            ASSET_SUB.save_loaded_asset(tgt, False)
            cloned_ism_parents[pkg] = tgt
            return tgt
        return m_iface

    for swarm_mesh_path in (
        "/Game/LuxGenerated/Extra/Sakura_Spirit_Swirl",
        "/Game/LuxGenerated/Extra/Celestial_Spirit_Koi",
        "/Game/LuxGenerated/Scale_T02/Dream_Scale_Blade",
    ):
        sm = loaded_meshes.get(swarm_mesh_path)
        if isinstance(sm, unreal.StaticMesh):
            for idx, slot in enumerate(sm.get_editor_property("static_materials")):
                if slot.material_interface:
                    fixed = _ensure_ism_parent(slot.material_interface)
                    if fixed != slot.material_interface:
                        sm.set_material(idx, fixed)
            ASSET_SUB.save_loaded_asset(sm, False)

    return loaded_meshes


def import_aurora_panorama_texture(mat_dir: str) -> unreal.Texture2D:
    if not PANO_SOURCE_JPG.is_file():
        raise FileNotFoundError(f"Missing aurora panorama JPG: {PANO_SOURCE_JPG}")
    target_pkg = f"{mat_dir}/T_OutdoorAuroraPano"
    if ASSET_SUB.does_asset_exist(target_pkg):
        existing = ASSET_SUB.load_asset(target_pkg)
        if isinstance(existing, unreal.Texture2D):
            return existing

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
        tmp_dir = "/Game/LuxGenerated/_V3Imp/PanoSky"
        src_data = INTERCHANGE_MGR.create_source_data(str(PANO_SOURCE_JPG))
        params = unreal.ImportAssetParameters()
        params.set_editor_property("is_automated", True)
        objs = INTERCHANGE_MGR.import_asset(tmp_dir, src_data, params) or []
        tex_cands = [o for o in objs if isinstance(o, unreal.Texture2D)]
        if not tex_cands:
            raise RuntimeError(f"Failed importing panorama texture {PANO_SOURCE_JPG}")
        src_pkg = tex_cands[0].get_path_name().split(".")[0]
        if not ASSET_SUB.rename_asset(src_pkg, target_pkg):
            ASSET_SUB.duplicate_asset(src_pkg, target_pkg)
        tex = ASSET_SUB.load_asset(target_pkg)

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


def ensure_lux_5realm_materials() -> dict[str, unreal.Material]:
    """Create 4 bespoke 360° HLSL SkyDome materials + 4 Mirror Ocean materials across Realms 2..5."""
    mat_dir = "/Game/LuxGenerated/Materials"
    lib = unreal.MaterialEditingLibrary
    created: dict[str, unreal.Material] = {}
    pano_tex = import_aurora_panorama_texture(mat_dir)

    def fresh_material(name: str) -> unreal.Material:
        pkg_path = f"{mat_dir}/{name}"
        if ASSET_SUB.does_asset_exist(pkg_path):
            ASSET_SUB.delete_asset(pkg_path)
        factory = unreal.MaterialFactoryNew()
        mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, mat_dir, unreal.Material, factory)
        if not mat:
            raise RuntimeError(f"Failed creating material {pkg_path}")
        return mat

    def build_skydome_material(name: str, u_offset: float, grade_hlsl: str) -> unreal.Material:
        sky = fresh_material(name)
        sky.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
        sky.set_editor_property("two_sided", True)

        wp = lib.create_material_expression(sky, unreal.MaterialExpressionWorldPosition, -1100, 0)
        norm_wp = lib.create_material_expression(sky, unreal.MaterialExpressionNormalize, -900, 0)
        lib.connect_material_expressions(wp, "", norm_wp, "VectorInput")

        custom_uv = lib.create_material_expression(sky, unreal.MaterialExpressionCustom, -680, -40)
        custom_uv.set_editor_property("description", f"{name}_UV")
        custom_uv.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT2)
        inp_dir = unreal.CustomInput()
        inp_dir.set_editor_property("input_name", "Dir")
        custom_uv.set_editor_property("inputs", [inp_dir])
        custom_uv.set_editor_property(
            "code",
            (
                "float3 d = normalize(Dir);\n"
                f"float u = frac(atan2(d.y, d.x) * 0.15915494 + 0.5 + {u_offset:.4f});\n"
                "float v = acos(clamp(d.z, -1.0, 1.0)) * 0.31830989;\n"
                "return float2(u, v);"
            ),
        )
        if not lib.connect_material_expressions(norm_wp, "", custom_uv, "Dir"):
            lib.connect_material_expressions(norm_wp, "", custom_uv, "")

        pano_sample = lib.create_material_expression(sky, unreal.MaterialExpressionTextureSample, -420, -40)
        pano_sample.set_editor_property("texture", pano_tex)
        if not lib.connect_material_expressions(custom_uv, "", pano_sample, "UVs"):
            lib.connect_material_expressions(custom_uv, "", pano_sample, "")

        time_node = lib.create_material_expression(sky, unreal.MaterialExpressionTime, -680, 220)

        grade = lib.create_material_expression(sky, unreal.MaterialExpressionCustom, -120, 40)
        grade.set_editor_property("description", f"{name}_Grade")
        grade.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        i_pano = unreal.CustomInput()
        i_pano.set_editor_property("input_name", "Pano")
        i_dir = unreal.CustomInput()
        i_dir.set_editor_property("input_name", "Dir")
        i_t = unreal.CustomInput()
        i_t.set_editor_property("input_name", "T")
        grade.set_editor_property("inputs", [i_pano, i_dir, i_t])
        grade.set_editor_property("code", grade_hlsl)

        lib.connect_material_expressions(pano_sample, "RGB", grade, "Pano")
        lib.connect_material_expressions(norm_wp, "", grade, "Dir")
        lib.connect_material_expressions(time_node, "", grade, "T")

        lib.connect_material_property(grade, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        lib.recompile_material(sky)
        ASSET_SUB.save_loaded_asset(sky, False)
        return sky

    def build_mirror_water_material(
        name: str,
        base_rgb: tuple[float, float, float],
        vein_rgb: tuple[float, float, float],
        roughness: float = 0.04,
        metallic: float = 0.24,
    ) -> unreal.Material:
        water = fresh_material(name)
        water.set_editor_property("two_sided", True)

        w_base = lib.create_material_expression(water, unreal.MaterialExpressionConstant3Vector, -320, -240)
        w_base.set_editor_property("constant", unreal.LinearColor(base_rgb[0], base_rgb[1], base_rgb[2], 1.0))
        lib.connect_material_property(w_base, "", unreal.MaterialProperty.MP_BASE_COLOR)

        w_metal = lib.create_material_expression(water, unreal.MaterialExpressionConstant, -320, -140)
        w_metal.set_editor_property("r", float(metallic))
        lib.connect_material_property(w_metal, "", unreal.MaterialProperty.MP_METALLIC)

        w_spec = lib.create_material_expression(water, unreal.MaterialExpressionConstant, -320, -60)
        w_spec.set_editor_property("r", 0.96)
        lib.connect_material_property(w_spec, "", unreal.MaterialProperty.MP_SPECULAR)

        w_rough = lib.create_material_expression(water, unreal.MaterialExpressionConstant, -320, 20)
        w_rough.set_editor_property("r", float(roughness))
        lib.connect_material_property(w_rough, "", unreal.MaterialProperty.MP_ROUGHNESS)

        w_wp = lib.create_material_expression(water, unreal.MaterialExpressionWorldPosition, -760, 180)
        w_time = lib.create_material_expression(water, unreal.MaterialExpressionTime, -760, 300)
        vein = lib.create_material_expression(water, unreal.MaterialExpressionCustom, -220, 200)
        vein.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        in_wp = unreal.CustomInput()
        in_wp.set_editor_property("input_name", "WP")
        in_t = unreal.CustomInput()
        in_t.set_editor_property("input_name", "T")
        vein.set_editor_property("inputs", [in_wp, in_t])
        vein.set_editor_property(
            "code",
            (
                "float2 p = WP.xy * 0.0022 + float2(T * 0.035, T * 0.024);\n"
                "float w1 = sin(p.x * 3.1 + sin(p.y * 2.7 + T * 0.4));\n"
                "float w2 = cos(p.y * 3.6 - sin(p.x * 2.3 - T * 0.3));\n"
                "float mask = pow(saturate(w1 * w2 * 0.5 + 0.5), 7.0);\n"
                f"return float3({vein_rgb[0]:.4f}, {vein_rgb[1]:.4f}, {vein_rgb[2]:.4f}) * mask;"
            ),
        )
        lib.connect_material_expressions(w_wp, "", vein, "WP")
        lib.connect_material_expressions(w_time, "", vein, "T")
        lib.connect_material_property(vein, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

        lib.recompile_material(water)
        ASSET_SUB.save_loaded_asset(water, False)
        return water

    # Realm 2: StarSea (Cyan/Rose Aurora + Golden Milky Way)
    created["starsea_sky"] = build_skydome_material(
        "M_Lux_StarSeaSkyDome",
        0.73,
        "return Pano * 1.38;",
    )
    created["starsea_water"] = build_mirror_water_material(
        "M_Lux_StarWater", (0.003, 0.008, 0.022), (0.024, 0.068, 0.125), roughness=0.04
    )

    # Realm 3: InkCloudSea (Song-dynasty Sumi-Ink Charcoal, Warm Amber Gold & Bioluminescent Jade Mist)
    created["ink_sky"] = build_skydome_material(
        "M_Lux_InkCloudSkyDome",
        0.38,
        (
            "float3 d = normalize(Dir);\n"
            "float lum = dot(Pano, float3(0.299, 0.587, 0.114));\n"
            "float horizon = exp(-abs(d.z + 0.02) * 5.2);\n"
            "float mistWave = 0.5 + 0.5 * sin(d.x * 7.0 + d.y * 5.0 + T * 0.18);\n"
            "float3 inkBase = lerp(float3(0.018, 0.022, 0.032), float3(0.76, 0.66, 0.50), pow(saturate(lum), 1.15));\n"
            "float3 jadeVein = float3(0.10, 0.42, 0.38) * saturate(Pano.g - Pano.r * 0.55) * 0.95;\n"
            "float3 amberSun = float3(0.95, 0.68, 0.32) * horizon * (0.42 + 0.28 * mistWave);\n"
            "return (inkBase + jadeVein + amberSun) * 1.25;"
        ),
    )
    created["ink_water"] = build_mirror_water_material(
        "M_Lux_InkMirrorWater", (0.008, 0.010, 0.014), (0.065, 0.110, 0.088), roughness=0.045
    )

    # Realm 4: CrystalMirage (Prismatic Rose-Quartz, Sapphire, Emerald & Violet Glazed Liuli Nebula)
    created["crystal_sky"] = build_skydome_material(
        "M_Lux_CrystalMirageSkyDome",
        0.58,
        (
            "float3 d = normalize(Dir);\n"
            "float ang = atan2(d.y, d.x);\n"
            "float3 prism = 0.5 + 0.5 * cos(ang * 3.0 + d.z * 5.0 + T * 0.22 + float3(0.0, 2.094, 4.188));\n"
            "float band = exp(-abs(d.z - 0.18 - 0.08 * sin(ang * 4.0 + T * 0.15)) * 4.2);\n"
            "float3 jewel = Pano * float3(1.18, 0.88, 1.36) + prism * band * 0.48;\n"
            "return jewel * 1.32;"
        ),
    )
    created["crystal_water"] = build_mirror_water_material(
        "M_Lux_CrystalMirrorWater", (0.010, 0.005, 0.026), (0.115, 0.048, 0.155), roughness=0.032, metallic=0.30
    )

    # Realm 5: TaijiAwakening (Cosmic Indigo-Obsidian, Pearl-White & Gold Yin-Yang Galaxy Spiral)
    created["taiji_sky"] = build_skydome_material(
        "M_Lux_TaijiCosmosSkyDome",
        0.16,
        (
            "float3 d = normalize(Dir);\n"
            "float ang = atan2(d.y, d.x) + T * 0.06;\n"
            "float rad = length(d.xy);\n"
            "float spiral = sin(ang * 2.0 - rad * 5.5);\n"
            "float crown = saturate(d.z * 1.25);\n"
            "float3 yangGold = float3(1.00, 0.86, 0.52) * pow(saturate(spiral * 0.5 + 0.5), 3.0) * crown * 0.62;\n"
            "float3 yinStar = float3(0.30, 0.52, 1.00) * pow(saturate(-spiral * 0.5 + 0.5), 3.0) * crown * 0.52;\n"
            "float horizonGold = exp(-abs(d.z) * 6.5) * 0.42;\n"
            "float3 baseSky = Pano * float3(0.95, 0.92, 1.18) + yangGold + yinStar + float3(0.95, 0.76, 0.38) * horizonGold;\n"
            "return baseSky * 1.28;"
        ),
    )
    created["taiji_water"] = build_mirror_water_material(
        "M_Lux_TaijiMirrorWater", (0.004, 0.005, 0.016), (0.120, 0.092, 0.038), roughness=0.035, metallic=0.28
    )

    REPORT["custom_materials"] = {k: v.get_path_name() for k, v in created.items()}
    return created


def set_point_light_cd(
    lc: unreal.PointLightComponent,
    intensity_cd: float,
    radius_cm: float,
    linear_color: unreal.LinearColor | None = None,
    temp_k: float | None = None,
) -> None:
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
    act = ACTOR_SUB.spawn_actor_from_class(unreal.StaticMeshActor, loc, rot)
    act.set_actor_label(label)
    smc = act.static_mesh_component
    smc.set_static_mesh(mesh)
    safe_set_prop(smc, "disallow_nanite", True)
    smc.set_collision_enabled(
        unreal.CollisionEnabled.QUERY_AND_PHYSICS if enable_collision else unreal.CollisionEnabled.NO_COLLISION
    )
    act.set_actor_scale3d(unreal.Vector(float(scale), float(scale), float(scale)))
    return act


def spawn_particle_swarm(
    label: str,
    mesh: unreal.StaticMesh,
    loc: unreal.Vector,
    count: int,
    radius_cm: float,
    height_span_cm: float,
    orbit_speed_deg: float,
    target_unit_cm: float,
    glow_color: unreal.LinearColor,
    light_cd: float,
    pattern: int,
) -> unreal.ButterflyParticleSwarmActor:
    box = mesh.get_bounding_box()
    sz = box.max - box.min
    max_dim = max(float(sz.x), float(sz.y), float(sz.z), 1.0)
    inst_scale = float(target_unit_cm) / max_dim
    swarm = ACTOR_SUB.spawn_actor_from_class(unreal.ButterflyParticleSwarmActor, loc, make_rot(0.0, 0.0, 0.0))
    swarm.set_actor_label(label)
    swarm.configure_swarm(
        mesh,
        int(count),
        float(radius_cm),
        float(height_span_cm),
        float(orbit_speed_deg),
        float(inst_scale),
        glow_color,
        float(light_cd),
        int(pattern),
    )
    return swarm


def bind_and_normalize_gate(
    gate_actor: unreal.ButterflyDreamGateActor,
    target_floor_z: float,
    target_height_cm: float,
    meshes: dict[str, unreal.StaticMesh],
    custom_frame_mesh: unreal.StaticMesh | None = None,
) -> dict:
    """Bind all gate sub-meshes explicitly, optionally swap custom Lux3D portal frame, and scale to target_height_cm."""
    ring_mesh = meshes["/Game/LuxGenerated/Tunnel_T01/Tunnel_Ring"]
    blade_mesh = meshes["/Game/LuxGenerated/Scale_T02/Dream_Scale_Blade"]
    inner_ring_mesh = meshes["/Game/LuxGenerated/Gate_G03/StarGate_InnerRing"]

    custom_portal_specs = {
        "Ink_Ripple_Portal": (unreal.Vector(0.0, 0.0, 27.388), 21.5),
        "Crystal_Prism_Portal": (unreal.Vector(0.0, 0.0, 15.016), 21.8),
        "Celestial_Scroll_Gate": (unreal.Vector(0.0, 0.0, 19.978), 18.5),
    }

    if custom_frame_mesh is not None:
        mname = custom_frame_mesh.get_name()
        if mname in custom_portal_specs:
            portal_center = custom_portal_specs[mname][0]
        else:
            fbox = custom_frame_mesh.get_bounding_box()
            fsize = fbox.max - fbox.min
            fcenter = (fbox.min + fbox.max) * 0.5
            portal_center = unreal.Vector(float(fcenter.x), float(fcenter.y), float(fbox.min.z + fsize.z * 0.45))
        gate_actor.configure_hinge_offsets(
            portal_center,
            portal_center,
            portal_center,
            portal_center,
        )

    comps = gate_actor.get_components_by_class(unreal.StaticMeshComponent)
    frame_unit_height = None
    frame_unit_min_z = 0.0

    for c in comps:
        c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        safe_set_prop(c, "disallow_nanite", True)
        cname = c.get_name()
        if "GateFrame" in cname and custom_frame_mesh is not None:
            c.set_static_mesh(custom_frame_mesh)
            c.set_editor_property("relative_rotation", make_rot(0.0, 180.0, 0.0))
        elif "LeftDoor" in cname and custom_frame_mesh is not None:
            c.set_static_mesh(inner_ring_mesh)
            mname = custom_frame_mesh.get_name()
            ibox = inner_ring_mesh.get_bounding_box()
            iw = max(float(ibox.max.x - ibox.min.x), float(ibox.max.z - ibox.min.z), 1.0)
            target_bore_diam = custom_portal_specs.get(mname, (None, 20.0))[1]
            r_scale = target_bore_diam / iw
            c.set_editor_property("relative_scale3d", unreal.Vector(r_scale, r_scale, r_scale))
        elif "TunnelRing_" in cname and c.static_mesh is None:
            c.set_static_mesh(ring_mesh)
        elif "VortexMote_" in cname and c.static_mesh is None:
            c.set_static_mesh(blade_mesh)

        sm = c.static_mesh
        if sm and "GateFrame" in cname:
            box = sm.get_bounding_box()
            rel_scale = c.get_editor_property("relative_scale3d")
            rel_loc = c.get_editor_property("relative_location")
            frame_unit_height = float(box.max.z - box.min.z) * abs(float(rel_scale.z))
            frame_unit_min_z = float(box.min.z) * float(rel_scale.z) + float(rel_loc.z)

    scale_factor = float(target_height_cm) / max(frame_unit_height or 250.0, 1.0)
    gate_actor.set_actor_scale3d(unreal.Vector(scale_factor, scale_factor, scale_factor))
    loc = gate_actor.get_actor_location()
    loc.z = float(target_floor_z) - frame_unit_min_z * scale_factor
    gate_actor.set_actor_location(loc, False, False)
    return {
        "scale": round(scale_factor, 4),
        "height_cm": round(float(target_height_cm), 1),
        "location": vec_to_list(loc),
    }


def spawn_sky_water_and_atmosphere(
    prefix: str,
    sky_mat: unreal.Material,
    water_mat: unreal.Material,
    sea_z: float,
    sun_rot: unreal.Rotator,
    sun_intensity: float,
    sun_color: unreal.Color,
    sky_intensity: float,
    sky_color: unreal.Color,
    fog_luminance: unreal.LinearColor,
    exposure_bias: float = 0.14,
) -> None:
    sphere_mesh = ASSET_SUB.load_asset("/Engine/BasicShapes/Sphere")
    plane_mesh = ASSET_SUB.load_asset("/Engine/BasicShapes/Plane")

    sky_actor = ACTOR_SUB.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0.0, 0.0, 0.0), make_rot(0.0, 0.0, 0.0))
    sky_actor.set_actor_label(f"{prefix}_SkyDome")
    sky_smc = sky_actor.static_mesh_component
    sky_smc.set_static_mesh(sphere_mesh)
    sky_smc.set_material(0, sky_mat)
    sky_smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    sky_smc.set_cast_shadow(False)
    sky_actor.set_actor_scale3d(unreal.Vector(1350.0, 1350.0, 1350.0))

    sea_actor = ACTOR_SUB.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0.0, 1500.0, sea_z), make_rot(0.0, 0.0, 0.0))
    sea_actor.set_actor_label(f"{prefix}_MirrorWater")
    sea_smc = sea_actor.static_mesh_component
    sea_smc.set_static_mesh(plane_mesh)
    sea_smc.set_material(0, water_mat)
    sea_smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    sea_smc.set_cast_shadow(False)
    sea_actor.set_actor_scale3d(unreal.Vector(1350.0, 1350.0, 1.0))

    dir_light = ACTOR_SUB.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0.0, 0.0, 1600.0), sun_rot)
    dir_light.set_actor_label(f"{prefix}_KeyLight")
    dlc = dir_light.light_component
    dlc.set_mobility(unreal.ComponentMobility.MOVABLE)
    dlc.set_editor_property("intensity", float(sun_intensity))
    dlc.set_editor_property("light_color", sun_color)

    sky_light = ACTOR_SUB.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0.0, 0.0, 1200.0), make_rot(0.0, 0.0, 0.0))
    sky_light.set_actor_label(f"{prefix}_SkyLight")
    slc = sky_light.light_component
    slc.set_mobility(unreal.ComponentMobility.MOVABLE)
    slc.set_editor_property("intensity", float(sky_intensity) * 0.85)
    slc.set_editor_property("light_color", sky_color)
    safe_set_prop(slc, "real_time_capture", False)
    safe_set_prop(slc, "source_type", unreal.SkyLightSourceType.SLS_CAPTURED_SCENE)
    safe_set_prop(slc, "lower_hemisphere_is_black", False)
    safe_set_prop(slc, "lower_hemisphere_color", unreal.LinearColor(0.04, 0.06, 0.10, 1.0))
    try:
        slc.recapture_sky()
    except Exception:
        pass

    fog = ACTOR_SUB.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0.0, 0.0, sea_z - 120.0), make_rot(0.0, 0.0, 0.0))
    fog.set_actor_label(f"{prefix}_Fog")
    fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    fc.set_editor_property("fog_density", 0.0014)
    fc.set_editor_property("fog_height_falloff", 0.34)
    fc.set_editor_property("fog_inscattering_luminance", fog_luminance)
    fc.set_editor_property("start_distance", 1650.0)

    ppv = ACTOR_SUB.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0.0, 0.0, 0.0), make_rot(0.0, 0.0, 0.0))
    ppv.set_actor_label(f"{prefix}_PostProcess")
    safe_set_prop(ppv, "unbound", True)
    pp = ppv.get_editor_property("settings")
    safe_set_prop(pp, "override_auto_exposure_min_brightness", True)
    safe_set_prop(pp, "auto_exposure_min_brightness", 0.40)
    safe_set_prop(pp, "override_auto_exposure_max_brightness", True)
    safe_set_prop(pp, "auto_exposure_max_brightness", 1.35)
    safe_set_prop(pp, "override_auto_exposure_bias", True)
    safe_set_prop(pp, "auto_exposure_bias", -0.32)
    safe_set_prop(pp, "override_bloom_intensity", True)
    safe_set_prop(pp, "bloom_intensity", 0.22)
    safe_set_prop(pp, "override_bloom_threshold", True)
    safe_set_prop(pp, "bloom_threshold", 1.25)
    safe_set_prop(pp, "override_screen_space_reflection_intensity", True)
    safe_set_prop(pp, "screen_space_reflection_intensity", 100.0)
    safe_set_prop(pp, "override_screen_space_reflection_quality", True)
    safe_set_prop(pp, "screen_space_reflection_quality", 100.0)
    ppv.set_editor_property("settings", pp)


def finalize_realm_level(map_path: str, spawn_loc: unreal.Vector, spawn_rot: unreal.Rotator) -> None:
    world = UNREAL_EDITOR_SUB.get_editor_world()
    if world:
        safe_set_prop(world.get_world_settings(), "default_game_mode", unreal.ButterflyGameMode)
    cam_loc = (
        spawn_loc
        - unreal.MathLibrary.get_forward_vector(spawn_rot) * 74.0
        + unreal.MathLibrary.get_up_vector(spawn_rot) * 15.0
    )
    set_viewport_camera(cam_loc, spawn_rot)
    if not LEVEL_SUB.save_current_level():
        raise RuntimeError(f"Failed saving {map_path}")


def create_clean_level(map_path: str) -> None:
    """Create a fresh clean level reliably without package collision."""
    if ASSET_SUB.does_asset_exist(map_path):
        if not LEVEL_SUB.load_level(map_path):
            raise RuntimeError(f"Failed loading existing level {map_path}")
        for act in list(ACTOR_SUB.get_all_level_actors()):
            cls_name = act.get_class().get_name()
            if cls_name not in ("WorldSettings", "Brush", "DefaultPhysicsVolume"):
                try:
                    ACTOR_SUB.destroy_actor(act)
                except Exception:
                    pass
        return
    if LEVEL_SUB.new_level(map_path):
        return
    raise RuntimeError(f"Failed creating {map_path}")


# ==============================================================================
# REALM 1: /Game/Maps/F06_SakuraDream (绯樱云阶金阙 -> Lux_StarSeaDream)
# ==============================================================================
def build_realm1_sakura(meshes: dict[str, unreal.StaticMesh]) -> None:
    map_path = "/Game/Maps/F06_SakuraDream"
    if not LEVEL_SUB.load_level(map_path):
        raise RuntimeError(f"Failed loading {map_path}")

    if ASSET_SUB.does_directory_exist("/Game/ThirdParty/F06"):
        for ap in ASSET_SUB.list_assets("/Game/ThirdParty/F06", recursive=True):
            try:
                asset = ASSET_SUB.load_asset(ap)
                if isinstance(asset, unreal.StaticMesh):
                    disable_nanite_and_save(asset)
            except Exception:
                pass

    all_actors = ACTOR_SUB.get_all_level_actors()
    author_camera = next((a for a in all_actors if isinstance(a, unreal.CameraActor)), None)
    lantern_locs: list[unreal.Vector] = []
    stone_lantern_locs: list[unreal.Vector] = []
    pagoda_box: tuple[unreal.Vector, unreal.Vector] | None = None

    for actor in all_actors:
        name = actor.get_name()
        label = actor.get_actor_label()
        if label.startswith("Lux_") or isinstance(
            actor,
            (
                unreal.PlayerStart,
                unreal.ButterflyDreamGateActor,
                unreal.ButterflyDreamPropActor,
                unreal.ButterflyParticleSwarmActor,
                unreal.ButterflyStoryTextActor,
            ),
        ):
            ACTOR_SUB.destroy_actor(actor)
            continue

        if isinstance(actor, unreal.StaticMeshActor):
            smc = actor.static_mesh_component
            sm = smc.static_mesh if smc else None
            sm_path = sm.get_path_name() if sm else ""
            if "Daisy" in label or "Daisy" in name or "/Daisy" in sm_path:
                ACTOR_SUB.destroy_actor(actor)
                continue
            if smc:
                safe_set_prop(smc, "disallow_nanite", True)
                if (
                    "SkyDome" in label
                    or "Sphere" in sm_path
                    or "Background_gradient" in label
                    or "Moon" in label
                    or "foliage" in sm_path.lower()
                    or "Cherry" in label
                    or "Grass" in label
                ):
                    smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            if sm and ("01-stairs" in sm_path.lower() or "stair" in label.lower()):
                try:
                    bs = sm.get_editor_property("body_setup")
                    if bs:
                        bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
                        sm.modify()
                        ASSET_SUB.save_loaded_asset(sm, False)
                except Exception:
                    pass
            origin, ext = actor.get_actor_bounds(False)
            bmin, bmax = origin - ext, origin + ext
            if "pagoda" in sm_path.lower() or "pagoda" in label.lower():
                pagoda_box = (
                    bmin if pagoda_box is None else unreal.Vector(min(pagoda_box[0].x, bmin.x), min(pagoda_box[0].y, bmin.y), min(pagoda_box[0].z, bmin.z)),
                    bmax if pagoda_box is None else unreal.Vector(max(pagoda_box[1].x, bmax.x), max(pagoda_box[1].y, bmax.y), max(pagoda_box[1].z, bmax.z)),
                )
        elif isinstance(actor, unreal.PointLight):
            plc = actor.light_component
            loc = actor.get_actor_location()
            if label in ("Point_10", "Point_11"):
                set_point_light_cd(plc, 300.0, 3600.0, linear_color=unreal.LinearColor(0.38, 0.58, 1.0, 1.0))
            elif "Lantern_point" in label or "Lantern_point" in name:
                lantern_locs.append(loc)
                set_point_light_cd(plc, 42.0, 720.0, temp_k=2450.0)
            elif "Stone_lantern" in label or "Stone_lantern" in name:
                stone_lantern_locs.append(loc)
                set_point_light_cd(plc, 48.0, 850.0, temp_k=2450.0)
            else:
                set_point_light_cd(plc, 28.0, 680.0, temp_k=2500.0)
        elif isinstance(actor, unreal.DirectionalLight):
            dlc = actor.light_component
            dlc.set_mobility(unreal.ComponentMobility.MOVABLE)
            dlc.set_editor_property("intensity", 1.55)
            dlc.set_editor_property("light_color", unreal.Color(214, 220, 255, 255))
        elif isinstance(actor, unreal.SkyLight):
            slc = actor.light_component
            slc.set_mobility(unreal.ComponentMobility.MOVABLE)
            slc.set_editor_property("intensity", 1.22)
            slc.set_editor_property("light_color", unreal.Color(225, 210, 250, 255))

    # Enhance F06 Sakura petals, grass & twilight sky material instances + calibrated exposure
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

    ppvs = [a for a in ACTOR_SUB.get_all_level_actors() if isinstance(a, unreal.PostProcessVolume)]
    if not ppvs:
        ppv = ACTOR_SUB.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0), make_rot(0, 0, 0))
        ppv.set_actor_label("Lux_F06_PostProcess")
        safe_set_prop(ppv, "unbound", True)
        ppvs = [ppv]
    pp_settings = ppvs[0].get_editor_property("settings")
    safe_set_prop(pp_settings, "override_auto_exposure_min_brightness", True)
    safe_set_prop(pp_settings, "auto_exposure_min_brightness", 0.50)
    safe_set_prop(pp_settings, "override_auto_exposure_max_brightness", True)
    safe_set_prop(pp_settings, "auto_exposure_max_brightness", 1.40)
    safe_set_prop(pp_settings, "override_auto_exposure_bias", True)
    safe_set_prop(pp_settings, "auto_exposure_bias", -0.18)
    safe_set_prop(pp_settings, "override_bloom_intensity", True)
    safe_set_prop(pp_settings, "bloom_intensity", 0.26)
    safe_set_prop(pp_settings, "override_bloom_threshold", True)
    safe_set_prop(pp_settings, "bloom_threshold", 1.20)
    ppvs[0].set_editor_property("settings", pp_settings)

    lantern_locs.sort(key=lambda v: v.y)
    stone_lantern_locs.sort(key=lambda v: v.y)
    if lantern_locs:
        x_mid = sum(v.x for v in lantern_locs) / len(lantern_locs)
        low_y = sum(v.y for v in lantern_locs[:2]) / len(lantern_locs[:2])
        low_z = sum(v.z for v in lantern_locs[:2]) / len(lantern_locs[:2])
        high_y = sum(v.y for v in lantern_locs[-2:]) / len(lantern_locs[-2:])
        high_z = sum(v.z for v in lantern_locs[-2:]) / len(lantern_locs[-2:])
    else:
        x_mid, low_y, low_z, high_y, high_z = 0.0, -1800.0, -180.0, -500.0, 220.0

    terrace_y = sum(v.y for v in stone_lantern_locs) / len(stone_lantern_locs) if stone_lantern_locs else (high_y + 240.0)
    terrace_z = sum(v.z for v in stone_lantern_locs) / len(stone_lantern_locs) if stone_lantern_locs else (high_z + 40.0)

    def stair_surface_z(y_val: float) -> float:
        alpha = max(-0.25, min(1.2, (y_val - low_y) / max(high_y - low_y, 1.0)))
        return (low_z + alpha * (high_z - low_z)) - 155.0

    spawn_rot = make_rot(6.2, 90.0, 0.0)
    spawn_loc = unreal.Vector(-0.07, -2780.0, -95.0)
    ps = ACTOR_SUB.spawn_actor_from_class(unreal.PlayerStart, spawn_loc, spawn_rot)
    ps.set_actor_label("Lux_F06_PlayerStart")
    spawn_point_light_cd("Lux_F06_HeroButterflyFill", spawn_loc + unreal.Vector(35.0, -45.0, 95.0), 15.0, 540.0, linear_color=unreal.LinearColor(1.0, 0.90, 0.78, 1.0))

    # V2 G01 Imperial Flying-Eaves Gate -> Lux_StarSeaDream
    gate_y = (pagoda_box[0].y - 410.0) if pagoda_box else (terrace_y - 60.0)
    gate_floor_z = max(terrace_z - 95.0, -34.0)
    gate_actor = ACTOR_SUB.spawn_actor_from_class(unreal.ButterflyDreamGateActor, unreal.Vector(x_mid, gate_y, gate_floor_z), make_rot(0.0, 0.0, 0.0))
    gate_actor.set_actor_label("Lux_F06_SakuraDreamGate")
    gate_actor.apply_gate_preset(False)
    gate_actor.configure_hinge_offsets(
        unreal.Vector(-69.475, 13.875, 153.383),
        unreal.Vector(71.508, 13.822, 142.913),
        unreal.Vector(1.253, -0.004, 27.039),
        unreal.Vector(0.0, 16.608, 129.212),
    )
    safe_set_prop(gate_actor, "GateTitle", "第一仙门 ｜ 飞檐鎏金绯樱阙 (通往：太虚瑶池星海)")
    safe_set_prop(gate_actor, "TargetMapPackageName", "/Game/Maps/Lux_StarSeaDream")
    safe_set_prop(gate_actor, "ResonanceDistance", 2200.0)
    safe_set_prop(gate_actor, "TriggerTeleportDistance", 290.0)
    gate_info = bind_and_normalize_gate(gate_actor, gate_floor_z, 485.0, meshes)

    spawn_point_light_cd("Lux_F06_GateGoldEaveKey", unreal.Vector(x_mid, gate_y - 185.0, gate_floor_z + 295.0), 78.0, 1200.0, linear_color=unreal.LinearColor(1.0, 0.78, 0.42, 1.0))
    spawn_point_light_cd("Lux_F06_GateTurquoiseRoof", unreal.Vector(x_mid, gate_y - 110.0, gate_floor_z + 455.0), 62.0, 980.0, linear_color=unreal.LinearColor(0.32, 0.92, 0.96, 1.0))

    # Twin Dragon Pillars + Floating Lanterns + Twin Phoenix Guardians + Crystal Lotuses
    pillar_mesh = meshes["/Game/LuxGenerated/Sanctuary/Dragon_Pillar"]
    pillar_scale = 420.0 / max((pillar_mesh.get_bounding_box().max - pillar_mesh.get_bounding_box().min).z, 1.0)
    pillar_y = low_y + 115.0
    pillar_base_z = stair_surface_z(pillar_y) - 18.0
    for side in (-1.0, 1.0):
        px = x_mid + side * 255.0
        tag = "L" if side < 0 else "R"
        spawn_static_landmark(f"Lux_F06_DragonPillar_{tag}", pillar_mesh, unreal.Vector(px, pillar_y, pillar_base_z), make_rot(0.0, -162.0 if side < 0 else 162.0, 0.0), pillar_scale)
        spawn_point_light_cd(f"Lux_F06_PillarPearl_{tag}", unreal.Vector(px, pillar_y - 28.0, pillar_base_z + 412.0), 55.0, 720.0, linear_color=unreal.LinearColor(0.66, 0.92, 1.0, 1.0))

    lantern_mesh = meshes["/Game/LuxGenerated/Props/Floating_Lantern"]
    lantern_scale = 112.0 / max((lantern_mesh.get_bounding_box().max - lantern_mesh.get_bounding_box().min).z, 1.0)
    for idx in range(4):
        alpha = (idx + 0.55) / 4.2
        ly = low_y + alpha * (high_y - low_y)
        lz = stair_surface_z(ly) + 195.0
        for side in (-1.0, 1.0):
            prop = ACTOR_SUB.spawn_actor_from_class(unreal.ButterflyDreamPropActor, unreal.Vector(x_mid + side * 295.0, ly, lz), make_rot(0.0, 180.0, 0.0))
            prop.set_actor_label(f"Lux_F06_Lantern_{idx}_{'L' if side < 0 else 'R'}")
            prop.configure_prop(lantern_mesh, lantern_scale, True, unreal.LinearColor(1.0, 0.68, 0.30, 1.0), 44.0, 720.0)
            safe_set_prop(prop, "BobAmplitude", 16.0)
            safe_set_prop(prop, "SpinSpeedYaw", 6.0)

    guardian_mesh = meshes["/Game/LuxGenerated/Sanctuary/Celestial_Guardian"]
    guardian_scale = 250.0 / max((guardian_mesh.get_bounding_box().max - guardian_mesh.get_bounding_box().min).z, 1.0)
    lotus_mesh = meshes["/Game/LuxGenerated/Props/Crystal_Lotus"]
    lotus_scale = 92.0 / max((lotus_mesh.get_bounding_box().max - lotus_mesh.get_bounding_box().min).z, 1.0)
    for side in (-1.0, 1.0):
        tag = "L" if side < 0 else "R"
        spawn_static_landmark(f"Lux_F06_Guardian_{tag}", guardian_mesh, unreal.Vector(x_mid + side * 320.0, gate_y - 135.0, gate_floor_z), make_rot(0.0, -152.0 if side < 0 else 152.0, 0.0), guardian_scale)
        lotus = ACTOR_SUB.spawn_actor_from_class(unreal.ButterflyDreamPropActor, unreal.Vector(x_mid + side * 225.0, gate_y - 165.0, gate_floor_z + 6.0), make_rot(0.0, 0.0, 0.0))
        lotus.set_actor_label(f"Lux_F06_CrystalLotus_{tag}")
        lotus.configure_prop(lotus_mesh, lotus_scale, True, unreal.LinearColor(0.52, 0.90, 1.0, 1.0), 34.0, 620.0)

    # NEW: GPU-instanced 3D Animated Particle Swarms (Falling Sakura Spirit Petals + Golden Gate Helix)
    swirl_mesh = meshes["/Game/LuxGenerated/Extra/Sakura_Spirit_Swirl"]
    koi_mesh = meshes["/Game/LuxGenerated/Extra/Celestial_Spirit_Koi"]
    spawn_particle_swarm(
        "Lux_F06_SakuraPetalCascade",
        swirl_mesh,
        unreal.Vector(x_mid, (low_y + gate_y) * 0.5, gate_floor_z + 240.0),
        44,
        780.0,
        560.0,
        22.0,
        68.0,
        unreal.LinearColor(1.0, 0.72, 0.86, 1.0),
        110.0,
        2,  # PetalCascade
    )
    spawn_particle_swarm(
        "Lux_F06_SpiritKoiSchool",
        koi_mesh,
        unreal.Vector(x_mid, gate_y - 460.0, gate_floor_z + 280.0),
        16,
        520.0,
        240.0,
        28.0,
        78.0,
        unreal.LinearColor(1.0, 0.84, 0.56, 1.0),
        95.0,
        3,  # FigureEightSchool
    )

    finalize_realm_level(map_path, spawn_loc, spawn_rot)
    REPORT["realms"]["F06_SakuraDream"] = {"player_start": vec_to_list(spawn_loc), "gate": gate_info}


# ==============================================================================
# REALM 2: /Game/Maps/Lux_StarSeaDream (太虚瑶池星海 -> Lux_InkCloudDream)
# ==============================================================================
def build_realm2_starsea(meshes: dict[str, unreal.StaticMesh], mats: dict[str, unreal.Material]) -> None:
    map_path = "/Game/Maps/Lux_StarSeaDream"
    create_clean_level(map_path)

    sea_z = -140.0
    spawn_sky_water_and_atmosphere(
        "Lux_StarSea",
        mats["starsea_sky"],
        mats["starsea_water"],
        sea_z,
        make_rot(-30.0, 52.0, 0.0),
        2.95,
        unreal.Color(218, 232, 255, 255),
        2.15,
        unreal.Color(205, 225, 255, 255),
        unreal.LinearColor(0.035, 0.065, 0.14, 1.0),
    )

    pav_mesh = meshes["/Game/LuxGenerated/Pavilion_S01/Floating_Pavilion"]
    pav_box = pav_mesh.get_bounding_box()
    pav_scale = 2250.0 / max((pav_box.max - pav_box.min).z, 1.0)
    pav_y = 2680.0
    pav_z = sea_z + 115.0 - pav_box.min.z * pav_scale
    spawn_static_landmark("Lux_StarSea_FloatingPavilion", pav_mesh, unreal.Vector(0.0, pav_y, pav_z), make_rot(0.0, 180.0, 0.0), pav_scale, enable_collision=True)
    spawn_point_light_cd("Lux_StarSea_PavilionGoldEave", unreal.Vector(0.0, pav_y - 760.0, sea_z + 1480.0), 540.0, 3600.0, linear_color=unreal.LinearColor(1.0, 0.78, 0.46, 1.0))
    spawn_point_light_cd("Lux_StarSea_PavilionCyanGlow", unreal.Vector(0.0, pav_y - 680.0, sea_z + 460.0), 480.0, 3200.0, linear_color=unreal.LinearColor(0.36, 0.90, 1.0, 1.0))

    lotus_mesh = meshes["/Game/LuxGenerated/Props/Crystal_Lotus"]
    lotus_box = lotus_mesh.get_bounding_box()
    lotus_unit_h = max((lotus_box.max - lotus_box.min).z, 1.0)
    lotus_unit_w = max((lotus_box.max - lotus_box.min).x, 1.0)
    cradle = ACTOR_SUB.spawn_actor_from_class(unreal.ButterflyDreamPropActor, unreal.Vector(0.0, pav_y, sea_z - 12.0), make_rot(0.0, 0.0, 0.0))
    cradle.set_actor_label("Lux_StarSea_GiantPavilionLotus")
    cradle.configure_prop(lotus_mesh, 1260.0 / lotus_unit_w, True, unreal.LinearColor(0.45, 0.88, 1.0, 1.0), 195.0, 2200.0)

    # Central Celestial Bridge
    bridge_mesh = meshes["/Game/LuxGenerated/Sanctuary/Celestial_Bridge"]
    spawn_static_landmark("Lux_StarSea_CelestialBridge", bridge_mesh, unreal.Vector(0.0, 480.0, sea_z - 10.0), make_rot(0.0, -43.52, 0.0), 950.0 / 32.75, enable_collision=True)
    spawn_point_light_cd("Lux_StarSea_BridgeGlow", unreal.Vector(0.0, 480.0, sea_z + 160.0), 150.0, 1300.0, linear_color=unreal.LinearColor(0.42, 0.90, 1.0, 1.0))

    # 6 Dragon Pillars Colonnade
    pillar_mesh = meshes["/Game/LuxGenerated/Sanctuary/Dragon_Pillar"]
    col_scale = 600.0 / max((pillar_mesh.get_bounding_box().max - pillar_mesh.get_bounding_box().min).z, 1.0)
    for p_idx, py in enumerate([-200.0, 680.0, 1560.0]):
        for side in (-1.0, 1.0):
            px = side * 700.0
            tag = f"{p_idx}_{'L' if side < 0 else 'R'}"
            spawn_static_landmark(f"Lux_StarSea_DragonPillar_{tag}", pillar_mesh, unreal.Vector(px, py, sea_z - 8.0), make_rot(0.0, -160.0 if side < 0 else 160.0, 0.0), col_scale)
            spawn_point_light_cd(f"Lux_StarSea_DragonPearl_{tag}", unreal.Vector(px, py, sea_z + 585.0), 90.0, 1150.0, linear_color=unreal.LinearColor(0.64, 0.92, 1.0, 1.0))

    spawn_loc = unreal.Vector(0.0, -1380.0, 148.0)
    spawn_rot = make_rot(3.8, 90.0, 0.0)
    ps = ACTOR_SUB.spawn_actor_from_class(unreal.PlayerStart, spawn_loc, spawn_rot)
    ps.set_actor_label("Lux_StarSea_PlayerStart")
    spawn_point_light_cd("Lux_StarSea_HeroFill", unreal.Vector(32.0, -1425.0, 235.0), 42.0, 540.0, linear_color=unreal.LinearColor(1.0, 0.90, 0.78, 1.0))

    # Forward Main Gate on Central Avenue (Y=1660) -> Lux_InkCloudDream!
    dais_scale = 340.0 / lotus_unit_w
    spawn_static_landmark("Lux_StarSea_ForwardGateDais", lotus_mesh, unreal.Vector(0.0, 1660.0, sea_z - 4.0), make_rot(0.0, 0.0, 0.0), dais_scale)
    fwd_floor_z = sea_z + lotus_unit_h * dais_scale * 0.86
    fwd_gate = ACTOR_SUB.spawn_actor_from_class(unreal.ButterflyDreamGateActor, unreal.Vector(0.0, 1660.0, fwd_floor_z), make_rot(0.0, 0.0, 0.0))
    fwd_gate.set_actor_label("Lux_StarSea_ForwardStarGate")
    fwd_gate.apply_gate_preset(True)
    fwd_gate.configure_hinge_offsets(
        unreal.Vector(-69.475, 13.875, 153.383),
        unreal.Vector(71.508, 13.822, 142.913),
        unreal.Vector(1.253, -0.004, 27.039),
        unreal.Vector(1.253, -0.004, 27.039),
    )
    safe_set_prop(fwd_gate, "GateTitle", "第二仙门 ｜ 浑天星轨玄门 (通往：墨染云海琴台)")
    safe_set_prop(fwd_gate, "TargetMapPackageName", "/Game/Maps/Lux_InkCloudDream")
    safe_set_prop(fwd_gate, "ResonanceDistance", 2200.0)
    safe_set_prop(fwd_gate, "TriggerTeleportDistance", 320.0)
    fwd_info = bind_and_normalize_gate(fwd_gate, fwd_floor_z, 520.0, meshes)

    # Return Gate -> F06_SakuraDream (Placed behind PlayerStart at Y = -2550, facing away along -Y)
    ret_dais_scale = 280.0 / lotus_unit_w
    spawn_static_landmark("Lux_StarSea_ReturnGateDais", lotus_mesh, unreal.Vector(0.0, -2550.0, sea_z - 4.0), make_rot(0.0, 270.0, 0.0), ret_dais_scale)
    ret_floor_z = sea_z + lotus_unit_h * ret_dais_scale * 0.86
    ret_gate = ACTOR_SUB.spawn_actor_from_class(unreal.ButterflyDreamGateActor, unreal.Vector(0.0, -2550.0, ret_floor_z), make_rot(0.0, 270.0, 0.0))
    ret_gate.set_actor_label("Lux_StarSea_ReturnGate")
    ret_gate.apply_gate_preset(True)
    ret_gate.configure_hinge_offsets(unreal.Vector(-69.475, 13.875, 153.383), unreal.Vector(71.508, 13.822, 142.913), unreal.Vector(1.253, -0.004, 27.039), unreal.Vector(1.253, -0.004, 27.039))
    safe_set_prop(ret_gate, "GateTitle", "归返仙门 ｜ 回溯绯樱云阶")
    safe_set_prop(ret_gate, "TargetMapPackageName", "/Game/Maps/F06_SakuraDream")
    safe_set_prop(ret_gate, "ResonanceDistance", 900.0)
    safe_set_prop(ret_gate, "TriggerTeleportDistance", 280.0)
    bind_and_normalize_gate(ret_gate, ret_floor_z, 440.0, meshes)

    # Right Hero Guardian + Forecourt Phoenixes + Lotus Pads & Lanterns
    guardian_mesh = meshes["/Game/LuxGenerated/Sanctuary/Celestial_Guardian"]
    g_unit_h = max((guardian_mesh.get_bounding_box().max - guardian_mesh.get_bounding_box().min).z, 1.0)
    spawn_static_landmark("Lux_StarSea_RightDais", lotus_mesh, unreal.Vector(520.0, -360.0, sea_z - 4.0), make_rot(0.0, 30.0, 0.0), ret_dais_scale)
    spawn_static_landmark("Lux_StarSea_HeroGuardian", guardian_mesh, unreal.Vector(520.0, -360.0, ret_floor_z), make_rot(0.0, 152.0, 0.0), 440.0 / g_unit_h)
    spawn_point_light_cd("Lux_StarSea_HeroGuardianKey", unreal.Vector(440.0, -500.0, ret_floor_z + 250.0), 145.0, 1150.0, linear_color=unreal.LinearColor(1.0, 0.82, 0.50, 1.0))

    lantern_mesh = meshes["/Game/LuxGenerated/Props/Floating_Lantern"]
    lantern_scale = 118.0 / max((lantern_mesh.get_bounding_box().max - lantern_mesh.get_bounding_box().min).z, 1.0)
    pad_scale = 92.0 / lotus_unit_h
    for idx in range(6):
        t = idx / 5.0
        y = -860.0 + t * 2350.0
        for side in (-1.0, 1.0):
            x = side * (320.0 + 110.0 * math.sin(t * math.pi * 1.4))
            lotus = ACTOR_SUB.spawn_actor_from_class(unreal.ButterflyDreamPropActor, unreal.Vector(x, y, sea_z + 2.0), make_rot(0.0, float(idx) * 35.0, 0.0))
            lotus.set_actor_label(f"Lux_StarSea_Lotus_{idx}_{'L' if side < 0 else 'R'}")
            lotus.configure_prop(lotus_mesh, pad_scale, True, unreal.LinearColor(0.50, 0.90, 1.0, 1.0), 30.0, 720.0)
            lantern = ACTOR_SUB.spawn_actor_from_class(unreal.ButterflyDreamPropActor, unreal.Vector(side * 520.0, y + 100.0, sea_z + 340.0 + 65.0 * math.sin(idx)), make_rot(0.0, 180.0, 0.0))
            lantern.set_actor_label(f"Lux_StarSea_Lantern_{idx}_{'L' if side < 0 else 'R'}")
            lantern.configure_prop(lantern_mesh, lantern_scale, True, unreal.LinearColor(1.0, 0.70, 0.34, 1.0), 46.0, 860.0)

    # 3D Animated Particle Swarms
    koi_mesh = meshes["/Game/LuxGenerated/Extra/Celestial_Spirit_Koi"]
    blade_mesh = meshes["/Game/LuxGenerated/Scale_T02/Dream_Scale_Blade"]
    swirl_mesh = meshes["/Game/LuxGenerated/Extra/Sakura_Spirit_Swirl"]
    spawn_particle_swarm("Lux_StarSea_KoiSchool", koi_mesh, unreal.Vector(0.0, 520.0, sea_z + 320.0), 28, 860.0, 340.0, 26.0, 92.0, unreal.LinearColor(0.48, 0.92, 1.0, 1.0), 140.0, 3)
    spawn_particle_swarm("Lux_StarSea_StardustHelix", blade_mesh, unreal.Vector(0.0, 1660.0, sea_z + 420.0), 56, 620.0, 680.0, 34.0, 42.0, unreal.LinearColor(0.82, 0.92, 1.0, 1.0), 125.0, 1)
    spawn_particle_swarm("Lux_StarSea_PalaceHalo", swirl_mesh, unreal.Vector(0.0, pav_y, sea_z + 1150.0), 36, 1180.0, 420.0, 18.0, 110.0, unreal.LinearColor(0.55, 0.88, 1.0, 1.0), 180.0, 0)

    finalize_realm_level(map_path, spawn_loc, spawn_rot)
    REPORT["realms"]["Lux_StarSeaDream"] = {"player_start": vec_to_list(spawn_loc), "forward_gate": fwd_info}


# ==============================================================================
# REALM 3: /Game/Maps/Lux_InkCloudDream (墨染云海琴台 -> Lux_CrystalMirageDream)
# ==============================================================================
def build_realm3_inkcloud(meshes: dict[str, unreal.StaticMesh], mats: dict[str, unreal.Material]) -> None:
    map_path = "/Game/Maps/Lux_InkCloudDream"
    create_clean_level(map_path)

    sea_z = -140.0
    spawn_sky_water_and_atmosphere(
        "Lux_InkCloud",
        mats["ink_sky"],
        mats["ink_water"],
        sea_z,
        make_rot(-26.0, 38.0, 0.0),
        2.85,
        unreal.Color(255, 232, 198, 255),
        2.05,
        unreal.Color(210, 228, 220, 255),
        unreal.LinearColor(0.065, 0.072, 0.065, 1.0),
        exposure_bias=0.16,
    )

    # 3-Peak Song-Dynasty Floating Ink-Wash Mountain Sanctuary Range!
    mtn_mesh = meshes["/Game/LuxGenerated/Extra/Ink_Cloud_Mountain_Complex"]
    mtn_box = mtn_mesh.get_bounding_box()
    mtn_unit_h = max((mtn_box.max - mtn_box.min).z, 1.0)
    hero_mtn_scale = 2480.0 / mtn_unit_h
    mtn_y = 2750.0
    spawn_static_landmark("Lux_InkCloud_CentralMountainSanctuary", mtn_mesh, unreal.Vector(0.0, mtn_y, sea_z + 60.0), make_rot(0.0, 180.0, 0.0), hero_mtn_scale, enable_collision=True)
    spawn_point_light_cd("Lux_InkCloud_MtnAmberLanternGlow", unreal.Vector(0.0, mtn_y - 780.0, sea_z + 1320.0), 560.0, 3600.0, linear_color=unreal.LinearColor(1.0, 0.74, 0.36, 1.0))
    spawn_point_light_cd("Lux_InkCloud_MtnJadeSpiritGlow", unreal.Vector(0.0, mtn_y - 680.0, sea_z + 440.0), 420.0, 3000.0, linear_color=unreal.LinearColor(0.28, 0.92, 0.78, 1.0))

    for side in (-1.0, 1.0):
        flank_scale = 1780.0 / mtn_unit_h
        tag = "L" if side < 0 else "R"
        spawn_static_landmark(
            f"Lux_InkCloud_FlankMountain_{tag}",
            mtn_mesh,
            unreal.Vector(side * 1580.0, 2080.0, sea_z + 140.0),
            make_rot(0.0, -125.0 if side < 0 else 125.0, 0.0),
            flank_scale,
            enable_collision=False,
        )
        spawn_point_light_cd(f"Lux_InkCloud_FlankAmber_{tag}", unreal.Vector(side * 1180.0, 1820.0, sea_z + 980.0), 280.0, 2400.0, linear_color=unreal.LinearColor(1.0, 0.76, 0.40, 1.0))

    # Central Colossal Luminous Seven-String Guqin Bridge!
    guqin_mesh = meshes["/Game/LuxGenerated/Extra/Luminous_Guqin_Bridge"]
    gbox = guqin_mesh.get_bounding_box()
    g_span = max(float(gbox.max.x - gbox.min.x), float(gbox.max.y - gbox.min.y), 1.0)
    guqin_scale = 1180.0 / g_span
    spawn_static_landmark("Lux_InkCloud_LuminousGuqinBridge", guqin_mesh, unreal.Vector(0.0, 520.0, sea_z - 6.0), make_rot(0.0, 22.0, 0.0), guqin_scale, enable_collision=True)
    spawn_point_light_cd("Lux_InkCloud_GuqinStringsGold", unreal.Vector(0.0, 520.0, sea_z + 290.0), 210.0, 1450.0, linear_color=unreal.LinearColor(1.0, 0.84, 0.44, 1.0))
    spawn_point_light_cd("Lux_InkCloud_GuqinJadeResonance", unreal.Vector(0.0, 520.0, sea_z + 110.0), 165.0, 1250.0, linear_color=unreal.LinearColor(0.32, 0.94, 0.82, 1.0))

    # Ceremonial Dragon Pillars & Warm Amber Floating Lanterns
    pillar_mesh = meshes["/Game/LuxGenerated/Sanctuary/Dragon_Pillar"]
    col_scale = 580.0 / max((pillar_mesh.get_bounding_box().max - pillar_mesh.get_bounding_box().min).z, 1.0)
    lantern_mesh = meshes["/Game/LuxGenerated/Props/Floating_Lantern"]
    lantern_scale = 122.0 / max((lantern_mesh.get_bounding_box().max - lantern_mesh.get_bounding_box().min).z, 1.0)
    lotus_mesh = meshes["/Game/LuxGenerated/Props/Crystal_Lotus"]
    lotus_box = lotus_mesh.get_bounding_box()
    lotus_unit_h = max((lotus_box.max - lotus_box.min).z, 1.0)
    lotus_unit_w = max((lotus_box.max - lotus_box.min).x, 1.0)

    for p_idx, py in enumerate([-220.0, 680.0, 1520.0]):
        for side in (-1.0, 1.0):
            px = side * 690.0
            tag = f"{p_idx}_{'L' if side < 0 else 'R'}"
            spawn_static_landmark(f"Lux_InkCloud_Pillar_{tag}", pillar_mesh, unreal.Vector(px, py, sea_z - 8.0), make_rot(0.0, -160.0 if side < 0 else 160.0, 0.0), col_scale)
            spawn_point_light_cd(f"Lux_InkCloud_PillarLight_{tag}", unreal.Vector(px, py, sea_z + 565.0), 85.0, 1100.0, linear_color=unreal.LinearColor(1.0, 0.80, 0.45, 1.0))
            lantern = ACTOR_SUB.spawn_actor_from_class(unreal.ButterflyDreamPropActor, unreal.Vector(side * 480.0, py + 160.0, sea_z + 320.0 + 45.0 * p_idx), make_rot(0.0, 180.0, 0.0))
            lantern.set_actor_label(f"Lux_InkCloud_Lantern_{tag}")
            lantern.configure_prop(lantern_mesh, lantern_scale, True, unreal.LinearColor(1.0, 0.72, 0.32, 1.0), 52.0, 880.0)

    spawn_loc = unreal.Vector(0.0, -1380.0, 152.0)
    spawn_rot = make_rot(4.0, 90.0, 0.0)
    ps = ACTOR_SUB.spawn_actor_from_class(unreal.PlayerStart, spawn_loc, spawn_rot)
    ps.set_actor_label("Lux_InkCloud_PlayerStart")
    spawn_point_light_cd("Lux_InkCloud_HeroFill", unreal.Vector(32.0, -1425.0, 240.0), 44.0, 540.0, linear_color=unreal.LinearColor(1.0, 0.90, 0.76, 1.0))

    # Forward Custom Lux3D Portal: Ink_Ripple_Portal -> Lux_CrystalMirageDream!
    ink_portal_mesh = meshes["/Game/LuxGenerated/Extra/Ink_Ripple_Portal"]
    dais_scale = 360.0 / lotus_unit_w
    spawn_static_landmark("Lux_InkCloud_ForwardDais", lotus_mesh, unreal.Vector(0.0, 1680.0, sea_z - 4.0), make_rot(0.0, 0.0, 0.0), dais_scale)
    fwd_floor_z = sea_z + lotus_unit_h * dais_scale * 0.86
    fwd_gate = ACTOR_SUB.spawn_actor_from_class(unreal.ButterflyDreamGateActor, unreal.Vector(0.0, 1680.0, fwd_floor_z), make_rot(0.0, 0.0, 0.0))
    fwd_gate.set_actor_label("Lux_InkCloud_ForwardInkPortal")
    fwd_gate.apply_gate_preset(True)
    safe_set_prop(fwd_gate, "GateTitle", "第三仙门 ｜ 水墨金缮涟漪门 (通往：七宝琉璃幻境)")
    safe_set_prop(fwd_gate, "TargetMapPackageName", "/Game/Maps/Lux_CrystalMirageDream")
    safe_set_prop(fwd_gate, "ResonanceDistance", 2200.0)
    safe_set_prop(fwd_gate, "TriggerTeleportDistance", 330.0)
    fwd_info = bind_and_normalize_gate(fwd_gate, fwd_floor_z, 540.0, meshes, custom_frame_mesh=ink_portal_mesh)
    spawn_point_light_cd("Lux_InkCloud_PortalJadeRim", unreal.Vector(0.0, 1510.0, fwd_floor_z + 280.0), 185.0, 1300.0, linear_color=unreal.LinearColor(0.32, 0.95, 0.86, 1.0))

    # Return Gate -> Lux_StarSeaDream (Placed behind PlayerStart at Y = -2550, facing away along -Y)
    ret_gate = ACTOR_SUB.spawn_actor_from_class(unreal.ButterflyDreamGateActor, unreal.Vector(0.0, -2550.0, sea_z + 18.0), make_rot(0.0, 270.0, 0.0))
    ret_gate.set_actor_label("Lux_InkCloud_ReturnGate")
    ret_gate.apply_gate_preset(True)
    ret_gate.configure_hinge_offsets(unreal.Vector(-69.475, 13.875, 153.383), unreal.Vector(71.508, 13.822, 142.913), unreal.Vector(1.253, -0.004, 27.039), unreal.Vector(1.253, -0.004, 27.039))
    safe_set_prop(ret_gate, "GateTitle", "归返仙门 ｜ 回溯太虚瑶池星海")
    safe_set_prop(ret_gate, "TargetMapPackageName", "/Game/Maps/Lux_StarSeaDream")
    safe_set_prop(ret_gate, "ResonanceDistance", 900.0)
    safe_set_prop(ret_gate, "TriggerTeleportDistance", 280.0)
    bind_and_normalize_gate(ret_gate, sea_z + 18.0, 430.0, meshes)

    # 3D Animated Particle Swarms: Spirit Koi School over Guqin + Ink-Gold Blade Helix + Mountain Cloud Swirl
    koi_mesh = meshes["/Game/LuxGenerated/Extra/Celestial_Spirit_Koi"]
    blade_mesh = meshes["/Game/LuxGenerated/Scale_T02/Dream_Scale_Blade"]
    swirl_mesh = meshes["/Game/LuxGenerated/Extra/Sakura_Spirit_Swirl"]
    spawn_particle_swarm("Lux_InkCloud_GuqinKoiSchool", koi_mesh, unreal.Vector(0.0, 520.0, sea_z + 340.0), 36, 920.0, 360.0, 24.0, 96.0, unreal.LinearColor(0.38, 0.96, 0.84, 1.0), 155.0, 3)
    spawn_particle_swarm("Lux_InkCloud_GoldBrushHelix", blade_mesh, unreal.Vector(0.0, 1680.0, sea_z + 440.0), 60, 640.0, 720.0, 30.0, 44.0, unreal.LinearColor(1.0, 0.84, 0.46, 1.0), 140.0, 1)
    spawn_particle_swarm("Lux_InkCloud_MountainSpiritSwirl", swirl_mesh, unreal.Vector(0.0, mtn_y - 200.0, sea_z + 1080.0), 40, 1280.0, 480.0, 16.0, 115.0, unreal.LinearColor(1.0, 0.80, 0.48, 1.0), 175.0, 0)

    finalize_realm_level(map_path, spawn_loc, spawn_rot)
    REPORT["realms"]["Lux_InkCloudDream"] = {"player_start": vec_to_list(spawn_loc), "forward_gate": fwd_info}


# ==============================================================================
# REALM 4: /Game/Maps/Lux_CrystalMirageDream (七宝琉璃幻境 -> Lux_TaijiAwakeningDream)
# ==============================================================================
def build_realm4_crystalmirage(meshes: dict[str, unreal.StaticMesh], mats: dict[str, unreal.Material]) -> None:
    map_path = "/Game/Maps/Lux_CrystalMirageDream"
    create_clean_level(map_path)

    sea_z = -140.0
    spawn_sky_water_and_atmosphere(
        "Lux_Crystal",
        mats["crystal_sky"],
        mats["crystal_water"],
        sea_z,
        make_rot(-32.0, 64.0, 0.0),
        3.05,
        unreal.Color(245, 222, 255, 255),
        2.25,
        unreal.Color(235, 215, 255, 255),
        unreal.LinearColor(0.075, 0.038, 0.115, 1.0),
        exposure_bias=0.12,
    )

    # Hero Centerpiece: Seven-Tier Rainbow Glazed Crystal Pagoda (2500 cm tall!) on Giant Crystal Lotus
    pagoda_mesh = meshes["/Game/LuxGenerated/Extra/Seven_Tier_Crystal_Pagoda"]
    pbox = pagoda_mesh.get_bounding_box()
    pagoda_scale = 2500.0 / max((pbox.max - pbox.min).z, 1.0)
    pagoda_y = 2680.0
    lotus_mesh = meshes["/Game/LuxGenerated/Props/Crystal_Lotus"]
    lbox = lotus_mesh.get_bounding_box()
    lotus_unit_h = max((lbox.max - lbox.min).z, 1.0)
    lotus_unit_w = max((lbox.max - lbox.min).x, 1.0)

    cradle = ACTOR_SUB.spawn_actor_from_class(unreal.ButterflyDreamPropActor, unreal.Vector(0.0, pagoda_y, sea_z - 10.0), make_rot(0.0, 0.0, 0.0))
    cradle.set_actor_label("Lux_Crystal_GiantLotusThrone")
    cradle.configure_prop(lotus_mesh, 1320.0 / lotus_unit_w, True, unreal.LinearColor(0.92, 0.56, 1.0, 1.0), 210.0, 2400.0)

    spawn_static_landmark("Lux_Crystal_SevenTierPagoda", pagoda_mesh, unreal.Vector(0.0, pagoda_y, sea_z + 95.0), make_rot(0.0, 180.0, 0.0), pagoda_scale, enable_collision=True)
    spawn_point_light_cd("Lux_Crystal_PagodaRubyBase", unreal.Vector(0.0, pagoda_y - 520.0, sea_z + 420.0), 420.0, 2600.0, linear_color=unreal.LinearColor(1.0, 0.42, 0.68, 1.0))
    spawn_point_light_cd("Lux_Crystal_PagodaEmeraldMid", unreal.Vector(0.0, pagoda_y - 520.0, sea_z + 1250.0), 420.0, 2600.0, linear_color=unreal.LinearColor(0.35, 0.96, 0.88, 1.0))
    spawn_point_light_cd("Lux_Crystal_PagodaAmethystTop", unreal.Vector(0.0, pagoda_y - 460.0, sea_z + 2050.0), 460.0, 2800.0, linear_color=unreal.LinearColor(0.84, 0.52, 1.0, 1.0))

    # Twin Floating Crystal Sky-Gardens flanking the central Celestial Bridge + High Sanctuary Island!
    garden_mesh = meshes["/Game/LuxGenerated/Extra/Floating_Crystal_Garden"]
    g_unit_w = max((garden_mesh.get_bounding_box().max - garden_mesh.get_bounding_box().min).x, 1.0)
    garden_scale = 880.0 / g_unit_w
    for side in (-1.0, 1.0):
        tag = "L" if side < 0 else "R"
        spawn_static_landmark(
            f"Lux_Crystal_FloatingGarden_{tag}",
            garden_mesh,
            unreal.Vector(side * 820.0, 820.0, sea_z + 190.0),
            make_rot(0.0, -145.0 if side < 0 else 145.0, 0.0),
            garden_scale,
            enable_collision=True,
        )
        spawn_point_light_cd(f"Lux_Crystal_GardenGlow_{tag}", unreal.Vector(side * 760.0, 760.0, sea_z + 520.0), 220.0, 1650.0, linear_color=unreal.LinearColor(1.0, 0.58, 0.92, 1.0))

    bridge_mesh = meshes["/Game/LuxGenerated/Sanctuary/Celestial_Bridge"]
    spawn_static_landmark("Lux_Crystal_CentralBridge", bridge_mesh, unreal.Vector(0.0, 480.0, sea_z - 10.0), make_rot(0.0, -43.52, 0.0), 960.0 / 32.75, enable_collision=True)

    # Twin Phoenix Guardians + Crystal Lotus Avenue
    guardian_mesh = meshes["/Game/LuxGenerated/Sanctuary/Celestial_Guardian"]
    gu_scale = 380.0 / max((guardian_mesh.get_bounding_box().max - guardian_mesh.get_bounding_box().min).z, 1.0)
    for side in (-1.0, 1.0):
        tag = "L" if side < 0 else "R"
        spawn_static_landmark(f"Lux_Crystal_Phoenix_{tag}", guardian_mesh, unreal.Vector(side * 460.0, 1740.0, sea_z + 18.0), make_rot(0.0, -155.0 if side < 0 else 155.0, 0.0), gu_scale)

    pad_scale = 105.0 / lotus_unit_h
    for idx in range(7):
        t = idx / 6.0
        y = -900.0 + t * 2400.0
        for side in (-1.0, 1.0):
            lotus = ACTOR_SUB.spawn_actor_from_class(unreal.ButterflyDreamPropActor, unreal.Vector(side * (310.0 + 80.0 * math.cos(idx)), y, sea_z + 4.0), make_rot(0.0, float(idx) * 42.0, 0.0))
            lotus.set_actor_label(f"Lux_Crystal_Pad_{idx}_{'L' if side < 0 else 'R'}")
            lotus.configure_prop(lotus_mesh, pad_scale, True, unreal.LinearColor(0.94, 0.56, 1.0, 1.0) if idx % 2 == 0 else unreal.LinearColor(0.44, 0.92, 1.0, 1.0), 38.0, 760.0)

    spawn_loc = unreal.Vector(0.0, -1380.0, 152.0)
    spawn_rot = make_rot(4.2, 90.0, 0.0)
    ps = ACTOR_SUB.spawn_actor_from_class(unreal.PlayerStart, spawn_loc, spawn_rot)
    ps.set_actor_label("Lux_Crystal_PlayerStart")
    spawn_point_light_cd("Lux_Crystal_HeroFill", unreal.Vector(32.0, -1425.0, 240.0), 44.0, 540.0, linear_color=unreal.LinearColor(1.0, 0.88, 0.98, 1.0))

    # Forward Custom Lux3D Portal: Crystal_Prism_Portal -> Lux_TaijiAwakeningDream!
    prism_portal_mesh = meshes["/Game/LuxGenerated/Extra/Crystal_Prism_Portal"]
    dais_scale = 360.0 / lotus_unit_w
    spawn_static_landmark("Lux_Crystal_ForwardDais", lotus_mesh, unreal.Vector(0.0, 1680.0, sea_z - 4.0), make_rot(0.0, 0.0, 0.0), dais_scale)
    fwd_floor_z = sea_z + lotus_unit_h * dais_scale * 0.86
    fwd_gate = ACTOR_SUB.spawn_actor_from_class(unreal.ButterflyDreamGateActor, unreal.Vector(0.0, 1680.0, fwd_floor_z), make_rot(0.0, 0.0, 0.0))
    fwd_gate.set_actor_label("Lux_Crystal_ForwardPrismPortal")
    fwd_gate.apply_gate_preset(True)
    safe_set_prop(fwd_gate, "GateTitle", "第四仙门 ｜ 虹光琉璃棱镜门 (通往：混沌太极归一)")
    safe_set_prop(fwd_gate, "TargetMapPackageName", "/Game/Maps/Lux_TaijiAwakeningDream")
    safe_set_prop(fwd_gate, "ResonanceDistance", 2200.0)
    safe_set_prop(fwd_gate, "TriggerTeleportDistance", 330.0)
    fwd_info = bind_and_normalize_gate(fwd_gate, fwd_floor_z, 560.0, meshes, custom_frame_mesh=prism_portal_mesh)
    spawn_point_light_cd("Lux_Crystal_PortalPrismGlow", unreal.Vector(0.0, 1510.0, fwd_floor_z + 290.0), 210.0, 1380.0, linear_color=unreal.LinearColor(0.92, 0.58, 1.0, 1.0))

    # Return Gate -> Lux_InkCloudDream (Placed behind PlayerStart at Y = -2550, facing away along -Y)
    ret_gate = ACTOR_SUB.spawn_actor_from_class(unreal.ButterflyDreamGateActor, unreal.Vector(0.0, -2550.0, sea_z + 18.0), make_rot(0.0, 270.0, 0.0))
    ret_gate.set_actor_label("Lux_Crystal_ReturnGate")
    ret_gate.apply_gate_preset(True)
    ret_gate.configure_hinge_offsets(unreal.Vector(-69.475, 13.875, 153.383), unreal.Vector(71.508, 13.822, 142.913), unreal.Vector(1.253, -0.004, 27.039), unreal.Vector(1.253, -0.004, 27.039))
    safe_set_prop(ret_gate, "GateTitle", "归返仙门 ｜ 回溯墨染云海琴台")
    safe_set_prop(ret_gate, "TargetMapPackageName", "/Game/Maps/Lux_InkCloudDream")
    safe_set_prop(ret_gate, "ResonanceDistance", 900.0)
    safe_set_prop(ret_gate, "TriggerTeleportDistance", 280.0)
    bind_and_normalize_gate(ret_gate, sea_z + 18.0, 430.0, meshes)

    # 3D Animated Particle Swarms: Rainbow Pagoda Double-Helix + Crystal Koi + Blossom Cascades
    koi_mesh = meshes["/Game/LuxGenerated/Extra/Celestial_Spirit_Koi"]
    blade_mesh = meshes["/Game/LuxGenerated/Scale_T02/Dream_Scale_Blade"]
    swirl_mesh = meshes["/Game/LuxGenerated/Extra/Sakura_Spirit_Swirl"]
    spawn_particle_swarm("Lux_Crystal_PagodaRainbowHelix", swirl_mesh, unreal.Vector(0.0, pagoda_y, sea_z + 1180.0), 64, 780.0, 1950.0, 26.0, 105.0, unreal.LinearColor(0.96, 0.62, 1.0, 1.0), 220.0, 1)
    spawn_particle_swarm("Lux_Crystal_MirageKoiSchool", koi_mesh, unreal.Vector(0.0, 560.0, sea_z + 340.0), 32, 920.0, 380.0, 28.0, 92.0, unreal.LinearColor(0.68, 0.88, 1.0, 1.0), 150.0, 3)
    spawn_particle_swarm("Lux_Crystal_PrismShardCascade", blade_mesh, unreal.Vector(0.0, 1180.0, sea_z + 520.0), 64, 980.0, 760.0, 24.0, 44.0, unreal.LinearColor(1.0, 0.72, 0.98, 1.0), 145.0, 2)

    finalize_realm_level(map_path, spawn_loc, spawn_rot)
    REPORT["realms"]["Lux_CrystalMirageDream"] = {"player_start": vec_to_list(spawn_loc), "forward_gate": fwd_info}


# ==============================================================================
# REALM 5: /Game/Maps/Lux_TaijiAwakeningDream (混沌太极归一 -> F06_SakuraDream)
# ==============================================================================
def build_realm5_taijiawakening(meshes: dict[str, unreal.StaticMesh], mats: dict[str, unreal.Material]) -> None:
    map_path = "/Game/Maps/Lux_TaijiAwakeningDream"
    create_clean_level(map_path)

    sea_z = -140.0
    spawn_sky_water_and_atmosphere(
        "Lux_Taiji",
        mats["taiji_sky"],
        mats["taiji_water"],
        sea_z,
        make_rot(-28.0, 45.0, 0.0),
        3.15,
        unreal.Color(255, 238, 205, 255),
        2.20,
        unreal.Color(220, 230, 255, 255),
        unreal.LinearColor(0.048, 0.052, 0.115, 1.0),
        exposure_bias=0.15,
    )

    # Grand Finale Centerpiece: Colossal Slowly-Rotating Taiji_Star_Sphere (1580 cm diameter!) in the sky!
    taiji_mesh = meshes["/Game/LuxGenerated/Extra/Taiji_Star_Sphere"]
    tbox = taiji_mesh.get_bounding_box()
    taiji_scale = 1580.0 / max((tbox.max - tbox.min).z, 1.0)
    taiji_y = 2680.0
    taiji_z = sea_z + 1120.0
    taiji_orb = ACTOR_SUB.spawn_actor_from_class(unreal.ButterflyDreamPropActor, unreal.Vector(0.0, taiji_y, taiji_z), make_rot(0.0, 180.0, 0.0))
    taiji_orb.set_actor_label("Lux_Taiji_ColossalYinYangSphere")
    taiji_orb.configure_prop(taiji_mesh, taiji_scale, True, unreal.LinearColor(1.0, 0.86, 0.50, 1.0), 620.0, 4200.0)
    safe_set_prop(taiji_orb, "BobAmplitude", 32.0)
    safe_set_prop(taiji_orb, "SpinSpeedYaw", 9.5)
    spawn_point_light_cd("Lux_Taiji_SphereCyanYinRim", unreal.Vector(-520.0, taiji_y - 480.0, taiji_z - 120.0), 380.0, 3200.0, linear_color=unreal.LinearColor(0.38, 0.82, 1.0, 1.0))
    spawn_point_light_cd("Lux_Taiji_SphereGoldYangRim", unreal.Vector(520.0, taiji_y - 480.0, taiji_z + 180.0), 420.0, 3200.0, linear_color=unreal.LinearColor(1.0, 0.82, 0.42, 1.0))

    # Giant Cosmic Lotus Altar beneath the Taiji Sphere + Distant Celestial Palace Silhouette
    lotus_mesh = meshes["/Game/LuxGenerated/Props/Crystal_Lotus"]
    lbox = lotus_mesh.get_bounding_box()
    lotus_unit_h = max((lbox.max - lbox.min).z, 1.0)
    lotus_unit_w = max((lbox.max - lbox.min).x, 1.0)
    altar = ACTOR_SUB.spawn_actor_from_class(unreal.ButterflyDreamPropActor, unreal.Vector(0.0, taiji_y, sea_z - 8.0), make_rot(0.0, 0.0, 0.0))
    altar.set_actor_label("Lux_Taiji_CosmicLotusAltar")
    altar.configure_prop(lotus_mesh, 1480.0 / lotus_unit_w, True, unreal.LinearColor(1.0, 0.84, 0.46, 1.0), 220.0, 2600.0)
    safe_set_prop(altar, "SpinSpeedYaw", -4.0)

    pav_mesh = meshes["/Game/LuxGenerated/Pavilion_S01/Floating_Pavilion"]
    pav_box = pav_mesh.get_bounding_box()
    pav_scale = 2100.0 / max((pav_box.max - pav_box.min).z, 1.0)
    spawn_static_landmark("Lux_Taiji_DistantCelestialPalace", pav_mesh, unreal.Vector(0.0, 4150.0, sea_z + 180.0 - pav_box.min.z * pav_scale), make_rot(0.0, 180.0, 0.0), pav_scale)

    # Octagonal 8-Trigram Bagua Array of Monumental Dragon Pillars (660 cm tall!)
    pillar_mesh = meshes["/Game/LuxGenerated/Sanctuary/Dragon_Pillar"]
    bagua_scale = 660.0 / max((pillar_mesh.get_bounding_box().max - pillar_mesh.get_bounding_box().min).z, 1.0)
    for idx in range(8):
        ang = (idx + 0.5) * (2.0 * math.pi / 8.0)
        bx = math.cos(ang) * 1180.0
        by = 1680.0 + math.sin(ang) * 1180.0
        # Keep central flight corridor clear around X=0, Y=500
        if abs(bx) < 280.0 and by < 800.0:
            bx = 360.0 if bx >= 0 else -360.0
        yaw_to_center = math.degrees(math.atan2(1680.0 - by, -bx))
        spawn_static_landmark(f"Lux_Taiji_BaguaPillar_{idx}", pillar_mesh, unreal.Vector(bx, by, sea_z - 8.0), make_rot(0.0, yaw_to_center, 0.0), bagua_scale)
        spawn_point_light_cd(f"Lux_Taiji_BaguaPearl_{idx}", unreal.Vector(bx, by, sea_z + 645.0), 95.0, 1250.0, linear_color=unreal.LinearColor(1.0, 0.85, 0.48, 1.0) if idx % 2 == 0 else unreal.LinearColor(0.48, 0.88, 1.0, 1.0))

    # Central Luminous Guqin Bridge leading toward Ultimate Scroll Gate
    guqin_mesh = meshes["/Game/LuxGenerated/Extra/Luminous_Guqin_Bridge"]
    gbox = guqin_mesh.get_bounding_box()
    g_span = max(float(gbox.max.x - gbox.min.x), float(gbox.max.y - gbox.min.y), 1.0)
    spawn_static_landmark("Lux_Taiji_GuqinBridge", guqin_mesh, unreal.Vector(0.0, 480.0, sea_z - 6.0), make_rot(0.0, 22.0, 0.0), 1120.0 / g_span, enable_collision=True)

    # Twin Cosmic Phoenixes + Floating Lanterns
    guardian_mesh = meshes["/Game/LuxGenerated/Sanctuary/Celestial_Guardian"]
    gu_scale = 420.0 / max((guardian_mesh.get_bounding_box().max - guardian_mesh.get_bounding_box().min).z, 1.0)
    lantern_mesh = meshes["/Game/LuxGenerated/Props/Floating_Lantern"]
    lantern_scale = 128.0 / max((lantern_mesh.get_bounding_box().max - lantern_mesh.get_bounding_box().min).z, 1.0)
    for side in (-1.0, 1.0):
        tag = "L" if side < 0 else "R"
        spawn_static_landmark(f"Lux_Taiji_Phoenix_{tag}", guardian_mesh, unreal.Vector(side * 520.0, 1680.0, sea_z + 18.0), make_rot(0.0, -150.0 if side < 0 else 150.0, 0.0), gu_scale)
        for l_idx in range(4):
            ly = -750.0 + l_idx * 720.0
            lantern = ACTOR_SUB.spawn_actor_from_class(unreal.ButterflyDreamPropActor, unreal.Vector(side * 540.0, ly, sea_z + 340.0 + 55.0 * l_idx), make_rot(0.0, 180.0, 0.0))
            lantern.set_actor_label(f"Lux_Taiji_Lantern_{l_idx}_{tag}")
            lantern.configure_prop(lantern_mesh, lantern_scale, True, unreal.LinearColor(1.0, 0.82, 0.44, 1.0), 54.0, 920.0)

    spawn_loc = unreal.Vector(0.0, -1380.0, 155.0)
    spawn_rot = make_rot(5.2, 90.0, 0.0)
    ps = ACTOR_SUB.spawn_actor_from_class(unreal.PlayerStart, spawn_loc, spawn_rot)
    ps.set_actor_label("Lux_Taiji_PlayerStart")
    spawn_point_light_cd("Lux_Taiji_HeroFill", unreal.Vector(32.0, -1425.0, 242.0), 46.0, 560.0, linear_color=unreal.LinearColor(1.0, 0.92, 0.80, 1.0))

    # Ultimate Grand Finale Portal: Celestial_Scroll_Gate (660 cm tall!) -> F06_SakuraDream
    scroll_gate_mesh = meshes["/Game/LuxGenerated/Extra/Celestial_Scroll_Gate"]
    dais_scale = 420.0 / lotus_unit_w
    spawn_static_landmark("Lux_Taiji_ScrollGateDais", lotus_mesh, unreal.Vector(0.0, 1680.0, sea_z - 4.0), make_rot(0.0, 0.0, 0.0), dais_scale)
    fwd_floor_z = sea_z + lotus_unit_h * dais_scale * 0.86
    fwd_gate = ACTOR_SUB.spawn_actor_from_class(unreal.ButterflyDreamGateActor, unreal.Vector(0.0, 1680.0, fwd_floor_z), make_rot(0.0, 0.0, 0.0))
    fwd_gate.set_actor_label("Lux_Taiji_UltimateScrollGate")
    fwd_gate.apply_gate_preset(True)
    safe_set_prop(fwd_gate, "GateTitle", "终极仙门 ｜ 齐物天书圣卷阙 (周而复始：庄周梦蝶)")
    safe_set_prop(fwd_gate, "TargetMapPackageName", "/Game/Maps/F06_SakuraDream")
    safe_set_prop(fwd_gate, "ResonanceDistance", 2400.0)
    safe_set_prop(fwd_gate, "TriggerTeleportDistance", 350.0)
    fwd_info = bind_and_normalize_gate(fwd_gate, fwd_floor_z, 660.0, meshes, custom_frame_mesh=scroll_gate_mesh)
    spawn_point_light_cd("Lux_Taiji_ScrollGateCrownGold", unreal.Vector(0.0, 1480.0, fwd_floor_z + 360.0), 260.0, 1550.0, linear_color=unreal.LinearColor(1.0, 0.84, 0.44, 1.0))

    # Return Gate -> Lux_CrystalMirageDream (Placed behind PlayerStart at Y = -2550, facing away along -Y)
    ret_gate = ACTOR_SUB.spawn_actor_from_class(unreal.ButterflyDreamGateActor, unreal.Vector(0.0, -2550.0, sea_z + 18.0), make_rot(0.0, 270.0, 0.0))
    ret_gate.set_actor_label("Lux_Taiji_ReturnGate")
    ret_gate.apply_gate_preset(True)
    ret_gate.configure_hinge_offsets(unreal.Vector(-69.475, 13.875, 153.383), unreal.Vector(71.508, 13.822, 142.913), unreal.Vector(1.253, -0.004, 27.039), unreal.Vector(1.253, -0.004, 27.039))
    safe_set_prop(ret_gate, "GateTitle", "归返仙门 ｜ 回溯七宝琉璃幻境")
    safe_set_prop(ret_gate, "TargetMapPackageName", "/Game/Maps/Lux_CrystalMirageDream")
    safe_set_prop(ret_gate, "ResonanceDistance", 900.0)
    safe_set_prop(ret_gate, "TriggerTeleportDistance", 280.0)
    bind_and_normalize_gate(ret_gate, sea_z + 18.0, 430.0, meshes)

    # Dual Counter-Rotating Yin-Yang 3D Particle Swarms around Taiji Sphere + Cosmic Koi School!
    koi_mesh = meshes["/Game/LuxGenerated/Extra/Celestial_Spirit_Koi"]
    blade_mesh = meshes["/Game/LuxGenerated/Scale_T02/Dream_Scale_Blade"]
    swirl_mesh = meshes["/Game/LuxGenerated/Extra/Sakura_Spirit_Swirl"]
    spawn_particle_swarm("Lux_Taiji_YangGoldVortex", swirl_mesh, unreal.Vector(0.0, taiji_y, taiji_z), 56, 1180.0, 620.0, 24.0, 118.0, unreal.LinearColor(1.0, 0.85, 0.45, 1.0), 220.0, 0)
    spawn_particle_swarm("Lux_Taiji_YinCyanCounterVortex", blade_mesh, unreal.Vector(0.0, taiji_y, taiji_z), 72, 1020.0, 780.0, -32.0, 48.0, unreal.LinearColor(0.45, 0.88, 1.0, 1.0), 180.0, 1)
    spawn_particle_swarm("Lux_Taiji_CosmicKoiSchool", koi_mesh, unreal.Vector(0.0, 960.0, sea_z + 380.0), 40, 1050.0, 420.0, 26.0, 98.0, unreal.LinearColor(1.0, 0.88, 0.62, 1.0), 165.0, 3)

    finalize_realm_level(map_path, spawn_loc, spawn_rot)
    REPORT["realms"]["Lux_TaijiAwakeningDream"] = {"player_start": vec_to_list(spawn_loc), "forward_gate": fwd_info}


def main() -> None:
    try:
        REPORT["project_dir"] = str(PROJECT_DIR)
        flush_report()
        step1_open_scratch_and_clean()
        meshes = step2_import_all_26_lux_assets()
        flush_report()
        mats = ensure_lux_5realm_materials()
        flush_report()
        build_realm1_sakura(meshes)
        flush_report()
        build_realm2_starsea(meshes, mats)
        flush_report()
        build_realm3_inkcloud(meshes, mats)
        flush_report()
        build_realm4_crystalmirage(meshes, mats)
        flush_report()
        build_realm5_taijiawakening(meshes, mats)
        REPORT["status"] = "SUCCEEDED"
    except Exception as exc:
        import traceback

        REPORT["status"] = "FAILED"
        REPORT["errors"].append(f"{exc}\n{traceback.format_exc()}")
        unreal.log_error(f"LUX_V3_REBUILD_FAILED: {exc}\n{traceback.format_exc()}")
    finally:
        flush_report()
        unreal.log(f"LUX_V3_REBUILD_DONE status={REPORT['status']} report={REPORT_PATH}")
        quit_editor = getattr(unreal.SystemLibrary, "quit_editor", None)
        if quit_editor:
            quit_editor()
        else:
            unreal.SystemLibrary.execute_console_command(None, "QUIT_EDITOR")


if __name__ == "__main__":
    main()
