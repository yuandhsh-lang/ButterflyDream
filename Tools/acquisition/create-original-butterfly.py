"""Create the project's original butterfly; C++ drives the separate wing pivots in UE."""
import bpy
import math
from array import array
from datetime import datetime, timezone
from hashlib import sha256
import json
from mathutils import Vector
from pathlib import Path

root = Path(__file__).resolve().parents[2]
destination = root / "Assets" / "Original" / "Butterfly"
destination.mkdir(parents=True, exist_ok=True)
for filename in ["Butterfly.blend", "Butterfly.glb"]:
    if (destination / filename).exists():
        raise FileExistsError(f"Refusing to overwrite original asset: {destination / filename}")

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.render.resolution_x = 640
scene.render.resolution_y = 480
scene.render.resolution_percentage = 100
scene.render.threads_mode = "FIXED"
scene.render.threads = 4
scene.view_settings.view_transform = "AgX"
scene.world = bpy.data.worlds.new("Studio World")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.16, 0.19, 0.26, 1)
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.4

size = 512
image = bpy.data.images.new("Butterfly_Wing_BaseColor", width=size, height=size, alpha=True)
pixels = array("f")
for y in range(size):
    v = y / (size - 1)
    for x in range(size):
        u = x / (size - 1)
        angle = math.atan2(v - 0.48, max(0.001, u))
        vein = abs(math.sin(angle * 9.0)) < 0.055 and u > 0.14
        border = u > 0.91 or v < 0.045 or v > 0.955
        gold = 0.855 < u < 0.9 or 0.07 < v < 0.10 or 0.90 < v < 0.93
        radial = min(1.0, math.sqrt(u * u + (v - 0.5) ** 2))
        color = (0.21 + 0.37 * u, 0.09 + 0.24 * u, 0.39 + 0.43 * u, 1.0)
        if vein or border:
            color = (0.025, 0.019, 0.065, 1.0)
        elif gold:
            color = (0.68, 0.43 + 0.15 * radial, 0.28, 1.0)
        pixels.extend(color)
image.pixels.foreach_set(pixels)
image.filepath_raw = str(destination / "Butterfly_Wing_BaseColor.png")
image.file_format = "PNG"
image.save()
image.pack()

wing_material = bpy.data.materials.new("Butterfly_Wing_PBR")
wing_material.use_nodes = True
nodes = wing_material.node_tree.nodes
shader = nodes.get("Principled BSDF")
shader.inputs["Roughness"].default_value = 0.48
shader.inputs["Metallic"].default_value = 0.08
shader.inputs["Subsurface Weight"].default_value = 0.07
texture = nodes.new("ShaderNodeTexImage")
texture.image = image
wing_material.node_tree.links.new(texture.outputs["Color"], shader.inputs["Base Color"])

body_material = bpy.data.materials.new("Butterfly_Body")
body_material.use_nodes = True
body_shader = body_material.node_tree.nodes.get("Principled BSDF")
body_shader.inputs["Base Color"].default_value = (0.025, 0.016, 0.055, 1)
body_shader.inputs["Roughness"].default_value = 0.4


