import unreal

levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
levels.load_level("/Game/Maps/F06_SakuraDream")
for a in unreal.EditorLevelLibrary.get_all_level_actors():
    if "SkyDome" in a.get_actor_label():
        smc = a.get_component_by_class(unreal.StaticMeshComponent)
        if smc and smc.static_mesh:
            unreal.log(f"F06_SKYDOME MESH: {smc.static_mesh.get_path_name()}")
            mat = smc.get_material(0)
            if mat:
                unreal.log(f"F06_SKYDOME MAT: {mat.get_path_name()}")
