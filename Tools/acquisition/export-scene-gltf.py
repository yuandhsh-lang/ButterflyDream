"""Export the active Blender scene to GLB and record unverified engine-facing limitations."""
import bpy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

args = sys.argv[sys.argv.index("--") + 1:]
destination = Path(args[0]).resolve()
scene_id = args[1]
if destination.suffix.lower() != ".glb":
    raise ValueError("Destination must use the .glb extension")
if destination.exists():
    raise FileExistsError(f"Refusing to overwrite existing conversion: {destination}")
source = Path(bpy.data.filepath).resolve()

def file_hash(path):
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

source_sha256 = file_hash(source)
scene = bpy.context.scene
materials = [{"name": material.name,
              "node_types": sorted({node.bl_idname for node in material.node_tree.nodes}) if material.use_nodes and material.node_tree else []}
             for material in bpy.data.materials]
destination.parent.mkdir(parents=True, exist_ok=True)
started = datetime.now(timezone.utc)
settings = {
    "filepath": str(destination),
    "export_format": "GLB",
    "export_texcoords": True,
    "export_normals": True,
    "export_materials": "EXPORT",
    "export_cameras": True,
    "export_lights": True,
    "export_extras": True,
    "export_apply": True,
    "export_animations": False,
    "export_image_format": "AUTO",
    "export_yup": True,
    "use_active_scene": True,
}
result = bpy.ops.export_scene.gltf(**settings)
if "FINISHED" not in result or not destination.is_file():
    raise RuntimeError(f"glTF export did not produce a GLB: {result}")
finished = datetime.now(timezone.utc)
report = {
    "scene_id": scene_id,
    "source_file": str(source),
    "source_sha256": source_sha256,
    "source_saved": False,
    "output": str(destination),
    "actual_bytes": destination.stat().st_size,
    "sha256": file_hash(destination),
    "started_at": started.isoformat(),
    "finished_at": finished.isoformat(),
    "export_seconds": (finished - started).total_seconds(),
    "blender_version": bpy.app.version_string,
    "settings": {key: value for key, value in settings.items() if key != "filepath"},
    "materials": materials,
    "status": "EXPORTED_NOT_ENGINE_VERIFIED",
    "engine_import_status": "NOT_TESTED",
    "visual_parity_status": "NOT_TESTED",
    "limitations": [
        "GLB structure and material conversion require separate validation",
        "Blender world, Cycles lighting, caustics, compositor effects, and procedural shaders may require Unreal reconstruction",
        "Export does not prove Unreal import, collision, flight, scene switching, or runtime resource release"
    ],
}
report_path = destination.with_suffix(".export.json")
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("SCENE_GLB_EXPORT_COMPLETE", scene_id, str(destination), flush=True)
