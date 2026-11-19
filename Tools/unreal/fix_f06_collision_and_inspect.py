import json
from pathlib import Path
import unreal

LEVEL_SUB = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ACTOR_SUB = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
REPORT_PATH = Path(r"E:\紫萱2版\Evidence\Unreal\LuxRebuild\f06-collision-inspect.json")


def vec_list(v: unreal.Vector) -> list[float]:
    return [round(float(v.x), 3), round(float(v.y), 3), round(float(v.z), 3)]


def rot_list(r: unreal.Rotator) -> list[float]:
    return [round(float(r.pitch), 3), round(float(r.yaw), 3), round(float(r.roll), 3)]


def main() -> None:
    if not LEVEL_SUB.load_level("/Game/Maps/F06_SakuraDream"):
        raise RuntimeError("Failed loading /Game/Maps/F06_SakuraDream")

    all_actors = ACTOR_SUB.get_all_level_actors()
    interesting = []
    disabled_collision_actors = []
    lantern_ys = []
    tree_bounds = []

    for a in all_actors:
        lbl = a.get_actor_label()
        name = a.get_name()
        cls = a.get_class().get_name()
        loc = a.get_actor_location()
        rot = a.get_actor_rotation()
        scale = a.get_actor_scale3d()
        orig, ext = a.get_actor_bounds(False)

        if "Lantern_point" in lbl or "Lantern_point" in name:
            lantern_ys.append(float(loc.y))
        if "Cherry" in lbl or "Cherry" in name:
            tree_bounds.append((vec_list(orig - ext), vec_list(orig + ext)))

        if isinstance(a, unreal.StaticMeshActor):
            smc = a.static_mesh_component
            sm = smc.static_mesh if smc else None
            sm_path = sm.get_path_name() if sm else ""
            if smc and (
                "SkyDome" in lbl
                or "Sphere" in sm_path
                or "Background_gradient" in lbl
                or "Moon" in lbl
                or "foliage" in sm_path.lower()
                or "Cherry" in lbl
                or "Grass" in lbl
            ):
                prev_col = str(smc.get_collision_enabled())
                smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                disabled_collision_actors.append({
                    "actor": name,
                    "label": lbl,
                    "mesh": sm_path,
                    "prev_collision": prev_col,
                    "loc": vec_list(loc),
                    "scale": vec_list(scale),
                    "bounds_min": vec_list(orig - ext),
                    "bounds_max": vec_list(orig + ext),
                })

            if any(k in lbl or k in name or k in sm_path for k in (
                "StaticMeshActor_1", "SkyDome", "Sphere", "Gradient", "Moon",
                "Pagoda", "Stairs", "04-main_node_0", "Cube_001", "Fog"
            )):
                mats = [m.get_path_name() if m else None for m in (smc.get_materials() if smc else [])]
                interesting.append({
                    "actor": name,
                    "label": lbl,
                    "class": cls,
                    "mesh": sm_path,
                    "loc": vec_list(loc),
                    "rot": rot_list(rot),
                    "scale": vec_list(scale),
                    "bounds_min": vec_list(orig - ext),
                    "bounds_max": vec_list(orig + ext),
                    "collision": str(smc.get_collision_enabled()) if smc else None,
                    "hidden_in_game": bool(a.is_hidden_ed()) if hasattr(a, "is_hidden_ed") else None,
                    "materials": mats,
                })
        elif isinstance(a, (unreal.PlayerStart, unreal.CameraActor, unreal.ButterflyDreamGateActor, unreal.ButterflyParticleSwarmActor)):
            interesting.append({
                "actor": name,
                "label": lbl,
                "class": cls,
                "loc": vec_list(loc),
                "rot": rot_list(rot),
                "scale": vec_list(scale),
                "bounds_min": vec_list(orig - ext),
                "bounds_max": vec_list(orig + ext),
            })

    if not LEVEL_SUB.save_current_level():
        raise RuntimeError("Failed saving /Game/Maps/F06_SakuraDream")

    # Quick read-only spawn check on Realms 2..5
    other_realms = {}
    for mpath in (
        "/Game/Maps/Lux_StarSeaDream",
        "/Game/Maps/Lux_InkCloudDream",
        "/Game/Maps/Lux_CrystalMirageDream",
        "/Game/Maps/Lux_TaijiAwakeningDream",
    ):
        if LEVEL_SUB.load_level(mpath):
            ps = [x for x in ACTOR_SUB.get_all_level_actors() if isinstance(x, unreal.PlayerStart)]
            gates = [x for x in ACTOR_SUB.get_all_level_actors() if isinstance(x, unreal.ButterflyDreamGateActor)]
            swarms = [x for x in ACTOR_SUB.get_all_level_actors() if isinstance(x, unreal.ButterflyParticleSwarmActor)]
            other_realms[mpath] = {
                "player_start": vec_list(ps[0].get_actor_location()) if ps else None,
                "player_rot": rot_list(ps[0].get_actor_rotation()) if ps else None,
                "gate_count": len(gates),
                "swarm_count": len(swarms),
            }

    lantern_ys.sort()
    out = {
        "status": "SUCCEEDED",
        "disabled_collision_count": len(disabled_collision_actors),
        "disabled_collision_sample": disabled_collision_actors[:15],
        "lantern_y_min": min(lantern_ys) if lantern_ys else None,
        "lantern_y_max": max(lantern_ys) if lantern_ys else None,
        "interesting_actors": interesting[:40],
        "other_realms": other_realms,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    unreal.log(f"F06_INSPECT_DONE disabled_col={len(disabled_collision_actors)}")


if __name__ == "__main__":
    main()
