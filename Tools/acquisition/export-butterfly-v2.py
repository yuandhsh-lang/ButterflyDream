import bpy
from hashlib import sha256
import json
from pathlib import Path
import struct

root = Path(__file__).resolve().parents[2]
source = Path(bpy.data.filepath).resolve()
expected = (root / "Assets" / "Original" / "Butterfly" / "Butterfly.blend").resolve()
if source != expected:
    raise RuntimeError(f"Expected the preserved butterfly source: {expected}")
base = source.parent
blend_path = base / "Butterfly.v2.blend"
glb_path = base / "Butterfly.v2.glb"
for path in [blend_path, glb_path]:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite: {path}")

root_object = bpy.data.objects["Butterfly_Root"]
for suffix in ["L", "R"]:
    pivot = bpy.data.objects[f"WingPivot_{suffix}"]
    pivot.parent = root_object
    bpy.ops.object.select_all(action="DESELECT")
    parts = [bpy.data.objects[name] for name in [f"WingFore_{suffix}", f"WingHind_{suffix}", f"WingTail_{suffix}"]]
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    wing = bpy.context.object
    wing.name = f"Wing_{suffix}"
    wing.data.name = f"Wing_{suffix}_Mesh"

bpy.ops.object.select_all(action="DESELECT")
parts = [bpy.data.objects[name] for name in ["Butterfly_Body", "Butterfly_Head", "Butterfly_Thorax", "Butterfly_Antenna_L", "Butterfly_Antenna_R"]]
for part in parts:
    part.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
body = bpy.context.object
body.name = "Butterfly_Body"
body.data.name = "Butterfly_Body_Mesh"

bpy.ops.object.select_all(action="DESELECT")
root_object.select_set(True)
for obj in root_object.children_recursive:
    obj.select_set(True)
bpy.context.view_layer.objects.active = root_object
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True)
bpy.ops.export_scene.gltf(filepath=str(glb_path), export_format="GLB", use_selection=True, export_animations=False, export_apply=True, export_extras=True)

with glb_path.open("rb") as handle:
    magic, version, length = struct.unpack("<III", handle.read(12))
    if magic != 0x46546C67 or version != 2 or length != glb_path.stat().st_size:
        raise RuntimeError("Invalid GLB header")
    json_length, chunk_type = struct.unpack("<II", handle.read(8))
    if chunk_type != 0x4E4F534A:
        raise RuntimeError("Missing GLB JSON chunk")
    document = json.loads(handle.read(json_length))
nodes = document.get("nodes", [])
mesh_names = {node["name"] for node in nodes if "mesh" in node}
required_meshes = {"Butterfly_Body", "Wing_L", "Wing_R"}
if not required_meshes.issubset(mesh_names):
    raise RuntimeError(f"Missing meshes: {required_meshes - mesh_names}")
pivot_checks = {}
for suffix in ["L", "R"]:
    pivot_nodes = [node for node in nodes if node.get("name") == f"WingPivot_{suffix}"]
    if len(pivot_nodes) != 1:
        raise RuntimeError(f"Missing unique WingPivot_{suffix}")
    children = pivot_nodes[0].get("children", [])
    child_names = [nodes[index].get("name") for index in children]
    if f"Wing_{suffix}" not in child_names:
        raise RuntimeError(f"Wing_{suffix} is not under its pivot")
    pivot_checks[suffix] = child_names


def digest(path):
    return sha256(path.read_bytes()).hexdigest()

scene = bpy.context.scene
render_path = root / "Evidence" / "Butterfly" / "v2-render.png"
scene.render.filepath = str(render_path)
bpy.ops.render.render(write_still=True)
report = {
    "status": "GLB_HIERARCHY_VERIFIED_NOT_UNREAL_VERIFIED",
    "source_blend": str(source),
    "source_blend_sha256": digest(source),
    "source_saved": False,
    "changes": ["Attach both wing pivots to Butterfly_Root before selection export", "Join each side's forewing, hindwing, and tail into Wing_L/Wing_R", "Join body, head, thorax, and antennae into Butterfly_Body"],
    "blend": {"path": str(blend_path), "bytes": blend_path.stat().st_size, "sha256": digest(blend_path)},
    "glb": {"path": str(glb_path), "bytes": glb_path.stat().st_size, "sha256": digest(glb_path)},
    "mesh_nodes": sorted(mesh_names),
    "wing_pivot_children": pivot_checks,
    "render": str(render_path),
    "render_sha256": digest(render_path),
    "provenance": "Original project asset; no third-party or Lux3D input",
    "unreal_import_status": "NOT_TESTED",
}
(root / "Evidence" / "Butterfly" / "v2-export.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("BUTTERFLY_V2_EXPORT_AND_HIERARCHY_VERIFIED", flush=True)
