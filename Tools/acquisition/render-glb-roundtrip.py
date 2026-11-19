"""Reimport a GLB beside its source working copy and render a technical comparison."""
import bpy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

args = sys.argv[sys.argv.index("--") + 1:]
source_glb = Path(args[0]).resolve()
out = Path(args[1])
scene_id = args[2]
out.mkdir(parents=True, exist_ok=True)
source_scene = bpy.context.scene
source_camera = source_scene.camera
roundtrip = bpy.data.scenes.new(f"{scene_id}_GLB_ROUNDTRIP")
bpy.context.window.scene = roundtrip
roundtrip.world = source_scene.world
roundtrip.view_settings.view_transform = source_scene.view_settings.view_transform
roundtrip.view_settings.look = source_scene.view_settings.look
roundtrip.view_settings.exposure = source_scene.view_settings.exposure
roundtrip.view_settings.gamma = source_scene.view_settings.gamma
scale = 512 / max(source_scene.render.resolution_x, source_scene.render.resolution_y)
roundtrip.render.resolution_x = max(8, round(source_scene.render.resolution_x * scale))
roundtrip.render.resolution_y = max(8, round(source_scene.render.resolution_y * scale))
roundtrip.render.resolution_percentage = 100
roundtrip.render.engine = "CYCLES"
roundtrip.cycles.device = "CPU"
roundtrip.cycles.samples = 16
roundtrip.cycles.use_denoising = True
roundtrip.render.use_simplify = True
roundtrip.cycles.texture_limit_render = "1024"
started = datetime.now(timezone.utc)
result = bpy.ops.import_scene.gltf(filepath=str(source_glb))
if "FINISHED" not in result:
    raise RuntimeError(f"GLB import failed: {result}")
cameras = [obj for obj in roundtrip.objects if obj.type == "CAMERA"]
if not cameras:
    raise RuntimeError("The converted scene has no imported camera")
roundtrip.camera = cameras[0]
roundtrip.render.image_settings.file_format = "PNG"
roundtrip.render.filepath = str(out / "glb-roundtrip.png")
bpy.ops.render.render(write_still=True)
finished = datetime.now(timezone.utc)
content = (out / "glb-roundtrip.png").read_bytes()
report = {
    "scene_id": scene_id,
    "source_blend": bpy.data.filepath,
    "source_glb": str(source_glb),
    "source_glb_sha256": sha256(source_glb.read_bytes()).hexdigest(),
    "source_blend_saved": False,
    "render": "glb-roundtrip.png",
    "render_sha256": sha256(content).hexdigest(),
    "render_bytes": len(content),
    "started_at": started.isoformat(),
    "finished_at": finished.isoformat(),
    "render_seconds": (finished - started).total_seconds(),
    "imported_objects": len(roundtrip.objects),
    "imported_meshes": len([obj for obj in roundtrip.objects if obj.type == "MESH"]),
    "imported_lights": len([obj for obj in roundtrip.objects if obj.type == "LIGHT"]),
    "imported_cameras": len(cameras),
    "imported_camera": roundtrip.camera.name,
    "source_camera": source_camera.name if source_camera else None,
    "world_reused_from_source": roundtrip.world.name if roundtrip.world else None,
    "status": "BLENDER_ROUNDTRIP_RENDERED",
    "unreal_import_status": "NOT_TESTED",
    "visual_parity_status": "REVIEW_REQUIRED",
}
(out / "glb-roundtrip.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("GLB_ROUNDTRIP_RENDER_COMPLETE", scene_id, str(out / "glb-roundtrip.png"), flush=True)
