import unreal

levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
for map_path in ["/Game/Maps/F06_SakuraDream", "/Game/Maps/Lux_StarSeaDream"]:
    unreal.log(f"================ MAP: {map_path} ================")
    levels.load_level(map_path)
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    unreal.log(f"Total actors: {len(actors)}")
    for a in actors:
        loc = a.get_actor_location()
        scale = a.get_actor_scale3d()
        mesh_name = ""
        smc = a.get_component_by_class(unreal.StaticMeshComponent)
        if smc and smc.static_mesh:
            mesh_name = smc.static_mesh.get_name()
        unreal.log(f"ACTOR: [{a.get_class().get_name()}] '{a.get_actor_label()}' mesh={mesh_name} loc=({loc.x:.1f}, {loc.y:.1f}, {loc.z:.1f}) scale=({scale.x:.1f}, {scale.y:.1f}, {scale.z:.1f})")
