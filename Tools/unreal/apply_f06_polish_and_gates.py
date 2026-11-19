import unreal

LEVEL_SUB = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ACTOR_SUB = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

MAPS = [
    "/Game/Maps/F06_SakuraDream",
    "/Game/Maps/Lux_StarSeaDream",
    "/Game/Maps/Lux_InkCloudDream",
    "/Game/Maps/Lux_CrystalMirageDream",
    "/Game/Maps/Lux_TaijiAwakeningDream",
]


def safe_set_prop(obj, prop: str, val) -> None:
    try:
        obj.set_editor_property(prop, val)
    except Exception:
        pass


def main() -> None:
    # 1. Polish F06 exposure, gate key intensity & closer PlayerStart framing inside cherry canopy
    if not LEVEL_SUB.load_level("/Game/Maps/F06_SakuraDream"):
        raise RuntimeError("Failed loading F06_SakuraDream")

    new_spawn = unreal.Vector(-0.07, -2780.0, -95.0)
    new_rot = unreal.Rotator()
    new_rot.pitch = 6.2
    new_rot.yaw = 90.0
    new_rot.roll = 0.0

    for a in ACTOR_SUB.get_all_level_actors():
        lbl = a.get_actor_label()
        if isinstance(a, unreal.DirectionalLight):
            lc = a.light_component
            lc.set_editor_property("intensity", 1.55)
        elif isinstance(a, unreal.SkyLight):
            lc = a.light_component
            lc.set_editor_property("intensity", 1.22)
        elif isinstance(a, unreal.PostProcessVolume):
            s = a.get_editor_property("settings")
            safe_set_prop(s, "auto_exposure_min_brightness", 0.50)
            safe_set_prop(s, "auto_exposure_max_brightness", 1.40)
            safe_set_prop(s, "auto_exposure_bias", -0.18)
            safe_set_prop(s, "bloom_intensity", 0.26)
            safe_set_prop(s, "bloom_threshold", 1.20)
            a.set_editor_property("settings", s)
        elif isinstance(a, unreal.PlayerStart) or lbl == "Lux_F06_PlayerStart":
            a.set_actor_location(new_spawn, False, False)
            a.set_actor_rotation(new_rot, False)
        elif lbl == "Lux_F06_HeroButterflyFill" and isinstance(a, unreal.PointLight):
            a.set_actor_location(new_spawn + unreal.Vector(35.0, -45.0, 95.0), False, False)
            a.light_component.set_editor_property("intensity", 15.0)
        elif lbl == "Lux_F06_GateGoldEaveKey" and isinstance(a, unreal.PointLight):
            a.light_component.set_editor_property("intensity", 78.0)
        elif lbl == "Lux_F06_GateTurquoiseRoof" and isinstance(a, unreal.PointLight):
            a.light_component.set_editor_property("intensity", 62.0)

    for mp in MAPS:
        if mp != "/Game/Maps/F06_SakuraDream":
            if not LEVEL_SUB.load_level(mp):
                raise RuntimeError(f"Failed loading {mp}")
        for a in ACTOR_SUB.get_all_level_actors():
            if isinstance(a, unreal.ButterflyDreamGateActor):
                t = str(a.get_editor_property("GateTitle"))
                nt = t.replace(" · ", " ｜ ").replace("·", "｜")
                if nt != t:
                    a.set_editor_property("GateTitle", nt)
        if not LEVEL_SUB.save_current_level():
            raise RuntimeError(f"Failed saving {mp}")
        unreal.log(f"POLISHED_MAP {mp}")


if __name__ == "__main__":
    main()
