import hashlib
import json
from pathlib import Path
import traceback
import unreal

root = Path(__file__).resolve().parents[2]
evidence = root / "Evidence" / "Unreal" / "F06"
evidence.mkdir(parents=True, exist_ok=True)
map_path = "/Game/Maps/F06_SakuraDream"
batches = [
    ("01-stairs", "03-stairs.glb", "5b007bc60bacd35ce98b7fe777efaa6da23ba4ebb75e277c2607a5de1db9aed0"),
    ("02-foliage", "01-foliage.glb", "700da1d35e0831476c66ddaf5da3ad60527db3eed4f63924adb9f1971e08d245"),
    ("03-pagoda", "02-pagoda.glb", "2f21d558a6a01f289c90cacfbca70de9b39c428c9d6a928988f68fe532843fc2"),
    ("04-main", "04-main.glb", "01b8197f5c6eea4f1c9cc00441cd5bfbac4fe03c621a87885e4ee403272593fe"),
]
report = {
    "scene_id": "F06",
    "map_path": map_path,
    "source_batch_report": "Evidence/Blender/F06/BatchedV2/split-F06-import-report.json",
    "status": "PREPARING_EMPTY_MAP",
    "visual_parity_status": "NOT_TESTED",
    "flight_status": "NOT_TESTED",
    "batches": [],
}


def save_report():
    (evidence / "batch-import-result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def actors_snapshot():
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    return {
        "count": len(actors),
        "mesh_component_count": sum(actor.get_component_by_class(unreal.StaticMeshComponent) is not None for actor in actors),
        "camera_count": sum(isinstance(actor, unreal.CameraActor) for actor in actors),
        "labels": [actor.get_actor_label() for actor in actors if actor.get_component_by_class(unreal.StaticMeshComponent) or isinstance(actor, unreal.CameraActor)],
    }


try:
    manager = unreal.InterchangeManager.get_interchange_manager_scripted()
    assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if assets.does_asset_exist(map_path):
        if not levels.load_level(map_path):
            raise RuntimeError("Could not load the existing F06 map")
        actors = unreal.EditorLevelLibrary.get_all_level_actors()
        non_empty = [actor.get_actor_label() for actor in actors if actor.get_component_by_class(unreal.StaticMeshComponent) or isinstance(actor, unreal.CameraActor)]
        if non_empty:
            raise RuntimeError(f"Refusing to reuse a nonempty F06 map: {non_empty[:10]}")
        report["reused_existing_empty_map"] = True
    elif not levels.new_level(map_path):
        raise RuntimeError("Could not create the F06 map")

    for name, filename, expected_hash in batches:
        source = root / "SourceScenes" / "Working" / "F06" / "BatchedV2" / filename
        if not source.is_file():
            raise FileNotFoundError(source)
        with source.open("rb") as handle:
            actual_hash = hashlib.file_digest(handle, "sha256").hexdigest()
        if actual_hash != expected_hash:
            raise RuntimeError(f"Unexpected batch hash: {source}")
        source_data = manager.create_source_data(str(source))
        if not manager.can_translate_source_data(source_data):
            raise RuntimeError(f"No Interchange translator for {source}")
        parameters = unreal.ImportAssetParameters()
        parameters.set_editor_property("is_automated", True)
        destination = f"/Game/ThirdParty/F06/{name}"
        entry = {
            "name": name,
            "source": str(source),
            "sha256": actual_hash,
            "destination": destination,
            "status": "REQUESTED",
        }
        report["batches"].append(entry)
        report["status"] = f"IMPORTING_{name}"
        save_report()
        succeeded = manager.import_scene(destination, source_data, parameters)
        entry["import_scene_return"] = succeeded
        if not succeeded:
            raise RuntimeError(f"Interchange returned false for {name}")
        entry["saved_assets"] = list(assets.list_assets(destination, recursive=True))
        if not entry["saved_assets"]:
            raise RuntimeError(f"No imported assets for {name}")
        if not assets.save_directory(destination):
            raise RuntimeError(f"Could not save batch {name}")
        entry["actors_after"] = actors_snapshot()
        entry["status"] = "IMPORTED_AND_SAVED"
        save_report()
        unreal.SystemLibrary.collect_garbage()

    lights_changed = 0
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        if isinstance(actor, unreal.PointLight):
            component = actor.get_component_by_class(unreal.PointLightComponent)
            component.set_editor_property("use_temperature", True)
            component.set_editor_property("temperature", 3000.0)
            lights_changed += 1
    report["point_lights_temperature_restored"] = lights_changed
    if not assets.save_directory("/Game/ThirdParty/F06"):
        raise RuntimeError("Could not save the full F06 asset directory")
    if not levels.save_current_level():
        raise RuntimeError("Could not save the combined F06 map")
    if not assets.does_asset_exist(map_path):
        raise RuntimeError("F06 map asset is missing after save")
    report["final_scene"] = actors_snapshot()
    report["status"] = "FOUR_BATCHES_IMPORTED_AND_MAP_SAVED_VISUAL_AND_FLIGHT_NOT_TESTED"
except Exception as error:
    report["status"] = "FAILED"
    report["error"] = str(error)
    report["traceback"] = traceback.format_exc()
    save_report()
    raise

save_report()
print("BUTTERFLY_F06_BATCH_IMPORT_FINISHED", report["status"], flush=True)
