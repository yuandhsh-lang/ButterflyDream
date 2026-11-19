import unreal

level_sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

map_path = "/Game/Maps/Lux_StarSeaDream"
unreal.log(f"=== Loading {map_path} ===")
level_sub.load_level(map_path)

actors = actor_sub.get_all_level_actors()
unreal.log(f"Total actors in StarSea: {len(actors)}")

for a in actors:
    lbl = a.get_actor_label()
    cls = a.get_class().get_name()
    loc = a.get_actor_location()
    rot = a.get_actor_rotation()
    scale = a.get_actor_scale3d()
    origin, ext = a.get_actor_bounds(False)
    
    mesh_info = ""
    smc = a.get_component_by_class(unreal.StaticMeshComponent)
    if smc and smc.static_mesh:
        mesh_info = f"mesh={smc.static_mesh.get_path_name()} mat={smc.get_material(0).get_name() if smc.get_material(0) else 'None'}"
        
    unreal.log(f"STARSEA_ACTOR: [{cls}] '{lbl}' loc=({loc.x:.1f}, {loc.y:.1f}, {loc.z:.1f}) rot=({rot.pitch:.1f}, {rot.yaw:.1f}, {rot.roll:.1f}) scale=({scale.x:.1f}, {scale.y:.1f}, {scale.z:.1f}) bounds_ext=({ext.x:.1f}, {ext.y:.1f}, {ext.z:.1f}) {mesh_info}")
