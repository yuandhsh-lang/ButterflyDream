"""Remove one named GLB node from scene traversal while preserving binary asset data."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
import struct
import sys

source = Path(sys.argv[1]).resolve()
destination = Path(sys.argv[2]).resolve()
node_name = sys.argv[3]
scene_id = sys.argv[4]
if destination.exists():
    raise FileExistsError(f"Refusing to overwrite existing GLB: {destination}")

def digest(path):
    value = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()

source_sha256 = digest(source)
with source.open("rb") as handle:
    magic, version, declared_length = struct.unpack("<III", handle.read(12))
    if magic != 0x46546C67 or version != 2 or declared_length != source.stat().st_size:
        raise ValueError("Invalid GLB header")
    json_length, json_type = struct.unpack("<II", handle.read(8))
    if json_type != 0x4E4F534A:
        raise ValueError("First GLB chunk is not JSON")
    document = json.loads(handle.read(json_length))

matches = [index for index, node in enumerate(document.get("nodes", [])) if node.get("name") == node_name]
if len(matches) != 1:
    raise RuntimeError(f"Expected one node named {node_name}, found {len(matches)}")
node_index = matches[0]
node = document["nodes"][node_index]
removed_references = 0
for scene in document.get("scenes", []):
    before = len(scene.get("nodes", []))
    scene["nodes"] = [index for index in scene.get("nodes", []) if index != node_index]
    removed_references += before - len(scene["nodes"])
for parent in document.get("nodes", []):
    before = len(parent.get("children", []))
    if before:
        parent["children"] = [index for index in parent["children"] if index != node_index]
        removed_references += before - len(parent["children"])
if not removed_references:
    raise RuntimeError("Matched node is not referenced by a scene or parent")
document.setdefault("asset", {}).setdefault("extras", {})["butterflyConversion"] = {
    "scene": scene_id, "removedNode": node_name, "reason": "Volume helper excluded from visible GLB traversal"
}

encoded = json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
encoded += b" " * ((-len(encoded)) % 4)
new_length = 12 + 8 + len(encoded) + (declared_length - (12 + 8 + json_length))
pending = destination.with_suffix(".glb.pending")
with source.open("rb") as input_handle, pending.open("wb") as output_handle:
    input_handle.seek(12 + 8 + json_length)
    output_handle.write(struct.pack("<III", magic, version, new_length))
    output_handle.write(struct.pack("<II", len(encoded), json_type))
    output_handle.write(encoded)
    shutil.copyfileobj(input_handle, output_handle, 8 * 1024 * 1024)
if pending.stat().st_size != new_length:
    raise RuntimeError("Patched GLB length mismatch")
pending.replace(destination)
report = {
    "scene_id": scene_id,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "source_glb": str(source),
    "source_sha256": source_sha256,
    "output": str(destination),
    "actual_bytes": destination.stat().st_size,
    "sha256": digest(destination),
    "removed_node": {"index": node_index, "name": node_name, "mesh": node.get("mesh")},
    "removed_scene_and_parent_references": removed_references,
    "binary_payload_changed": False,
    "textures_reencoded": False,
    "status": "PATCHED_NOT_ENGINE_VERIFIED",
    "engine_import_status": "NOT_TESTED",
    "visual_parity_status": "NOT_TESTED",
}
report_path = destination.with_suffix(".export.json")
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("GLB_NODE_PATCH_COMPLETE", node_name, str(destination), flush=True)
