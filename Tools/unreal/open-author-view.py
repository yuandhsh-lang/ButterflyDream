import hashlib
import json
import os
from pathlib import Path
import time
import traceback
import unreal


def _resolve_paths(scene_id: str):
    map_path = {"F09": "/Game/Maps/F09_Unawakened", "F06": "/Game/Maps/F06_SakuraDream"}.get(scene_id)
    if not map_path:
        raise ValueError(f"Unsupported scene: {scene_id}")
    root = Path(__file__).resolve().parents[2]
    evidence = root / "Evidence" / "Unreal" / scene_id
    evidence.mkdir(parents=True, exist_ok=True)
    return root, map_path, evidence


def prepare_author_view(scene_id: str):
    root, map_path, evidence = _resolve_paths(scene_id)
    assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    if not assets.does_asset_exist(map_path):
        raise FileNotFoundError(f"Saved scene does not exist: {map_path}")

    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    editor_sub = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    current_world = editor_sub.get_editor_world() if editor_sub else None
    current_path = current_world.get_path_name() if current_world else ""
    expected_world_prefix = map_path + "."
    if not current_path.startswith(expected_world_prefix):
        if not levels.load_level(map_path):
            raise RuntimeError(f"Could not load actual scene map: {map_path}")

    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    cameras = [actor for actor in actors if isinstance(actor, unreal.CameraActor)]
    if not cameras:
        raise RuntimeError("No imported author camera exists")
    camera = cameras[0]
    component = camera.get_component_by_class(unreal.CameraComponent)
    levels.pilot_level_actor(camera)
    levels.editor_set_game_view(True)
    if hasattr(levels, "editor_set_viewport_realtime"):
        levels.editor_set_viewport_realtime(True)
    levels.editor_invalidate_viewports()

    world = editor_sub.get_editor_world() if editor_sub else camera.get_world()
    location = camera.get_actor_location()
    rotation = camera.get_actor_rotation()
    report = {
        "scene_id": scene_id,
        "map_path": map_path,
        "world": world.get_path_name() if world else map_path,
        "camera": camera.get_name(),
        "location": [location.x, location.y, location.z],
        "rotation": [rotation.pitch, rotation.yaw, rotation.roll],
        "camera_fov": component.get_editor_property("field_of_view") if component else None,
        "actor_count": len(actors),
        "status": "SAVED_SCENE_REOPENED_AUTHOR_VIEW_READY_NOT_FLIGHT_VERIFIED",
        "visual_parity_status": "NOT_TESTED",
    }
    report["actor_classes"] = {}
    for actor in actors:
        name = actor.get_class().get_name()
        report["actor_classes"][name] = report["actor_classes"].get(name, 0) + 1
    report["meshes"] = []
    report["lights"] = []
    for actor in actors:
        mesh_component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if mesh_component:
            mesh = mesh_component.get_editor_property("static_mesh")
            body_setup = mesh.get_editor_property("body_setup") if mesh else None
            report["meshes"].append({
                "actor": actor.get_name(),
                "mesh": mesh.get_path_name() if mesh else None,
                "collision_enabled": str(mesh_component.get_collision_enabled()),
                "collision_trace_flag": str(body_setup.get_editor_property("collision_trace_flag")) if body_setup else None,
                "materials": [str(material.get_path_name()) if material else None for material in list(mesh_component.get_editor_property("override_materials"))],
            })
        if isinstance(actor, unreal.Light):
            light_component = actor.get_component_by_class(unreal.LightComponent)
            if light_component:
                color = light_component.get_light_color()
                report["lights"].append({
                    "actor": actor.get_name(),
                    "class": actor.get_class().get_name(),
                    "intensity": light_component.get_editor_property("intensity"),
                    "color": [color.r, color.g, color.b, color.a],
                    "use_temperature": light_component.get_editor_property("use_temperature"),
                    "temperature": light_component.get_editor_property("temperature"),
                })
    map_file = Path(unreal.Paths.project_content_dir()) / "Maps" / (map_path.rsplit("/", 1)[-1] + ".umap")
    with map_file.open("rb") as handle:
        report["map_sha256"] = hashlib.file_digest(handle, "sha256").hexdigest()
    report["map_bytes"] = map_file.stat().st_size
    return report, camera, evidence


