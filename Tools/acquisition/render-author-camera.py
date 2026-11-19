"""Render a technical preview from the source camera; never save the .blend."""
import bpy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

args = sys.argv[sys.argv.index("--") + 1:]
out = Path(args[0])
out.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
assert scene.camera, "The author did not provide an active camera"
original = {"file": bpy.data.filepath, "camera": scene.camera.name, "engine": scene.render.engine,
            "resolution": [scene.render.resolution_x, scene.render.resolution_y],
            "resolution_percentage": scene.render.resolution_percentage,
            "samples": scene.cycles.samples, "device": scene.cycles.device,
            "exposure": scene.view_settings.exposure, "gamma": scene.view_settings.gamma,
            "look": scene.view_settings.look, "view_transform": scene.view_settings.view_transform}
texture_limit = "1024" if "--limit-textures" in args else "OFF"
if texture_limit != "OFF":
    original["use_simplify"] = scene.render.use_simplify
    original["texture_limit_render"] = scene.cycles.texture_limit_render
    scene.render.use_simplify = True
    scene.cycles.texture_limit_render = texture_limit
scale = 512 / max(scene.render.resolution_x, scene.render.resolution_y)
scene.render.resolution_x = max(8, round(scene.render.resolution_x * scale))
scene.render.resolution_y = max(8, round(scene.render.resolution_y * scale))
scene.render.resolution_percentage = 100
scene.cycles.samples = 16
scene.cycles.device = "CPU"
scene.cycles.use_denoising = True
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(out / "author-camera-technical-preview.png")
started = datetime.now(timezone.utc)
bpy.ops.render.render(write_still=True)
finished = datetime.now(timezone.utc)
libraries = [{"name": x.name, "filepath": x.filepath, "packed": bool(getattr(x, "packed_file", None)),
              "is_missing": bool(getattr(x, "is_missing", False))} for x in bpy.data.libraries]
report = {"original_settings": original, "temporary_overrides": {"samples": 16, "device": "CPU",
          "resolution": [scene.render.resolution_x, scene.render.resolution_y], "denoising": True,
          "texture_limit_render": texture_limit},
          "started_at": started.isoformat(), "finished_at": finished.isoformat(),
          "render_seconds": (finished-started).total_seconds(), "source_saved": False,
          "preview_only": True, "visual_baseline_passed": False, "libraries": libraries}
(out / "author-camera-render.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("AUTHOR_CAMERA_PREVIEW_COMPLETE", str(out / "author-camera-technical-preview.png"))
