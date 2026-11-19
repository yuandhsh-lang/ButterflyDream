"""Render a GLB in an otherwise empty Blender scene using explicit baseline settings."""
import bpy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

args = sys.argv[sys.argv.index("--") + 1:]
source_glb = Path(args[0]).resolve()
out = Path(args[1])
config = json.loads(Path(args[2]).read_text(encoding="utf-8"))
out.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
for obj in list(scene.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = config.get("samples", 12)
scene.cycles.use_denoising = True
scene.render.threads_mode = "FIXED"
scene.render.threads = config.get("threads", 4)
scene.render.use_simplify = True
scene.cycles.texture_limit_render = config.get("texture_limit", "512")
scene.render.resolution_x = config.get("width", 512)
scene.render.resolution_y = config.get("height", 512)
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = config["view_transform"]
scene.view_settings.look = config["look"]
scene.view_settings.exposure = config.get("exposure", 0)
scene.view_settings.gamma = config.get("gamma", 1)
world = bpy.data.worlds.new(f"{config['scene_id']}_StandaloneWorld")
world.use_nodes = True
background = world.node_tree.nodes.get("Background")
background.inputs["Color"].default_value = config["world_color"]
background.inputs["Strength"].default_value = config["world_strength"]
scene.world = world
started = datetime.now(timezone.utc)
result = bpy.ops.import_scene.gltf(filepath=str(source_glb))
if "FINISHED" not in result:
    raise RuntimeError(f"GLB import failed: {result}")
cameras = [obj for obj in scene.objects if obj.type == "CAMERA"]
if not cameras:
    raise RuntimeError("GLB has no camera")
scene.camera = cameras[0]
from mathutils import Vector
bounds = [obj.matrix_world @ Vector(corner) for obj in scene.objects if obj.type == "MESH" for corner in obj.bound_box]
bounds_min = [min(point[i] for point in bounds) for i in range(3)]
bounds_max = [max(point[i] for point in bounds) for i in range(3)]
print("GLB_SCENE_BOUNDS", json.dumps({"min": bounds_min, "max": bounds_max}), flush=True)
print("GLB_AUTHOR_CAMERA", json.dumps({"location": list(scene.camera.location), "matrix_world": [list(row) for row in scene.camera.matrix_world]}), flush=True)
if config.get("camera_mode") == "overview":
    center = Vector([(low + high) / 2 for low, high in zip(bounds_min, bounds_max)])
    extent = max(high - low for low, high in zip(bounds_min, bounds_max))
    camera_data = bpy.data.cameras.new("DiagnosticOverview")
    camera = bpy.data.objects.new("DiagnosticOverview", camera_data)
    scene.objects.link(camera)
    camera.location = center + Vector((extent * 0.6, -extent * 1.2, extent * 0.5))
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.clip_end = max(10000, extent * 20)
    camera.data.lens = 28
    scene.camera = camera
    print("GLB_OVERVIEW_CAMERA", json.dumps({"location": list(camera.location), "target": list(center)}), flush=True)
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(out / "glb-standalone.png")
bpy.ops.render.render(write_still=True)
finished = datetime.now(timezone.utc)
content = (out / "glb-standalone.png").read_bytes()
report = {
    "scene_id": config["scene_id"],
    "source_glb": str(source_glb),
    "source_glb_sha256": sha256(source_glb.read_bytes()).hexdigest(),
    "render": "glb-standalone.png",
    "render_sha256": sha256(content).hexdigest(),
    "render_bytes": len(content),
    "started_at": started.isoformat(),
    "finished_at": finished.isoformat(),
    "render_seconds": (finished - started).total_seconds(),
    "imported_objects": len(scene.objects),
    "imported_meshes": len([obj for obj in scene.objects if obj.type == "MESH"]),
    "imported_lights": len([obj for obj in scene.objects if obj.type == "LIGHT"]),
    "imported_cameras": len(cameras),
    "imported_camera": scene.camera.name,
    "world": config,
    "status": "STANDALONE_GLB_RENDERED",
    "unreal_import_status": "NOT_TESTED",
    "visual_parity_status": "REVIEW_REQUIRED",
}
(out / "glb-standalone.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("STANDALONE_GLB_RENDER_COMPLETE", str(out / "glb-standalone.png"), flush=True)