def start_interactive_session(scene_id: str):
    _, map_path, evidence = _resolve_paths(scene_id)
    error_file = evidence / "author-view-error.txt"
    ready_file = evidence / "author-view-ready.json"
    complete_file = evidence / "capture-complete.json"
    viewport_shot = evidence / "author-ue.png"
    for p in (error_file, ready_file, viewport_shot):
        if p.exists():
            p.unlink()

    state = {
        "phase": "WAIT_STARTUP",
        "start_time": time.monotonic(),
        "ticks": 0,
        "report": None,
        "camera": None,
        "shot_task": None,
        "shot_time": None,
        "quitting": False,
    }

    def on_tick(delta_seconds):
        if state["quitting"]:
            return
        state["ticks"] += 1
        try:
            if state["phase"] == "WAIT_STARTUP":
                if state["ticks"] < 20 or (time.monotonic() - state["start_time"]) < 4.0:
                    return
                report, camera, _ = prepare_author_view(scene_id)
                state["report"] = report
                state["camera"] = camera
                state["phase"] = "WARMUP_RENDER"
                state["warmup_start"] = time.monotonic()
                state["warmup_ticks"] = 0
                return

            if state["phase"] == "WARMUP_RENDER":
                state["warmup_ticks"] += 1
                levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
                levels.editor_invalidate_viewports()
                if state["warmup_ticks"] < 60 or (time.monotonic() - state["warmup_start"]) < 15.0:
                    return
                if hasattr(unreal, "AutomationLibrary") and hasattr(unreal.AutomationLibrary, "take_high_res_screenshot"):
                    try:
                        state["shot_task"] = unreal.AutomationLibrary.take_high_res_screenshot(
                            1920,
                            1080,
                            str(viewport_shot),
                            camera=state["camera"],
                            delay=0.5,
                            force_game_view=True,
                        )
                    except Exception:
                        error_file.write_text(traceback.format_exc(), encoding="utf-8")
                state["shot_time"] = time.monotonic()
                state["phase"] = "WAIT_SHOT"
                return

            if state["phase"] == "WAIT_SHOT":
                if not viewport_shot.is_file() and (time.monotonic() - state["shot_time"]) < 8.0:
                    return
                if viewport_shot.is_file():
                    state["report"]["native_viewport_screenshot"] = str(viewport_shot)
                    state["report"]["native_viewport_screenshot_bytes"] = viewport_shot.stat().st_size
                ready_file.write_text(json.dumps(state["report"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print("BUTTERFLY_AUTHOR_VIEW_READY", scene_id, flush=True)
                state["phase"] = "WAIT_CAPTURE_COMPLETE"
                return

            if state["phase"] == "WAIT_CAPTURE_COMPLETE":
                if complete_file.is_file():
                    state["quitting"] = True
                    unreal.SystemLibrary.quit_editor()
        except Exception:
            error_file.write_text(traceback.format_exc(), encoding="utf-8")
            state["quitting"] = True
            unreal.SystemLibrary.quit_editor()

    if hasattr(unreal, "register_slate_post_tick_callback"):
        unreal.register_slate_post_tick_callback(on_tick)
    else:
        report, _, _ = prepare_author_view(scene_id)
        ready_file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    scene_id = os.environ.get("BUTTERFLY_SCENE_ID", "F09")
    report, _, evidence = prepare_author_view(scene_id)
    (evidence / "author-view-ready.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("BUTTERFLY_AUTHOR_VIEW_READY", scene_id, flush=True)

    if hasattr(unreal, "register_slate_post_tick_callback"):
        def close_after_capture(delta_seconds):
            if (evidence / "capture-complete.json").is_file():
                unreal.SystemLibrary.quit_editor()
        unreal.register_slate_post_tick_callback(close_after_capture)