def leaf(name, side, length, height, offset, pivot):
    vertices = []
    faces = []
    rows = 28
    columns = 24
    for row in range(rows + 1):
        u = row / rows
        spread = math.sin(math.pi * u) ** 0.65
        for column in range(columns + 1):
            v = column / columns * 2 - 1
            x = side * (0.014 + length * u)
            y = offset * u + height * v * spread
            z = 0.006 * math.sin(math.pi * u) * math.cos(v * math.pi / 2)
            vertices.append((x, y, z))
    for row in range(rows):
        for column in range(columns):
            a = row * (columns + 1) + column
            face = (a, a + 1, a + columns + 2, a + columns + 1)
            faces.append(face if side > 0 else tuple(reversed(face)))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    uv = mesh.uv_layers.new(name="Wing UV")
    for polygon in mesh.polygons:
        polygon.use_smooth = True
        for loop_index in polygon.loop_indices:
            vertex_index = mesh.loops[loop_index].vertex_index
            uv.data[loop_index].uv = (vertex_index // (columns + 1) / rows, vertex_index % (columns + 1) / columns)
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    obj.parent = pivot
    obj.data.materials.append(wing_material)
    solidify = obj.modifiers.new("Thin wing membrane", "SOLIDIFY")
    solidify.thickness = 0.0004
    return obj


def sphere(name, location, scale, material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def antenna(name, side):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = 0.0015
    curve.bevel_resolution = 3
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(2)
    for point, coordinate in zip(spline.bezier_points, [(side * 0.008, 0.09, 0.014), (side * 0.021, 0.12, 0.024), (side * 0.033, 0.14, 0.025)]):
        point.co = coordinate
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, curve)
    scene.collection.objects.link(obj)
    obj.data.materials.append(body_material)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")


sphere("Butterfly_Body", (0, 0, 0), (0.014, 0.08, 0.014), body_material)
sphere("Butterfly_Thorax", (0, 0.045, 0.003), (0.018, 0.027, 0.017), body_material)
sphere("Butterfly_Head", (0, 0.081, 0.005), (0.017, 0.017, 0.015), body_material)
antenna("Butterfly_Antenna_L", -1)
antenna("Butterfly_Antenna_R", 1)

for side, suffix in [(-1, "L"), (1, "R")]:
    pivot = bpy.data.objects.new(f"WingPivot_{suffix}", None)
    scene.collection.objects.link(pivot)
    pivot.location = (0, 0.038, 0.012)
    pivot.empty_display_size = 0.015
    leaf(f"WingFore_{suffix}", side, 0.19, 0.065, 0.1, pivot)
    leaf(f"WingHind_{suffix}", side, 0.135, 0.054, -0.07, pivot)
    tail = sphere(f"WingTail_{suffix}", (0, 0, 0), (0.003, 0.024, 0.0015), wing_material)
    tail.parent = pivot
    tail.location = (side * 0.103, -0.09, -0.002)
    tail.rotation_euler[2] = side * -0.45

bpy.ops.object.empty_add(type="PLAIN_AXES")
pivot = bpy.context.object
pivot.name = "Butterfly_Root"
for obj in list(scene.objects):
    if obj != pivot and obj.parent is None and obj.type == "MESH":
        obj.parent = pivot

camera_data = bpy.data.cameras.new("Butterfly_Preview_Camera")
camera = bpy.data.objects.new("Butterfly_Preview_Camera", camera_data)
scene.collection.objects.link(camera)
camera.location = (0.48, 0.58, 0.49)
camera.rotation_euler = (Vector((0, 0.025, 0.0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.lens = 52
scene.camera = camera
for name, position, energy, size_value in [
    ("Key", (0.3, 0.1, 0.7), 22, 0.4),
    ("Rim", (-0.4, -0.2, 0.4), 18, 0.3),
]:
    light_data = bpy.data.lights.new(name, "AREA")
    light_data.energy = energy
    light_data.shape = "DISK"
    light_data.size = size_value
    light = bpy.data.objects.new(name, light_data)
    scene.collection.objects.link(light)
    light.location = position
    light.rotation_euler = (Vector((0, 0, 0)) - light.location).to_track_quat("-Z", "Y").to_euler()

for obj in scene.objects:
    if obj.name in {"WingPivot_L", "WingPivot_R"}:
        obj.parent = pivot

bpy.ops.object.select_all(action="DESELECT")
pivot.select_set(True)
for obj in pivot.children_recursive:
    obj.select_set(True)
bpy.context.view_layer.objects.active = pivot
blend_path = destination / "Butterfly.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True)
glb_path = destination / "Butterfly.glb"
bpy.ops.export_scene.gltf(filepath=str(glb_path), export_format="GLB", use_selection=True, export_animations=False, export_apply=True, export_extras=True)
scene.render.filepath = str(root / "Evidence" / "Butterfly" / "original-render.png")
Path(scene.render.filepath).parent.mkdir(parents=True, exist_ok=True)
bpy.ops.render.render(write_still=True)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()

report = {
    "status": "ORIGINAL_ASSET_CREATED_NOT_UNREAL_VERIFIED",
    "created_at": datetime.now(timezone.utc).isoformat(),
    "provenance": "Original procedural geometry and texture authored for this project; not Lux3D generated",
    "blend": {"path": str(blend_path), "bytes": blend_path.stat().st_size, "sha256": digest(blend_path)},
    "glb": {"path": str(glb_path), "bytes": glb_path.stat().st_size, "sha256": digest(glb_path)},
    "wing_pivots": ["WingPivot_L", "WingPivot_R"],
    "animation": "No baked animation; runtime C++ wing rotation requires UE verification",
    "render": str(Path(scene.render.filepath)),
    "render_sha256": digest(Path(scene.render.filepath)),
}
(root / "Evidence" / "Butterfly" / "creation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("ORIGINAL_BUTTERFLY_COMPLETE", str(glb_path), flush=True)
