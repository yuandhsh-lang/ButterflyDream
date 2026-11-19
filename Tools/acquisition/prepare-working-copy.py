"""Save a minimal working copy with explicit library relinks; never overwrite the source."""
import bpy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

args = sys.argv[sys.argv.index("--") + 1:]
destination = Path(args[0]).resolve()
config = json.loads(Path(args[1]).read_text(encoding="utf-8"))
source = Path(bpy.data.filepath).resolve()
if destination == source:
    raise RuntimeError("Working copy must differ from the source file")
if destination.exists():
    raise FileExistsError(f"Refusing to overwrite existing working copy: {destination}")

def file_hash(path):
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

source_hash = file_hash(source)
if source_hash != config["source_sha256"]:
    raise RuntimeError("Source SHA256 does not match the working-copy configuration")

relinks = []
for old_suffix, new_path in config.get("library_relinks", {}).items():
    if not Path(new_path).is_file():
        raise FileNotFoundError(new_path)
    for library in bpy.data.libraries:
        if library.name.startswith(old_suffix):
            previous = library.filepath
            library.filepath = new_path
            relinks.append({"name": library.name, "from": previous, "to": new_path})

destination.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(destination), compress=True, check_existing=False)
report = {
    "scene_id": config["scene_id"],
    "created_at": datetime.now(timezone.utc).isoformat(),
    "source_file": str(source),
    "source_sha256": source_hash,
    "source_saved": False,
    "working_copy": str(destination),
    "working_copy_bytes": destination.stat().st_size,
    "working_copy_sha256": file_hash(destination),
    "blender_version": bpy.app.version_string,
    "library_relinks": relinks,
    "changes": "Working-copy save and listed library relinks only; no intentional geometry, material, lighting, camera, or render-setting edits",
}
report_path = destination.parent / "working-copy.json"
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("WORKING_COPY_COMPLETE", str(destination), flush=True)
