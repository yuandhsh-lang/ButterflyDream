"""Merge selected saved dressing into the current four maps in the recovery project."""

import json
import re
import sys
import traceback
from pathlib import Path

import unreal


PROJECT = Path("E:/ButterflyDream_Recovery/Project")
SOURCE_MODELS = Path(__file__).resolve().parents[2] / "Assets/LuxGenerated/Optimized/FX_20261119"
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)

DRESSING = {
    "StarSea": r"FloatingPavilion|Lantern_\d+_[LR]|DragonPillar_\d+_[LR]|DragonPearl_\d+_[LR]|Lotus_\d+_[LR]|GiantPavilionLotus|RightDais|HeroGuardian(?:Key)?|BridgeGlow|Pavilion(?:GoldEave|CyanGlow)|KoiSchool|StardustHelix|PalaceHalo",
    "InkCloud": r"MirrorWater|LuminousGuqinBridge|CentralMountainSanctuary|FlankMountain_[LR]|FlankAmber_[LR]|Lantern_\d+_[LR]|Pillar_\d+_[LR]|PillarLight_\d+_[LR]|ForwardDais|GuqinStringsGold|GuqinJadeResonance|GuqinKoiSchool|GoldBrushHelix|MountainSpiritSwirl",
    "Crystal": r"MirrorWater|CentralBridge|ForwardDais|GiantLotusThrone|FloatingGarden_[LR]|Phoenix_[LR]|MirageKoiSchool|PrismShardCascade|PagodaRainbowHelix|SevenTierPagoda|Pagoda(?:RubyBase|EmeraldMid|AmethystTop)|Pad_\d+_[LR]|GardenGlow_[LR]",
    "Taiji": r"MirrorWater|DistantCelestialPalace|GuqinBridge|CosmicLotusAltar|Lantern_\d+_[LR]|Phoenix_[LR]|ScrollGateDais|ScrollGateCrownGold|CosmicKoiSchool|YangGoldVortex|YinCyanCounterVortex",
}
OPTIMIZED_SOURCES = (
    "/Game/LuxGenerated/Scale_T02/Dream_Scale_Blade",
    "/Game/LuxGenerated/Extra/Celestial_Spirit_Koi",
    "/Game/LuxGenerated/Extra/Sakura_Spirit_Swirl",
    "/Game/LuxGenerated/Tunnel_T01/Tunnel_Ring",
    "/Game/LuxGenerated/Tunnel_T01/Tunnel_Ring",
)


def load(path, cls):
    asset = ASSETS.load_asset(path)
    if not isinstance(asset, cls):
        raise RuntimeError(f"Missing {cls.__name__}: {path}")
    return asset


def save(asset):
    if not ASSETS.save_loaded_asset(asset, False):
        raise RuntimeError(f"Could not save {asset.get_path_name()}")


def optimized_meshes():
    meshes = {}
    importer = unreal.InterchangeManager.get_interchange_manager_scripted()
    params = unreal.ImportAssetParameters()
    params.set_editor_property("is_automated", True)
    for source in OPTIMIZED_SOURCES:
        original = load(source, unreal.StaticMesh)
        name = original.get_name() + "_FX"
        path = f"/Game/Optimized/{name}"
        if not ASSETS.does_asset_exist(path):
            source_file = SOURCE_MODELS / f"{name}.glb"
            if not source_file.is_file():
                raise RuntimeError(f"Missing optimized source: {source_file}")
            source_data = importer.create_source_data(str(source_file))
            if not source_data or not importer.can_translate_source_data(source_data):
                raise RuntimeError(f"Interchange cannot import {source_file}")
            import_folder = f"/Game/Optimized/_Import_{name}"
            imported = importer.import_asset(import_folder, source_data, params) or []
            candidates = [asset for asset in imported if isinstance(asset, unreal.StaticMesh)]
            if not candidates:
                candidates = [
                    asset for asset_path in ASSETS.list_assets(import_folder, recursive=True)
                    if isinstance((asset := ASSETS.load_asset(asset_path)), unreal.StaticMesh)
                ]
            if not candidates:
                raise RuntimeError(f"Interchange did not create a static mesh from {source_file}")
            imported_path = candidates[0].get_path_name().split(".")[0]
            ASSETS.save_directory(import_folder, True, True)
            if not ASSETS.rename_asset(imported_path, path):
                raise RuntimeError(f"Could not move {imported_path} to {path}")
        mesh = load(path, unreal.StaticMesh)
        for index, slot in enumerate(original.get_editor_property("static_materials")):
            mesh.set_material(index, slot.material_interface)
        settings = mesh.get_editor_property("nanite_settings")
        settings.set_editor_property("enabled", False)
        mesh.set_editor_property("nanite_settings", settings)
        save(mesh)
        meshes[source] = mesh
    return meshes


