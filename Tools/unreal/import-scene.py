import hashlib
import json
import os
from pathlib import Path
import traceback
import unreal

root = Path(__file__).resolve().parents[2]
scene_id = os.environ.get("BUTTERFLY_SCENE_ID", "F09")
scenes = {
    "F09": {"source": "SourceScenes/Working/F09/White_Lands.ue.glb", "map": "/Game/Maps/F09_Unawakened"},
    "F06": {"source": "SourceScenes/Working/F06/F06.ue.glb", "map": "/Game/Maps/F06_SakuraDream"},
}
if scene_id not in scenes:
    raise ValueError(f"Unsupported scene: {scene_id}")
source = root / scenes[scene_id]["source"]
map_path = scenes[scene_id]["map"]
content_path = f"/Game/ThirdParty/{scene_id}"
evidence = root / "Evidence" / "Unreal" / scene_id
evidence.mkdir(parents=True, exist_ok=True)
report = {
    "scene_id": scene_id,
    "source": str(source),
    "map_path": map_path,
    "content_path": content_path,
    "status": "API_INSPECTION",
    "engine_version": unreal.SystemLibrary.get_engine_version(),
    "visual_parity_status": "NOT_TESTED",
    "flight_status": "NOT_TESTED",
}
if not source.is_file():
    raise FileNotFoundError(source)
report["source_bytes"] = source.stat().st_size
report["source_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()


def documentation(value, names):
    return {name: getattr(getattr(value, name, None), "__doc__", None) for name in names}


def write_report():
    (evidence / "import-result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


try:
    manager = unreal.InterchangeManager.get_interchange_manager_scripted()
    report["api"] = {
        "import_scene": unreal.InterchangeManager.import_scene.__doc__,
        "import_asset": unreal.InterchangeManager.import_asset.__doc__,
        "asset_import_tasks": unreal.AssetTools.import_asset_tasks.__doc__,
        "create_source_data": unreal.InterchangeManager.create_source_data.__doc__,
        "level_subsystem": dir(unreal.LevelEditorSubsystem),
    }
    source_data = manager.create_source_data(str(source))
    if not source_data:
        raise RuntimeError("Interchange could not create source data")
    report["source_data"] = source_data.get_path_name()
    report["can_translate"] = manager.can_translate_source_data(source_data)
    if not report["can_translate"]:
        raise RuntimeError("No registered Interchange translator accepted this GLB")

    parameters = unreal.ImportAssetParameters()
    report["parameter_members"] = dir(parameters)
    report["parameter_automation_doc"] = type(parameters).is_automated.__doc__
    parameters.set_editor_property("is_automated", True)
    report["is_automated"] = parameters.get_editor_property("is_automated")
    write_report()
    (evidence / "import-api-details.json").write_text(json.dumps(report["api"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    if assets.does_asset_exist(map_path):
        raise FileExistsError(f"Refusing to replace an existing map: {map_path}")
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not levels.new_level(map_path):
        raise RuntimeError("Unreal did not create the requested level")
    report["level_created"] = True
    report["status"] = "IMPORT_REQUESTED"
    write_report()

    result = manager.import_scene(content_path, source_data, parameters)
    report["result_type"] = type(result).__name__
    report["import_scene_succeeded"] = result
    if result is not True:
        raise RuntimeError("Interchange import_scene returned false")
    imported = list(assets.list_assets(content_path, recursive=True))
    report["imported_assets"] = imported
    report["imported_asset_count"] = len(imported)
    if not imported:
        raise RuntimeError("No imported assets were registered in the scene content directory")

    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    report["actor_classes"] = {}
    for actor in actors:
        name = actor.get_class().get_name()
        report["actor_classes"][name] = report["actor_classes"].get(name, 0) + 1
    cameras = [actor for actor in actors if isinstance(actor, unreal.CameraActor)]
    report["author_camera_count"] = len(cameras)
    report["author_cameras"] = [{
        "name": actor.get_name(),
        "location": [actor.get_actor_location().x, actor.get_actor_location().y, actor.get_actor_location().z],
        "rotation": [actor.get_actor_rotation().pitch, actor.get_actor_rotation().yaw, actor.get_actor_rotation().roll],
    } for actor in cameras]
    meshes = [actor for actor in actors if isinstance(actor, unreal.StaticMeshActor)]
    if not meshes:
        raise RuntimeError("No imported StaticMeshActor exists in the actual level")
    report["static_mesh_actor_count"] = len(meshes)
    if not cameras:
        raise RuntimeError("No original scene camera was imported")

    if not assets.save_directory(content_path):
        raise RuntimeError("Unreal did not save the imported asset directory")
    if not levels.save_current_level():
        raise RuntimeError("Unreal did not save the imported level")
    if not assets.does_asset_exist(map_path):
        raise RuntimeError("The saved map asset does not exist")
    report["map_asset_exists"] = True
    report["status"] = "IMPORTED_AND_MAP_SAVED_VISUAL_AND_FLIGHT_NOT_TESTED"
except Exception as error:
    report["status"] = "FAILED"
    report["error"] = str(error)
    report["traceback"] = traceback.format_exc()
    write_report()
    raise

write_report()
print("BUTTERFLY_SCENE_IMPORT_FINISHED", scene_id, report["status"], flush=True)
