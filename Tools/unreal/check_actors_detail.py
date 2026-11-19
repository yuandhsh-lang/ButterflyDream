import unreal

def log(msg):
    unreal.log(f"[ACTOR_DETAIL] {msg}")

level_sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

for map_path in ["/Game/Maps/F06_SakuraDream", "/Game/Maps/Lux_StarSeaDream"]:
    log(f"=== CHECKING {map_path} ===")
    level_sub.load_level(map_path)
    actors = actor_sub.get_all_level_actors()
    log(f"Total actors: {len(actors)}")
    for a in actors:
        label = a.get_actor_label()
        loc = a.get_actor_location()
        rot = a.get_actor_rotation()
        scale = a.get_actor_scale3d()
        mesh_name = "N/A"
        mats = []
        if isinstance(a, unreal.StaticMeshActor):
            smc = a.static_mesh_component
            if smc.static_mesh:
                mesh_name = smc.static_mesh.get_path_name()
            mats = [smc.get_material(i).get_path_name() if smc.get_material(i) else "None" for i in range(smc.get_num_materials())]
        log(f"  [{label}] class={a.get_class().get_name()} loc=({loc.x:.1f}, {loc.y:.1f}, {loc.z:.1f}) rot=({rot.pitch:.1f}, {rot.yaw:.1f}, {rot.roll:.1f}) scale=({scale.x:.1f}, {scale.y:.1f}, {scale.z:.1f}) mesh={mesh_name} mats={mats}")
