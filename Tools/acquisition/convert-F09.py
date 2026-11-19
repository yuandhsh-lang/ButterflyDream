"""Create an isolated F09 engine-conversion copy without changing the source scene."""
import bpy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

args = sys.argv[sys.argv.index("--") + 1:]
destination = Path(args[0]).resolve()
if destination.exists():
    raise FileExistsError(f"Refusing to overwrite existing conversion copy: {destination}")
source = Path(bpy.data.filepath).resolve()
if source == destination:
    raise RuntimeError("Conversion destination must differ from its source")

def file_hash(path):
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

source_sha256 = file_hash(source)
changes = []
sun = bpy.data.objects.get("Sun")
if not sun or sun.type != "LIGHT" or not sun.data.use_nodes:
    raise RuntimeError("Expected F09 Sun light with a node tree")
emission = sun.data.node_tree.nodes.get("Emission")
if not emission:
    raise RuntimeError("Expected F09 Sun emission node")
previous = list(sun.data.color)
converted = list(emission.inputs["Color"].default_value[:3])
sun.data.color = converted
changes.append({
    "object": "Sun",
    "property": "color",
    "from": previous,
    "to": converted,
    "reason": "Use the active emission node color instead of exporting ignored HDR light-color properties",
})

excluded = []
for obj in list(bpy.context.scene.objects):
    if obj.type != "MESH":
        continue
    volume_only = False
    for material in obj.data.materials:
        if not material or not material.use_nodes or not material.node_tree:
            continue
        output = next((node for node in material.node_tree.nodes if node.bl_idname == "ShaderNodeOutputMaterial" and node.is_active_output), None)
        if output and output.inputs["Volume"].is_linked and not output.inputs["Surface"].is_linked:
            volume_only = True
    if volume_only:
        excluded.append({"object": obj.name, "reason": "Volume-only helper; reconstruct as engine volume rather than an opaque GLB surface"})
        for collection in list(obj.users_collection):
            collection.objects.unlink(obj)

destination.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(destination), compress=True, check_existing=False)
report = {
    "scene_id": "F09",
    "created_at": datetime.now(timezone.utc).isoformat(),
    "source_file": str(source),
    "source_sha256": source_sha256,
    "source_saved": False,
    "conversion_copy": str(destination),
    "conversion_copy_sha256": file_hash(destination),
    "conversion_copy_bytes": destination.stat().st_size,
    "changes": changes,
    "excluded_volume_helpers": excluded,
    "remaining_requirements": [
        "Reconstruct water absorption, caustics, and underwater volume treatment in Unreal",
        "Compare snow displacement, transparency, shadows, exposure, and reflections after Unreal import",
        "This conversion is not yet evidence of Unreal import or gameplay"
    ],
    "adaptation_license": "CC BY-SA 4.0",
    "attribution": "White Lands by Oksana Dobrovolska; converted for Butterfly Dream with documented light and volume-helper changes",
    "license_evidence": "Evidence/acquisition/F09-license.json",
}
(destination.parent / "conversion-changes.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("F09_CONVERSION_COPY_COMPLETE", str(destination), flush=True)
