"""Read the opened .blend without saving it or running embedded scripts."""
import bpy
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

args = sys.argv[sys.argv.index("--") + 1:]
out = Path(args[0])
out.mkdir(parents=True, exist_ok=True)
decode_images = "--decode-images" in args


def image_info(image):
    packed = bool(image.packed_file or len(image.packed_files))
    absolute = bpy.path.abspath(image.filepath, library=image.library) if image.filepath else ""
    required = image.source in {"FILE", "SEQUENCE", "MOVIE", "TILED"}
    return {"name": image.name, "source": image.source, "filepath": image.filepath,
            "resolved_path": absolute, "packed": packed,
            "packed_count": len(image.packed_files),
            "packed_byte_count": getattr(image.packed_file, "size", None) if image.packed_file else None,
            "missing": bool(required and not packed and (not absolute or not Path(absolute).is_file())),
            "size": list(image.size) if decode_images else None,
            "size_status": "READ_WITH_IMAGE_DECODE" if decode_images else "NOT_READ_NO_IMAGE_DECODE",
            "colorspace": image.colorspace_settings.name}


images = [image_info(x) for x in bpy.data.images]
libraries = [{"name": x.name, "filepath": x.filepath,
              "exists": Path(bpy.path.abspath(x.filepath)).is_file(),
              "packed": bool(getattr(x, "packed_file", None)),
              "is_missing": bool(getattr(x, "is_missing", False))} for x in bpy.data.libraries]
for library in libraries:
    library["missing"] = bool(library["is_missing"] or (not library["exists"] and not library["packed"]))
modifiers = [{"object": obj.name, "name": mod.name, "type": mod.type,
              "node_group": mod.node_group.name if mod.type == "NODES" and mod.node_group else None,
              "show_render": mod.show_render, "show_viewport": mod.show_viewport}
             for obj in bpy.data.objects for mod in obj.modifiers]
def socket_value(socket):
    value = getattr(socket, "default_value", None)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    try:
        return list(value)
    except TypeError:
        return str(value)


def node_tree_info(tree):
    if not tree:
        return None
    return {"name": tree.name, "nodes": [{"name": n.name, "type": n.bl_idname,
            "inputs": {s.name: socket_value(s) for s in n.inputs if hasattr(s, "default_value")}}
            for n in tree.nodes],
            "links": [{"from": f"{link.from_node.name}:{link.from_socket.name}",
                       "to": f"{link.to_node.name}:{link.to_socket.name}"} for link in tree.links]}


cameras = [{"name": obj.name, "location": list(obj.location), "rotation_euler": list(obj.rotation_euler),
            "matrix_world": [list(row) for row in obj.matrix_world], "lens": obj.data.lens,
            "clip_start": obj.data.clip_start, "clip_end": obj.data.clip_end}
           for obj in bpy.data.objects if obj.type == "CAMERA"]
lights = [{"name": obj.name, "type": obj.data.type, "energy": obj.data.energy,
           "color": list(obj.data.color), "location": list(obj.location),
           "rotation_euler": list(obj.rotation_euler),
           "use_shadow": bool(getattr(obj.data, "use_shadow", False)),
           "node_tree": node_tree_info(obj.data.node_tree if getattr(obj.data, "use_nodes", False) else None)}
          for obj in bpy.data.objects if obj.type == "LIGHT"]
materials = [{"name": material.name, "use_nodes": material.use_nodes,
              "surface_render_method": getattr(material, "surface_render_method", None),
              "use_backface_culling": bool(getattr(material, "use_backface_culling", False)),
              "node_tree": node_tree_info(material.node_tree if material.use_nodes else None)}
             for material in bpy.data.materials]
scenes = []
for scene in bpy.data.scenes:
    scenes.append({"name": scene.name, "engine": scene.render.engine,
                   "active_camera": scene.camera.name if scene.camera else None,
                   "object_count": len(scene.objects),
                   "world": scene.world.name if scene.world else None,
                   "resolution": [scene.render.resolution_x, scene.render.resolution_y],
                   "resolution_percentage": scene.render.resolution_percentage,
                   "frame": scene.frame_current, "frame_start": scene.frame_start, "frame_end": scene.frame_end,
                   "fps": scene.render.fps, "unit_scale": scene.unit_settings.scale_length,
                   "exposure": scene.view_settings.exposure, "gamma": scene.view_settings.gamma,
                   "view_transform": scene.view_settings.view_transform, "look": scene.view_settings.look,
                   "cycles_samples": scene.cycles.samples, "cycles_device": scene.cycles.device,
                   "world_node_tree": node_tree_info(scene.world.node_tree if scene.world and scene.world.use_nodes else None),
                   "compositing_enabled": bool(getattr(scene, "use_nodes", False) or getattr(scene, "compositing_node_group", None)),
                   "compositor_node_tree": node_tree_info(getattr(scene, "node_tree", None) or getattr(scene, "compositing_node_group", None))})
report = {
    "checked_at": datetime.now(timezone.utc).isoformat(),
    "file": bpy.data.filepath, "blender_version": bpy.app.version_string,
    "file_version": list(bpy.data.version), "opened": True,
    "autoexec_disabled": not bpy.context.preferences.filepaths.use_scripts_auto_execute,
    "embedded_script_blocked": bool(getattr(bpy.app, "autoexec_fail", False)),
    "embedded_script_message": getattr(bpy.app, "autoexec_fail_message", ""),
    "read_only_inspection": True, "source_saved": False,
    "counts": {"objects": len(bpy.data.objects), "meshes": len(bpy.data.meshes),
               "mesh_polygons_without_modifiers": sum(len(x.polygons) for x in bpy.data.meshes),
               "materials": len(bpy.data.materials), "images": len(bpy.data.images),
               "node_groups": len(bpy.data.node_groups), "cameras": len(cameras),
               "object_types": dict(Counter(x.type for x in bpy.data.objects))},
    "scenes": scenes, "cameras": cameras, "lights": lights, "materials": materials, "images": images,
    "missing_images": [x for x in images if x["missing"]],
    "libraries": libraries, "missing_libraries": [x for x in libraries if x["missing"]],
    "unresolved_library_paths": [x for x in libraries if not x["exists"]],
    "undefined_nodes": [{"group": g.name, "node": n.name, "type": n.bl_idname}
                        for g in bpy.data.node_groups for n in g.nodes if n.type == "UNDEFINED"],
    "modifiers": modifiers,
    "geometry_node_groups": [x.name for x in bpy.data.node_groups if x.bl_idname == "GeometryNodeTree"],
    "embedded_texts": [{"name": x.name, "use_module": x.use_module} for x in bpy.data.texts],
    "driver_count": sum(len(x.animation_data.drivers) for x in bpy.data.objects if x.animation_data),
    "visual_baseline_status": "NOT_TESTED", "engine_import_status": "NOT_TESTED", "build_whitelist": False,
}
(out / "inspection.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("BUTTERFLY_INSPECTION", json.dumps({"file": bpy.data.filepath, "opened": True,
      "counts": report["counts"], "missing_images": len(report["missing_images"]),
      "missing_libraries": len(report["missing_libraries"]), "scenes": scenes}, ensure_ascii=False))
