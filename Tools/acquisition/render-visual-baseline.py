"""Render fixed technical-baseline views without saving the opened .blend."""
import bpy
from datetime import datetime, timezone
from hashlib import sha256
import json
from mathutils import Vector
from pathlib import Path
import sys

args = sys.argv[sys.argv.index("--") + 1:]
out = Path(args[0])
config = json.loads(Path(args[1]).read_text(encoding="utf-8"))
out.mkdir(parents=True, exist_ok=True)
source = Path(bpy.data.filepath)
source_hash = sha256()
with source.open("rb") as handle:
    for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
        source_hash.update(block)
if source_hash.hexdigest() != config["source_sha256"]:
    raise RuntimeError("Source SHA256 does not match the baseline configuration")

scene = bpy.context.scene
original = {
    "file": str(source),
    "source_sha256": source_hash.hexdigest(),
    "camera": scene.camera.name if scene.camera else None,
    "engine": scene.render.engine,
    "resolution": [scene.render.resolution_x, scene.render.resolution_y],
    "resolution_percentage": scene.render.resolution_percentage,
    "samples": scene.cycles.samples,
    "device": scene.cycles.device,
    "exposure": scene.view_settings.exposure,
    "gamma": scene.view_settings.gamma,
    "look": scene.view_settings.look,
    "view_transform": scene.view_settings.view_transform,
}
report = {
    "scene_id": config["scene_id"],
    "original_settings": original,
    "source_saved": False,
    "preview_only": True,
    "visual_baseline_status": "TECHNICAL_PREVIEW_REVIEW_REQUIRED",
    "views": [],
}

try:
    library_relinks = []
    for old_suffix, new_path in config.get("library_relinks", {}).items():
        for library in bpy.data.libraries:
            if library.name.startswith(old_suffix):
                previous = library.filepath
                library.filepath = new_path
                library_relinks.append({"name": library.name, "from": previous, "to": new_path})
    report["temporary_library_relinks"] = library_relinks

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = config.get("samples", 16)
    scene.cycles.use_denoising = True
    scene.cycles.use_adaptive_sampling = True
    scene.render.resolution_x = config.get("width", 640)
    scene.render.resolution_y = config.get("height", 640)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.use_simplify = True
    scene.render.simplify_subdivision_render = config.get("subdivision_render", 0)
    scene.cycles.texture_limit_render = config.get("texture_limit", "1024")
    scene.render.threads_mode = "FIXED"
    scene.render.threads = config.get("threads", 8)
    report["temporary_overrides"] = {
        "engine": scene.render.engine,
        "device": scene.cycles.device,
        "samples": scene.cycles.samples,
        "denoising": scene.cycles.use_denoising,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "subdivision_render": scene.render.simplify_subdivision_render,
        "texture_limit_render": scene.cycles.texture_limit_render,
        "threads": scene.render.threads,
    }

    for view in config["views"]:
        started = datetime.now(timezone.utc)
        temporary_camera = None
        try:
            if "source_camera" in view:
                camera = bpy.data.objects[view["source_camera"]]
            else:
                camera_data = bpy.data.cameras.new(f"Baseline_{view['name']}")
                temporary_camera = bpy.data.objects.new(camera_data.name, camera_data)
                scene.collection.objects.link(temporary_camera)
                camera = temporary_camera
                camera.location = Vector(view["location"])
                camera.rotation_euler = (Vector(view["target"]) - camera.location).to_track_quat("-Z", "Y").to_euler()
                camera.data.lens = view.get("lens", 35)
                camera.data.clip_start = view.get("clip_start", 0.05)
                camera.data.clip_end = view.get("clip_end", 10000)
            scene.camera = camera
            destination = out / f"{view['name']}.png"
            scene.render.filepath = str(destination)
            bpy.ops.render.render(write_still=True)
            finished = datetime.now(timezone.utc)
            content = destination.read_bytes()
            report["views"].append({
                "name": view["name"],
                "purpose": view["purpose"],
                "camera": camera.name,
                "location": list(camera.location),
                "rotation_euler": list(camera.rotation_euler),
                "lens": camera.data.lens,
                "file": destination.name,
                "bytes": len(content),
                "sha256": sha256(content).hexdigest(),
                "started_at": started.isoformat(),
                "finished_at": finished.isoformat(),
                "render_seconds": (finished - started).total_seconds(),
                "status": "RENDERED",
            })
            (out / "visual-baseline.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print("BASELINE_VIEW_COMPLETE", config["scene_id"], view["name"], str(destination), flush=True)
        except Exception as error:
            report["views"].append({"name": view["name"], "status": "FAILED", "error": str(error)})
            raise
        finally:
            if temporary_camera:
                camera_data = temporary_camera.data
                bpy.data.objects.remove(temporary_camera, do_unlink=True)
                bpy.data.cameras.remove(camera_data)
finally:
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    (out / "visual-baseline.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print("VISUAL_BASELINE_RENDER_COMPLETE", config["scene_id"], str(out), flush=True)