def set_mesh_overrides(component, mesh_spec):
    for index, material in enumerate(mesh_spec["overrides"]):
        if material:
            component.set_material(index, load(material, unreal.MaterialInterface))


def restore_actor(row, location, scale, optimized):
    pitch, yaw, roll = row["rotation"]
    actor_class = getattr(unreal, row["class"])
    actor = ACTORS.spawn_actor_from_class(
        actor_class, unreal.Vector(*location), unreal.Rotator(pitch=pitch, yaw=yaw, roll=roll))
    actor.set_actor_label(row["label"])
    actor.set_actor_scale3d(unreal.Vector(*scale))
    if "swarm" in row:
        settings = row["swarm"]
        original = load(settings["swarm_asset"], unreal.StaticMesh)
        mesh = optimized.get(original.get_path_name().split(".")[0], original)
        actor.configure_swarm(
            mesh, settings["instance_count"], settings["swarm_radius"], settings["swarm_height_span"],
            settings["orbit_speed_degrees"], settings["base_instance_scale"],
            unreal.LinearColor(*settings["swarm_glow_color"]), min(settings["swarm_light_candelas"], 60.0),
            settings["motion_pattern"])
        actor.set_editor_property("mesh_yaw_offset_degrees", settings["mesh_yaw_offset_degrees"])
    elif "prop" in row:
        light = row["light"]
        actor.configure_prop(
            load(row["meshes"][0]["mesh"], unreal.StaticMesh), row["prop_scale"], False,
            unreal.LinearColor(*light["color"]), 0.0, light["radius"])
        for prop, value in row["prop"].items():
            actor.set_editor_property(prop, value)
    elif isinstance(actor, unreal.StaticMeshActor):
        component = actor.static_mesh_component
        component.set_static_mesh(load(row["meshes"][0]["mesh"], unreal.StaticMesh))
        set_mesh_overrides(component, row["meshes"][0])
        component.set_collision_profile_name("NoCollision")
        component.set_editor_property("generate_overlap_events", False)
    elif isinstance(actor, unreal.PointLight):
        light = row["light"]
        component = actor.light_component
        component.set_mobility(unreal.ComponentMobility.MOVABLE)
        component.set_intensity_units(unreal.LightUnits.CANDELAS)
        component.set_intensity(min(light["intensity"], 125.0))
        component.set_attenuation_radius(min(light["radius"], 1450.0))
        component.set_light_color(unreal.LinearColor(*light["color"]))
        component.set_cast_shadows(False)
    else:
        raise RuntimeError(f"Unsupported dressing actor: {row['label']} ({row['class']})")
    return actor


def selected_scale(name, suffix, row):
    if name != "Taiji":
        return row["scale"]
    sizes = {
        "DistantCelestialPalace": (2100.0, "height"),
        "GuqinBridge": (1120.0, "span"),
        "Phoenix_L": (420.0, "height"),
        "Phoenix_R": (420.0, "height"),
        "ScrollGateDais": (420.0, "width"),
    }
    if suffix in sizes:
        target, dimension = sizes[suffix]
        bounds = load(row["meshes"][0]["mesh"], unreal.StaticMesh).get_bounding_box()
        extent = bounds.max - bounds.min
        mesh_size = {"height": extent.z, "span": max(extent.x, extent.y), "width": extent.x}
        return [target / max(mesh_size[dimension], 1.0)] * 3
    return row["scale"] if suffix == "MirrorWater" else [1.0] * 3


