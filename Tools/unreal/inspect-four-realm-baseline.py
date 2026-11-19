"""Inventory saved actors in the four recovery maps without saving any packages."""

import json
import runpy
from pathlib import Path

import unreal


MAPS = (
    "Lux_StarSeaDream",
    "Lux_InkCloudDream",
    "Lux_CrystalMirageDream",
    "Lux_TaijiAwakeningDream",
)
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def value(obj, name):
    result = obj.get_editor_property(name)
    if isinstance(result, unreal.Object):
        return result.get_path_name()
    if isinstance(result, unreal.LinearColor):
        return [result.r, result.g, result.b, result.a]
    if isinstance(result, unreal.Vector):
        return vector(result)
    if isinstance(result, (bool, float, int, str)) or result is None:
        return result
    return str(result)


def vector(v):
    return [v.x, v.y, v.z]


def read(actor):
    rotation = actor.get_actor_rotation()
    meshes = []
    for comp in actor.get_components_by_class(unreal.StaticMeshComponent):
        if not comp.static_mesh:
            continue
        meshes.append({
            "component": comp.get_name(),
            "mesh": comp.static_mesh.get_path_name(),
            "overrides": [mat.get_path_name() if mat else None for mat in
                          comp.get_editor_property("override_materials")],
        })
    row = {
        "label": actor.get_actor_label(),
        "class": actor.get_class().get_name(),
        "location": vector(actor.get_actor_location()),
        "rotation": [rotation.pitch, rotation.yaw, rotation.roll],
        "scale": vector(actor.get_actor_scale3d()),
        "meshes": meshes,
    }
    if isinstance(actor, unreal.ButterflyParticleSwarmActor):
        row["swarm"] = {
            name: value(actor, name) for name in (
                "swarm_asset", "instance_count", "swarm_radius", "swarm_height_span",
                "orbit_speed_degrees", "base_instance_scale", "swarm_glow_color",
                "swarm_light_candelas", "motion_pattern", "mesh_yaw_offset_degrees")
        }
    if isinstance(actor, unreal.ButterflyDreamPropActor):
        row["prop"] = {
            name: value(actor, name) for name in (
                "bob_amplitude", "bob_speed", "spin_speed_yaw", "sway_amplitude_degrees",
                "sway_speed", "breathe_scale_amplitude", "phase_offset")
        }
        component_scale = actor.prop_mesh.get_editor_property("relative_scale3d")
        row["prop_scale"] = component_scale.x
        row["light"] = read_light(actor.glow_light)
    if isinstance(actor, unreal.PointLight):
        row["light"] = read_light(actor.light_component)
    return row


def read_light(component):
    color = component.get_light_color()
    return {
        "color": [color.r, color.g, color.b, color.a],
        "intensity": component.get_editor_property("intensity"),
        "radius": component.get_editor_property("attenuation_radius"),
        "visible": component.get_editor_property("visible"),
    }


def main():
    output = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()))
    report = {}
    for folder in ("RecoveryBaseline", "Maps"):
        report[folder] = {}
        for name in MAPS:
            path = f"/Game/{folder}/{name}"
            if not LEVELS.load_level(path):
                raise RuntimeError(f"Could not load {path}")
            report[folder][name] = [read(actor) for actor in ACTORS.get_all_level_actors()]
    (output / "recovery-actors.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
        project_dir = Path(unreal.Paths.project_dir()).resolve()
        if (project_dir / "Saved" / "restore-dressing.request").is_file():
            runpy.run_path(str(Path(__file__).with_name("restore-four-realm-set-dressing.py")), run_name="__main__")
    finally:
        unreal.SystemLibrary.quit_editor()
