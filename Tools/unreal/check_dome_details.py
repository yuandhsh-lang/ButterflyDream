import unreal

mat = unreal.load_asset("/Game/LuxGenerated/Materials/M_Lux_StarSeaSkyDome")
unreal.log(f"MAT: {mat.get_name()}")
unreal.log(f"  two_sided: {mat.get_editor_property('two_sided')}")
unreal.log(f"  is_sky: {mat.get_editor_property('is_sky')}")
unreal.log(f"  shading_model: {mat.get_editor_property('shading_model')}")
unreal.log(f"  blend_mode: {mat.get_editor_property('blend_mode')}")

# Check mesh
mesh = unreal.load_asset("/Engine/BasicShapes/Sphere")
unreal.log(f"MESH: {mesh.get_name()}")
box = mesh.get_bounding_box()
unreal.log(f"  box min: ({box.min.x}, {box.min.y}, {box.min.z}) max: ({box.max.x}, {box.max.y}, {box.max.z})")

# Check level
level_sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
level_sub.load_level("/Game/Maps/Lux_StarSeaDream")

for a in actor_sub.get_all_level_actors():
    if "SkyDome" in a.get_actor_label():
        smc = a.get_component_by_class(unreal.StaticMeshComponent)
        unreal.log(f"ACTOR: {a.get_actor_label()}")
        unreal.log(f"  loc: {a.get_actor_location()}")
        unreal.log(f"  rot: {a.get_actor_rotation()}")
        unreal.log(f"  scale: {a.get_actor_scale3d()}")
        unreal.log(f"  visible: {a.get_actor_enable_collision()}")
        unreal.log(f"  hidden: {a.is_hidden()}")
        if smc:
            unreal.log(f"  smc hidden: {smc.get_editor_property('hidden_in_game')}")
            unreal.log(f"  smc visible: {smc.is_visible()}")
            unreal.log(f"  smc cast_shadow: {smc.get_editor_property('cast_shadow')}")
            unreal.log(f"  smc materials: {[smc.get_material(i).get_name() if smc.get_material(i) else None for i in range(smc.get_num_materials())]}")
