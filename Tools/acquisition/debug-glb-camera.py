"""Compare source and reimported GLB camera transforms and center-ray hits."""
import bpy
from mathutils import Vector
import json
from pathlib import Path
import sys

args = sys.argv[sys.argv.index("--") + 1:]
source_glb = Path(args[0]).resolve()
out = Path(args[1])
source_scene = bpy.context.scene
source_camera = source_scene.camera
roundtrip = bpy.data.scenes.new("GLB_CAMERA_DEBUG")
bpy.context.window.scene = roundtrip
bpy.ops.import_scene.gltf(filepath=str(source_glb))
imported_camera = next(obj for obj in roundtrip.objects if obj.type == "CAMERA")
bpy.context.view_layer.update()

def camera_info(scene, camera):
    bpy.context.window.scene = scene
    bpy.context.view_layer.update()
    direction = camera.matrix_world.to_quaternion() @ Vector((0, 0, -1))
    hit, location, normal, face_index, obj, matrix = scene.ray_cast(bpy.context.evaluated_depsgraph_get(), camera.location, direction)
    return {
        "name": camera.name,
        "location": list(camera.location),
        "matrix_world": [list(row) for row in camera.matrix_world],
        "forward": list(direction),
        "lens": camera.data.lens,
        "clip_start": camera.data.clip_start,
        "clip_end": camera.data.clip_end,
        "center_ray_hit": bool(hit),
        "hit_object": obj.name if obj else None,
        "hit_location": list(location),
        "hit_distance": (location - camera.location).length,
    }

report = {
    "source": camera_info(source_scene, source_camera),
    "imported": camera_info(roundtrip, imported_camera),
    "imported_object_count": len(roundtrip.objects),
    "source_saved": False,
}
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("GLB_CAMERA_DEBUG", out, flush=True)
