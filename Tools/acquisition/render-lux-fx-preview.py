import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


args = sys.argv[sys.argv.index('--') + 1:]
if len(args) != 2:
    raise ValueError('Usage: blender --python render-lux-fx-preview.py -- <source.glb> <new-output-directory>')
source = Path(args[0]).resolve()
out = Path(args[1]).resolve()
if out.exists():
    raise FileExistsError(f'Refusing to overwrite preview directory: {out}')
out.mkdir(parents=True)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def point_at(obj, target):
    obj.rotation_euler = (target - obj.location).to_track_quat('-Z', 'Y').to_euler()


def area_light(name, location, energy, color, size, target):
    data = bpy.data.lights.new(name=name, type='AREA')
    data.energy = energy
    data.color = color
    data.shape = 'DISK'
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    point_at(obj, target)


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source))
scene = bpy.context.scene
meshes = [obj for obj in scene.objects if obj.type == 'MESH']
if not meshes:
    raise RuntimeError('Preview source contains no mesh')
points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
low = Vector([min(point[i] for point in points) for i in range(3)])
high = Vector([max(point[i] for point in points) for i in range(3)])
center = (low + high) * 0.5
extent = max(high - low)
if extent <= 0:
    raise RuntimeError('Preview source has empty bounds')

camera_data = bpy.data.cameras.new('FX_PreviewCamera')
camera = bpy.data.objects.new('FX_PreviewCamera', camera_data)
scene.collection.objects.link(camera)
camera.location = center + Vector((extent * 0.65, -extent * 1.35, extent * 0.55))
camera.data.lens = 38
camera.data.clip_end = max(10000, extent * 30)
point_at(camera, center)
scene.camera = camera

world = bpy.data.worlds.new('FX_PreviewWorld')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.035, 0.045, 0.075, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.3
scene.world = world
energy = max(0.05, extent * extent * 20)
area_light('FX_Key', center + Vector((extent * 0.6, -extent * 0.8, extent * 1.4)), energy, (1.0, 0.86, 0.70), extent * 0.7, center)
area_light('FX_Fill', center + Vector((-extent * 0.8, -extent * 0.2, extent * 0.5)), energy * 0.55, (0.48, 0.72, 1.0), extent * 0.6, center)
area_light('FX_Rim', center + Vector((extent * 0.2, extent * 0.9, extent * 0.9)), energy * 0.8, (0.72, 0.88, 1.0), extent * 0.5, center)

scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 16
scene.cycles.use_denoising = True
scene.render.threads_mode = 'FIXED'
scene.render.threads = 4
scene.render.resolution_x = 640
scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = 0
scene.view_settings.gamma = 1
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = str(out / 'fx-preview.png')
bpy.ops.render.render(write_still=True)

triangles = 0
for obj in meshes:
    obj.data.calc_loop_triangles()
    triangles += len(obj.data.loop_triangles)
report = {
    'source': str(source),
    'source_sha256': sha256(source),
    'triangles': triangles,
    'preview': 'fx-preview.png',
    'preview_sha256': sha256(out / 'fx-preview.png'),
    'status': 'RENDERED_REVIEW_REQUIRED',
}
(out / 'fx-preview.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"FX_PREVIEW_RENDERED {out / 'fx-preview.png'}", flush=True)
