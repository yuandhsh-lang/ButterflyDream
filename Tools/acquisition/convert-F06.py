"""Create an isolated F06 conversion copy without exporting volume helpers as surfaces."""
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
        excluded.append({"object": obj.name, "reason": "Volume-only helper; reconstruct fog in Unreal instead of rendering a default GLB surface"})
        for collection in list(obj.users_collection):
            collection.objects.unlink(obj)
if not excluded:
    raise RuntimeError("No volume-only helpers found; inspect the scene instead of producing an unchanged copy")

destination.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(destination), compress=True, check_existing=False)
report = {
    "scene_id": "F06",
    "created_at": datetime.now(timezone.utc).isoformat(),
    "source_file": str(source),
    "source_sha256": source_sha256,
    "source_saved": False,
    "conversion_copy": str(destination),
    "conversion_copy_sha256": file_hash(destination),
    "conversion_copy_bytes": destination.stat().st_size,
    "excluded_volume_helpers": excluded,
    "remaining_requirements": [
        "Rebuild fog, compositor glow, streaks, sharpening, and lens dispersion in Unreal",
        "Verify particle grass, linked tree instances, transparency, shadows, and author-camera parity after import",
        "Use shared mesh instances rather than assuming every GLB node needs a unique runtime mesh",
        "This conversion is not yet evidence of Unreal import or gameplay"
    ],
    "license": "Blendkit Royalty Free",
    "license_evidence": "Evidence/acquisition/F06-license.json",
}
(destination.parent / "conversion-changes.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("F06_CONVERSION_COPY_COMPLETE", str(destination), flush=True)
