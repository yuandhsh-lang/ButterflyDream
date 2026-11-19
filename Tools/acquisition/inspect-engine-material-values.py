import bpy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
source = Path(bpy.data.filepath).resolve()
scene_id = source.parent.name
if scene_id not in {"F06", "F09"} or source.parent.parent.name != "Original":
    raise RuntimeError("Only the preserved F06/F09 source scene is accepted")
output = root / "Evidence" / "Unreal" / scene_id / "material-source-values.json"
output.parent.mkdir(parents=True, exist_ok=True)


def socket_value(socket):
    if not hasattr(socket, "default_value"):
        return None
    value = socket.default_value
    if isinstance(value, (int, float, bool, str)):
        return value
    try:
        return list(value)
    except TypeError:
        return str(value)


def digest(path):
    with path.open("rb") as handle:
        return sha256(handle.read()).hexdigest()

materials = {}
for name in (["water", "snow_01", "snow_02", "white", "Wood"] if scene_id == "F09" else list(bpy.data.materials.keys())):
    material = bpy.data.materials.get(name)
    if not material or not material.use_nodes:
        continue
    nodes = []
    for node in material.node_tree.nodes:
        if node.bl_idname.startswith("ShaderNode"):
            nodes.append({
                "name": node.name,
                "type": node.bl_idname,
                "inputs": {item.name: socket_value(item) for item in node.inputs if socket_value(item) is not None},
            })
    materials[name] = {"nodes": nodes, "links": [{"from": f"{link.from_node.name}:{link.from_socket.name}", "to": f"{link.to_node.name}:{link.to_socket.name}"} for link in material.node_tree.links]}

lights = []
for obj in bpy.context.scene.objects:
    if obj.type != "LIGHT":
        continue
    lights.append({
        "name": obj.name,
        "type": obj.data.type,
        "energy": obj.data.energy,
        "color": list(obj.data.color),
        "location": list(obj.location),
        "rotation_euler": list(obj.rotation_euler),
        "shadow_soft_size": getattr(obj.data, "shadow_soft_size", None),
        "nodes": [{"name": node.name, "type": node.bl_idname, "inputs": {item.name: socket_value(item) for item in node.inputs if socket_value(item) is not None}} for node in obj.data.node_tree.nodes] if obj.data.use_nodes else [],
    })

world_nodes = []
if bpy.context.scene.world and bpy.context.scene.world.use_nodes:
    for node in bpy.context.scene.world.node_tree.nodes:
        world_nodes.append({"name": node.name, "type": node.bl_idname, "inputs": {item.name: socket_value(item) for item in node.inputs if socket_value(item) is not None}})
        if node.bl_idname == "ShaderNodeTexSky":
            world_nodes[-1]["sky_properties"] = {name: str(getattr(node, name)) for name in ["sky_type", "sun_elevation", "sun_rotation", "sun_size", "sun_intensity", "altitude", "air_density", "dust_density", "ozone_density"] if hasattr(node, name)}

report = {
    "scene_id": scene_id,
    "source": str(source),
    "source_sha256": digest(source),
    "source_saved": False,
    "checked_at": datetime.now(timezone.utc).isoformat(),
    "materials": materials,
    "lights": lights,
    "world_nodes": world_nodes,
    "engine_import_status": "NOT_TESTED",
    "note": "Measured Blender source parameters for explicit UE reconstruction, not evidence of engine visual parity",
}
output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("SOURCE_MATERIAL_VALUES_RECORDED", scene_id, str(output), flush=True)
