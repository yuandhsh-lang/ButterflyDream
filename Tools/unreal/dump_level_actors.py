import unreal
import json

level_sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

results = {}

for map_path in [
    "/Game/Maps/F06_SakuraDream",
    "/Game/Maps/Lux_StarSeaDream",
    "/Game/Maps/Lux_InkCloudDream",
    "/Game/Maps/Lux_CrystalMirageDream",
    "/Game/Maps/Lux_TaijiAwakeningDream",
]:
    level_sub.load_level(map_path)
    actors = actor_sub.get_all_level_actors()
    map_data = []
    for a in actors:
        label = a.get_actor_label()
        loc = a.get_actor_location()
        rot = a.get_actor_rotation()
        scale = a.get_actor_scale3d()
        mesh_name = None
        mats = []
        if isinstance(a, unreal.StaticMeshActor):
            smc = a.static_mesh_component
            if smc.static_mesh:
                mesh_name = smc.static_mesh.get_path_name()
            mats = [smc.get_material(i).get_path_name() if smc.get_material(i) else "None" for i in range(smc.get_num_materials())]
        elif isinstance(a, unreal.ButterflyDreamGateActor):
            mesh_name = "GateActor"
        elif isinstance(a, unreal.ButterflyDreamPropActor):
            mesh_name = "PropActor"
            
        map_data.append({
            "label": label,
            "class": a.get_class().get_name(),
            "loc": [round(loc.x, 1), round(loc.y, 1), round(loc.z, 1)],
            "rot": [round(rot.pitch, 1), round(rot.yaw, 1), round(rot.roll, 1)],
            "scale": [round(scale.x, 1), round(scale.y, 1), round(scale.z, 1)],
            "mesh": mesh_name,
            "mats": mats,
            "hidden": a.get_actor_hidden_in_game()
        })
    results[map_path] = map_data

with open("E:/紫萱2版/Evidence/Unreal/actors_dump.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("ACTORS_DUMP_COMPLETE")