def selected_location(name, suffix, row, scale, current):
    if name == "Taiji":
        sea = -140.0
        sphere_location = current["Lux_Taiji_CentralYinYangSphere"]["location"]
        if suffix == "DistantCelestialPalace":
            mesh = load(row["meshes"][0]["mesh"], unreal.StaticMesh)
            return [0.0, 4150.0, sea + 180.0 - mesh.get_bounding_box().min.z * scale[2]]
        if suffix == "CosmicLotusAltar":
            return [sphere_location[0], sphere_location[1], sea - 8.0]
        if suffix == "GuqinBridge":
            return [0.0, 480.0, sea - 6.0]
        if suffix.startswith("Phoenix_"):
            side = -1.0 if suffix.endswith("_L") else 1.0
            return [side * 520.0, 1680.0, sea + 18.0]
        if suffix.startswith("Lantern_"):
            match = re.fullmatch(r"Lantern_(\d+)_([LR])", suffix)
            index = int(match.group(1))
            side = -1.0 if match.group(2) == "L" else 1.0
            return [side * 540.0, -750.0 + index * 720.0, sea + 340.0 + 55.0 * index]
        if suffix == "CosmicKoiSchool":
            return [0.0, 960.0, sea + 380.0]
        if suffix in ("YangGoldVortex", "YinCyanCounterVortex"):
            return sphere_location
        if suffix in ("ScrollGateDais", "ScrollGateCrownGold"):
            gate_x, gate_y, gate_z = current["Lux_Taiji_ForwardGate"]["location"]
            return [gate_x, gate_y, gate_z - 30.0 if suffix == "ScrollGateDais" else gate_z + 360.0]
    if name == "Crystal" and suffix == "FloatingGarden_L":
        return [-820.0, 820.0, 190.0]
    if name == "Crystal" and suffix == "FloatingGarden_R":
        return [820.0, 820.0, 190.0]
    if name == "Crystal" and suffix == "SevenTierPagoda":
        return [0.0, 2750.0, 240.0]
    if name == "Crystal" and suffix.startswith("Pagoda"):
        height = {"PagodaRubyBase": 420.0, "PagodaEmeraldMid": 1250.0, "PagodaAmethystTop": 2050.0}.get(suffix, 420.0)
        return [0.0, 2230.0, height]
    if name == "Crystal" and suffix == "GardenGlow_L":
        return [-760.0, 760.0, 520.0]
    if name == "Crystal" and suffix == "GardenGlow_R":
        return [760.0, 760.0, 520.0]
    if name == "Crystal" and suffix == "CentralBridge":
        return [0.0, 480.0, -10.0]
    if name == "Crystal" and suffix == "ForwardDais":
        return [0.0, 1680.0, -4.0]
    if name == "StarSea" and suffix == "FloatingPavilion":
        return [0.0, 2680.0, 220.0]
    if name == "StarSea" and suffix in ("PavilionGoldEave", "PavilionCyanGlow"):
        return [0.0, 2460.0, 850.0 if suffix == "PavilionGoldEave" else 300.0]
    if name == "InkCloud" and suffix == "CentralMountainSanctuary":
        return [0.0, 2750.0, 120.0]
    if name == "InkCloud" and suffix.startswith("FlankMountain_"):
        side = -1.0 if suffix.endswith("_L") else 1.0
        return [side * 1580.0, 2080.0, 180.0]
    if name == "InkCloud" and suffix.startswith("FlankAmber_"):
        side = -1.0 if suffix.endswith("_L") else 1.0
        return [side * 1180.0, 1820.0, 840.0]
    if name == "InkCloud" and suffix == "GuqinStringsGold":
        return [0.0, 480.0, 130.0]
    if name == "InkCloud" and suffix == "GuqinJadeResonance":
        return [0.0, 480.0, 180.0]
    if name == "InkCloud" and suffix == "MountainSpiritSwirl":
        return [0.0, 2550.0, 1150.0]
    if name == "StarSea" and suffix == "GiantPavilionLotus":
        return [0.0, 2680.0, -152.0]
    if name == "StarSea" and suffix in ("KoiSchool", "StardustHelix", "PalaceHalo"):
        return {
            "KoiSchool": [0.0, 520.0, 180.0],
            "StardustHelix": [0.0, 1660.0, 280.0],
            "PalaceHalo": [0.0, 2680.0, 1010.0],
        }[suffix]
    if name == "InkCloud" and suffix in ("GuqinKoiSchool", "GoldBrushHelix"):
        return [0.0, 480.0 if suffix == "GuqinKoiSchool" else 1680.0,
                200.0 if suffix == "GuqinKoiSchool" else 360.0]
    if name == "Crystal" and suffix in ("GiantLotusThrone", "PagodaRainbowHelix", "MirageKoiSchool", "PrismShardCascade"):
        return {
            "GiantLotusThrone": [0.0, 2680.0, -150.0],
            "PagodaRainbowHelix": [0.0, 2750.0, 1040.0],
            "MirageKoiSchool": [0.0, 560.0, 200.0],
            "PrismShardCascade": [0.0, 1180.0, 380.0],
        }[suffix]
    return row["location"]


