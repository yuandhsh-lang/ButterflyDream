import unreal

subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
subsystem.load_map('/Game/Maps/Lux_StarSeaDream')
actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = actor_sub.get_all_level_actors()
print(f"TOTAL ACTORS: {len(actors)}")
for a in sorted(actors, key=lambda x: x.get_name()):
    loc = a.get_actor_location()
    rot = a.get_actor_rotation()
    scale = a.get_actor_scale3d()
    print(f"ACTOR: {a.get_name():<32} class={a.get_class().get_name():<20} loc=({loc.x:7.1f}, {loc.y:7.1f}, {loc.z:7.1f}) rot=({rot.pitch:5.1f}, {rot.yaw:5.1f}, {rot.roll:5.1f}) scale=({scale.x:6.1f}, {scale.y:6.1f}, {scale.z:6.1f})")
    # If static mesh actor, check mesh and material
    if isinstance(a, unreal.StaticMeshActor):
        smc = a.static_mesh_component
        mesh = smc.static_mesh.get_name() if smc.static_mesh else "None"
        mats = [smc.get_material(i).get_name() if smc.get_material(i) else "None" for i in range(smc.get_num_materials())]
        print(f"       Mesh: {mesh} | Materials: {mats}")