def restore_maps(audit, optimized):
    output = []
    for name, rows in audit["RecoveryBaseline"].items():
        realm = next(realm for realm in DRESSING if name.startswith(f"Lux_{realm}"))
        baseline = {row["label"]: row for row in rows}
        current = {row["label"]: row for row in audit["Maps"][name]}
        path = f"/Game/Maps/{name}"
        if not LEVELS.load_level(path):
            raise RuntimeError(f"Could not load {path}")
        actors = {actor.get_actor_label(): actor for actor in ACTORS.get_all_level_actors()}
        sky_label = f"Lux_{realm}_SkyDome"
        set_mesh_overrides(actors[sky_label].static_mesh_component, baseline[sky_label]["meshes"][0])
        restored = []
        for label, row in baseline.items():
            prefix = f"Lux_{realm}_"
            suffix = label.removeprefix(prefix)
            if label.startswith(prefix) and re.fullmatch(DRESSING[realm], suffix):
                scale = selected_scale(realm, suffix, row)
                location = selected_location(realm, suffix, row, scale, current)
                actor = actors.get(label)
                if actor is None and suffix == "MirrorWater":
                    actor = actors.get(f"Lux_{realm}_OpenWater")
                if actor is not None:
                    actor.set_actor_location(unreal.Vector(*location), False, True)
                    actor.set_actor_scale3d(unreal.Vector(*scale))
                    if isinstance(actor, unreal.StaticMeshActor):
                        component = actor.static_mesh_component
                        component.set_static_mesh(load(row["meshes"][0]["mesh"], unreal.StaticMesh))
                        set_mesh_overrides(component, row["meshes"][0])
                        component.set_collision_profile_name("NoCollision")
                        component.set_editor_property("generate_overlap_events", False)
                else:
                    restore_actor(row, location, scale, optimized)
                restored.append(label)
        if not restored or not LEVELS.save_current_level():
            raise RuntimeError(f"Could not restore dressing in {path}")
        output.append({"map": path, "restored": restored})
    return output


def build_fx(output, optimized):
    bridge = unreal.FourRealmNiagaraEditorBridge
    ring = load("/Game/LuxGenerated/Gate_G03/StarGate_OuterRing", unreal.StaticMesh)
    if not ring.get_editor_property("allow_cpu_access"):
        ring.set_editor_property("allow_cpu_access", True)
        save(ring)
    return {
        "wing_ribbon": bridge.create_wing_ribbon_system(str(output / "wing-ribbon.json")),
        "gate_swarm": bridge.create_gate_mesh_swarm_system(
            ring, optimized[OPTIMIZED_SOURCES[0]], str(output / "gate-swarm.json")),
    }


def main():
    if Path(unreal.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise RuntimeError("Run this script in the isolated recovery project.")
    output = PROJECT / "Saved"
    report = {"status": "FAILED"}
    try:
        audit = json.loads((output / "recovery-actors.json").read_text(encoding="utf-8"))
        optimized = optimized_meshes()
        report["maps"] = restore_maps(audit, optimized)
        report["fx"] = build_fx(output, optimized)
        if all(report["fx"].values()):
            report["status"] = "SUCCEEDED"
    except Exception:
        report["error"] = traceback.format_exc()
        unreal.log_error(report["error"])
    finally:
        (output / "dressing-restoration.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        unreal.SystemLibrary.quit_editor()


if __name__ == "__main__":
    main()
