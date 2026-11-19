"""Split the verified F06 GLB into four V2 import batches without changing binary data."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import struct


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "SourceScenes" / "Working" / "F06" / "F06.ue.glb"
OUTPUT_DIR = ROOT / "SourceScenes" / "Working" / "F06" / "BatchedV2"
REPORT = ROOT / "Evidence" / "Blender" / "F06" / "BatchedV2" / "split-F06-import-report.json"
TARGET_GROUPS = (
    {
        "output": "01-foliage",
        "mesh": 1,
        "mesh_name": "Plane.004",
        "node_names": tuple(f"Cherry_tree_{index}" for index in range(1, 23)),
        "triangles": 838480,
    },
    {
        "output": "02-pagoda",
        "mesh": 9,
        "mesh_name": "Plane.005",
        "node_names": ("Pagoda",),
        "triangles": 616776,
    },
    {
        "output": "03-stairs",
        "mesh": 11,
        "mesh_name": "Plane.001",
        "node_names": ("Stairs_2",),
        "triangles": 1830912,
    },
)
TARGET_MESHES = frozenset(group["mesh"] for group in TARGET_GROUPS)
MAIN_OUTPUT = "04-main"
EXPECTED_SOURCE_BYTES = 542141712
EXPECTED_SOURCE_SHA256 = "52edec52871edea08be42120dacd45b74664b8e6f610890ba6cf6389be4cbcb9"
EXPECTED_UNIQUE_TRIANGLES = 3366038
EXPECTED_INSTANCED_TRIANGLES = 23259240
GLB_MAGIC = 0x46546C67
JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942
COPY_BLOCK_BYTES = 8 * 1024 * 1024


def inspect_glb(path):
    actual_bytes = path.stat().st_size
    full_hash = hashlib.sha256()
    bin_hash = hashlib.sha256()
    with path.open("rb") as handle:
        def take(size):
            data = handle.read(size)
            if len(data) != size:
                raise ValueError(f"Truncated GLB: {path}")
            full_hash.update(data)
            return data

        magic, version, declared_bytes = struct.unpack("<III", take(12))
        if magic != GLB_MAGIC or version != 2:
            raise ValueError(f"Not a GLB 2 file: {path}")
        if declared_bytes != actual_bytes:
            raise ValueError(f"Declared length mismatch: {path}")
        json_bytes, json_type = struct.unpack("<II", take(8))
        if json_type != JSON_CHUNK:
            raise ValueError(f"First chunk is not JSON: {path}")
        document = json.loads(take(json_bytes).decode("utf-8"))
        bin_bytes, bin_type = struct.unpack("<II", take(8))
        if bin_type != BIN_CHUNK:
            raise ValueError(f"Second chunk is not BIN: {path}")
        bin_offset = handle.tell()
        if bin_offset + bin_bytes != actual_bytes:
            raise ValueError(f"BIN length or trailing chunks are invalid: {path}")
        remaining = bin_bytes
        while remaining:
            data = take(min(COPY_BLOCK_BYTES, remaining))
            bin_hash.update(data)
            remaining -= len(data)

    buffers = document.get("buffers", [])
    if len(buffers) != 1 or "uri" in buffers[0]:
        raise ValueError(f"Expected one embedded BIN buffer: {path}")
    buffer_bytes = buffers[0]["byteLength"]
    if not 0 <= bin_bytes - buffer_bytes <= 3:
        raise ValueError(f"BIN chunk does not match buffer byteLength: {path}")
    return {
        "path": path,
        "document": document,
        "bytes": actual_bytes,
        "sha256": full_hash.hexdigest(),
        "bin_offset": bin_offset,
        "bin_bytes": bin_bytes,
        "bin_sha256": bin_hash.hexdigest(),
    }


def primitive_triangles(document, primitive):
    if "indices" in primitive:
        count = document["accessors"][primitive["indices"]]["count"]
    else:
        count = document["accessors"][primitive["attributes"]["POSITION"]]["count"]
    mode = primitive.get("mode", 4)
    if mode == 4:
        if count % 3:
            raise ValueError("Triangle-list index count is not divisible by three")
        return count // 3
    if mode in (5, 6):
        return max(0, count - 2)
    return 0


def mesh_triangles(document):
    return [
        sum(primitive_triangles(document, primitive) for primitive in mesh.get("primitives", []))
        for mesh in document.get("meshes", [])
    ]


def source_hierarchy(document):
    scenes = document.get("scenes", [])
    if len(scenes) != 1 or document.get("scene", 0) != 0:
        raise ValueError("This converter requires exactly one source scene with scene index 0")
    if document.get("skins") or document.get("animations"):
        raise ValueError("Skins and animations are not present in the verified source and are not supported")
    nodes = document.get("nodes", [])
    parents = {}
    for parent, node in enumerate(nodes):
        for child in node.get("children", []):
            if not 0 <= child < len(nodes) or child in parents:
                raise ValueError("Source node hierarchy has an invalid child or multiple parents")
            parents[child] = parent
    roots = scenes[0].get("nodes", [])
    reachable = set()

    def visit(index):
        if index in reachable:
            raise ValueError("Source node hierarchy contains a cycle or repeated node")
        reachable.add(index)
        for child in nodes[index].get("children", []):
            visit(child)

    for root in roots:
        if not 0 <= root < len(nodes):
            raise ValueError("Source scene has an invalid root node")
        visit(root)
    return parents


def material_texture_references(material):
    references = []

    def walk(value, key=None):
        if isinstance(value, dict):
            if key and key.endswith("Texture") and "index" in value:
                references.append(value)
            for child_key, child in value.items():
                if child_key != "extras":
                    walk(child, child_key)
        elif isinstance(value, list):
            for child in value:
                walk(child, key)

    walk(material)
    return references


def texture_image_references(texture):
    references = []
    if "source" in texture:
        references.append(texture)

    def walk_extensions(value):
        if isinstance(value, dict):
            if "source" in value:
                references.append(value)
            for child in value.values():
                walk_extensions(child)
        elif isinstance(value, list):
            for child in value:
                walk_extensions(child)

    walk_extensions(texture.get("extensions", {}))
    return references


def variant_material_references(mesh):
    references = []
    for primitive in mesh.get("primitives", []):
        variants = primitive.get("extensions", {}).get("KHR_materials_variants", {})
        for mapping in variants.get("mappings", []):
            if "material" in mapping:
                references.append(mapping)
    return references


def extension_names(document):
    names = set()

    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "extensions":
                    names.update(child)
                elif key != "extras":
                    walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(document)
    return names


def build_document(source, target_mesh=None):
    document = source["document"]
    nodes = document["nodes"]
    parents = source_hierarchy(document)
    is_main = target_mesh is None
    excluded_meshes = TARGET_MESHES if is_main else {target_mesh}
    target_nodes = {
        index for index, node in enumerate(nodes) if node.get("mesh") in excluded_meshes
    }
    if not target_nodes:
        raise ValueError(f"Source meshes {sorted(excluded_meshes)} have no node instances")

    if not is_main:
        retained = set(target_nodes)
        for index in target_nodes:
            while index in parents:
                index = parents[index]
                retained.add(index)
    else:
        retained = set(range(len(nodes))) - target_nodes
        roots = set(document["scenes"][0].get("nodes", []))
        for index in retained:
            if index not in roots and index in parents and parents[index] not in retained:
                raise ValueError("Main batch would need transform baking below an omitted target node")

    source_indices = sorted(retained)
    node_map = {old: new for new, old in enumerate(source_indices)}
    output_nodes = [deepcopy(nodes[old]) for old in source_indices]
    for old, node in zip(source_indices, output_nodes):
        if "children" in node:
            children = [node_map[child] for child in node["children"] if child in node_map]
            if children:
                node["children"] = children
            else:
                del node["children"]
        if "mesh" in node:
            if not is_main and old not in target_nodes:
                del node["mesh"]
        if not is_main:
            node.pop("camera", None)
            extensions = node.get("extensions", {})
            extensions.pop("KHR_lights_punctual", None)
            if "extensions" in node and not extensions:
                del node["extensions"]

    used_meshes = sorted({node["mesh"] for node in output_nodes if "mesh" in node})
    mesh_map = {old: new for new, old in enumerate(used_meshes)}
    output_meshes = [deepcopy(document["meshes"][old]) for old in used_meshes]
    for node in output_nodes:
        if "mesh" in node:
            node["mesh"] = mesh_map[node["mesh"]]

    used_materials = set()
    for mesh in output_meshes:
        for primitive in mesh.get("primitives", []):
            if "material" in primitive:
                used_materials.add(primitive["material"])
        for reference in variant_material_references(mesh):
            used_materials.add(reference["material"])
    material_map = {old: new for new, old in enumerate(sorted(used_materials))}
    for mesh in output_meshes:
        for primitive in mesh.get("primitives", []):
            if "material" in primitive:
                primitive["material"] = material_map[primitive["material"]]
        for reference in variant_material_references(mesh):
            reference["material"] = material_map[reference["material"]]
    output_materials = [deepcopy(document["materials"][old]) for old in sorted(used_materials)]

    used_textures = sorted({
        reference["index"]
        for material in output_materials
        for reference in material_texture_references(material)
    })
    texture_map = {old: new for new, old in enumerate(used_textures)}
    for material in output_materials:
        for reference in material_texture_references(material):
            reference["index"] = texture_map[reference["index"]]
    output_textures = [deepcopy(document["textures"][old]) for old in used_textures]

    used_images = sorted({
        reference["source"]
        for texture in output_textures
        for reference in texture_image_references(texture)
    })
    image_map = {old: new for new, old in enumerate(used_images)}
    for texture in output_textures:
        for reference in texture_image_references(texture):
            reference["source"] = image_map[reference["source"]]
    output_images = [deepcopy(document["images"][old]) for old in used_images]

    output = deepcopy(document)
    output["nodes"] = output_nodes
    output["scenes"] = deepcopy(document["scenes"])
    output["scenes"][0]["nodes"] = [
        node_map[root] for root in document["scenes"][0].get("nodes", []) if root in node_map
    ]
    output["meshes"] = output_meshes
    for key, values in (
        ("materials", output_materials),
        ("textures", output_textures),
        ("images", output_images),
    ):
        if values:
            output[key] = values
        else:
            output.pop(key, None)

    used_cameras = sorted({node["camera"] for node in output_nodes if "camera" in node})
    camera_map = {old: new for new, old in enumerate(used_cameras)}
    if used_cameras:
        output["cameras"] = [deepcopy(document["cameras"][old]) for old in used_cameras]
        for node in output_nodes:
            if "camera" in node:
                node["camera"] = camera_map[node["camera"]]
    else:
        output.pop("cameras", None)

    light_nodes = [
        node.get("extensions", {}).get("KHR_lights_punctual", {})
        for node in output_nodes
        if "light" in node.get("extensions", {}).get("KHR_lights_punctual", {})
    ]
    used_lights = sorted({extension["light"] for extension in light_nodes})
    light_map = {old: new for new, old in enumerate(used_lights)}
    top_extensions = output.get("extensions", {})
    if used_lights:
        source_lights = document["extensions"]["KHR_lights_punctual"]["lights"]
        top_extensions["KHR_lights_punctual"] = {
            **deepcopy(document["extensions"]["KHR_lights_punctual"]),
            "lights": [deepcopy(source_lights[old]) for old in used_lights],
        }
        for extension in light_nodes:
            extension["light"] = light_map[extension["light"]]
    else:
        top_extensions.pop("KHR_lights_punctual", None)
    if "extensions" in output and not top_extensions:
        del output["extensions"]

    used_extensions = extension_names(output)
    for key in ("extensionsUsed", "extensionsRequired"):
        if key in output:
            values = [name for name in output[key] if name in used_extensions]
            if values:
                output[key] = values
            else:
                del output[key]

    return {
        "document": output,
        "source_indices": source_indices,
        "node_map": node_map,
        "mesh_map": mesh_map,
        "material_map": material_map,
        "texture_map": texture_map,
        "image_map": image_map,
        "camera_map": camera_map,
        "light_map": light_map,
    }


def write_glb(path, document, source, created):
    json_payload = json.dumps(
        document, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    json_payload += b" " * ((-len(json_payload)) % 4)
    declared_bytes = 12 + 8 + len(json_payload) + 8 + source["bin_bytes"]
    with source["path"].open("rb") as input_handle, path.open("xb") as output:
        created.append(path)
        output.write(struct.pack("<III", GLB_MAGIC, 2, declared_bytes))
        output.write(struct.pack("<II", len(json_payload), JSON_CHUNK))
        output.write(json_payload)
        output.write(struct.pack("<II", source["bin_bytes"], BIN_CHUNK))
        input_handle.seek(source["bin_offset"])
        remaining = source["bin_bytes"]
        while remaining:
            data = input_handle.read(min(COPY_BLOCK_BYTES, remaining))
            if not data:
                raise ValueError("Source BIN became truncated during conversion")
            output.write(data)
            remaining -= len(data)


def file_metrics(info, source_indices=None):
    document = info["document"]
    triangles = mesh_triangles(document)
    nodes = document.get("nodes", [])
    if source_indices is None:
        source_indices = list(range(len(nodes)))
    retained_nodes = []
    for new, (old, node) in enumerate(zip(source_indices, nodes)):
        retained_nodes.append({
            "output_index": new,
            "source_index": old,
            "name": node.get("name"),
            "source_mesh": info.get("source_mesh_indices", {}).get(old, node.get("mesh")),
            "output_mesh": node.get("mesh"),
        })
    light_count = sum(
        "light" in node.get("extensions", {}).get("KHR_lights_punctual", {})
        for node in nodes
    )
    reachable = set()
    pending = list(document["scenes"][0].get("nodes", []))
    while pending:
        index = pending.pop()
        if index not in reachable:
            reachable.add(index)
            pending.extend(nodes[index].get("children", []))
    unreferenced = sorted(set(range(len(nodes))) - reachable)
    return {
        "path": str(info["path"].resolve()),
        "bytes": info["bytes"],
        "sha256": info["sha256"],
        "bin_bytes": info["bin_bytes"],
        "bin_sha256": info["bin_sha256"],
        "scene_count": len(document.get("scenes", [])),
        "default_scene": document.get("scene", 0),
        "scene_root_count": len(document["scenes"][0].get("nodes", [])),
        "scene_unreferenced_node_count": len(unreferenced),
        "scene_unreferenced_node_names": [nodes[index].get("name") for index in unreferenced],
        "node_count": len(nodes),
        "mesh_count": len(document.get("meshes", [])),
        "material_count": len(document.get("materials", [])),
        "texture_count": len(document.get("textures", [])),
        "image_count": len(document.get("images", [])),
        "camera_definition_count": len(document.get("cameras", [])),
        "camera_node_count": sum("camera" in node for node in nodes),
        "light_definition_count": len(document.get("extensions", {}).get("KHR_lights_punctual", {}).get("lights", [])),
        "light_node_count": light_count,
        "accessor_count": len(document.get("accessors", [])),
        "bufferView_count": len(document.get("bufferViews", [])),
        "unique_triangles": sum(triangles),
        "instanced_triangles": sum(triangles[node["mesh"]] for node in nodes if "mesh" in node),
        "extensionsUsed": document.get("extensionsUsed", []),
        "extensionsRequired": document.get("extensionsRequired", []),
        "retained_node_names": [node.get("name") for node in nodes],
        "retained_nodes": retained_nodes,
        "meshes": [
            {
                "output_index": index,
                "name": mesh.get("name"),
                "unique_triangles": triangles[index],
                "instance_count": sum(node.get("mesh") == index for node in nodes),
            }
            for index, mesh in enumerate(document.get("meshes", []))
        ],
    }


def validate_output(source, output, build, target_mesh=None):
    source_doc = source["document"]
    document = output["document"]
    source_hierarchy(document)
    for key in ("buffers", "bufferViews", "accessors", "samplers"):
        if document.get(key) != source_doc.get(key):
            raise ValueError(f"{key} changed in {output['path']}")
    if output["bin_bytes"] != source["bin_bytes"] or output["bin_sha256"] != source["bin_sha256"]:
        raise ValueError(f"BIN chunk changed in {output['path']}")

    for old, new in build["node_map"].items():
        source_node = source_doc["nodes"][old]
        output_node = document["nodes"][new]
        for key in ("name", "matrix", "translation", "rotation", "scale", "weights", "extras"):
            if output_node.get(key) != source_node.get(key):
                raise ValueError(f"Node property {key} changed for source node {old}")
        if "mesh" in source_node:
            if target_mesh is not None and source_node["mesh"] != target_mesh:
                if "mesh" in output_node:
                    raise ValueError("A non-target ancestor retained its mesh in a target batch")
            elif output_node.get("mesh") != build["mesh_map"][source_node["mesh"]]:
                raise ValueError(f"Mesh mapping changed for source node {old}")

    for old, new in build["mesh_map"].items():
        expected = deepcopy(source_doc["meshes"][old])
        for primitive in expected.get("primitives", []):
            if "material" in primitive:
                primitive["material"] = build["material_map"][primitive["material"]]
        for reference in variant_material_references(expected):
            reference["material"] = build["material_map"][reference["material"]]
        if document["meshes"][new] != expected:
            raise ValueError(f"Mesh data changed beyond index remapping for source mesh {old}")
    for old, new in build["material_map"].items():
        expected = deepcopy(source_doc["materials"][old])
        for reference in material_texture_references(expected):
            reference["index"] = build["texture_map"][reference["index"]]
        if document["materials"][new] != expected:
            raise ValueError(f"Material data changed beyond texture remapping for source material {old}")
    for old, new in build["texture_map"].items():
        expected = deepcopy(source_doc["textures"][old])
        for reference in texture_image_references(expected):
            reference["source"] = build["image_map"][reference["source"]]
        if document["textures"][new] != expected:
            raise ValueError(f"Texture data changed beyond image remapping for source texture {old}")
    for old, new in build["image_map"].items():
        if document["images"][new] != source_doc["images"][old]:
            raise ValueError(f"Image data changed for source image {old}")
    for old, new in build["camera_map"].items():
        if document["cameras"][new] != source_doc["cameras"][old]:
            raise ValueError(f"Camera data changed for source camera {old}")
    output_lights = document.get("extensions", {}).get("KHR_lights_punctual", {}).get("lights", [])
    source_lights = source_doc.get("extensions", {}).get("KHR_lights_punctual", {}).get("lights", [])
    for old, new in build["light_map"].items():
        if output_lights[new] != source_lights[old]:
            raise ValueError(f"Light data changed for source light {old}")

    if target_mesh is not None:
        if document.get("cameras") or any("camera" in node for node in document["nodes"]):
            raise ValueError("A non-main batch contains a camera")
        if document.get("extensions", {}).get("KHR_lights_punctual") or any(
            "KHR_lights_punctual" in node.get("extensions", {}) for node in document["nodes"]
        ):
            raise ValueError("A non-main batch contains a punctual light")
        if "KHR_lights_punctual" in document.get("extensionsRequired", []):
            raise ValueError("A non-main batch falsely requires KHR_lights_punctual")

    used_meshes = {node["mesh"] for node in document["nodes"] if "mesh" in node}
    if used_meshes != set(range(len(document.get("meshes", [])))):
        raise ValueError("Output has an unused or invalid mesh")
    used_materials = set()
    for mesh in document.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            if "material" in primitive:
                used_materials.add(primitive["material"])
        for reference in variant_material_references(mesh):
            used_materials.add(reference["material"])
    if used_materials != set(range(len(document.get("materials", [])))):
        raise ValueError("Output has an unused or invalid material")
    used_textures = {
        reference["index"]
        for material in document.get("materials", [])
        for reference in material_texture_references(material)
    }
    if used_textures != set(range(len(document.get("textures", [])))):
        raise ValueError("Output has an unused or invalid texture")
    used_images = {
        reference["source"]
        for texture in document.get("textures", [])
        for reference in texture_image_references(texture)
    }
    if used_images != set(range(len(document.get("images", [])))):
        raise ValueError("Output has an unused or invalid image")


def mapping_entries(mapping):
    return [{"source_index": old, "output_index": new} for old, new in sorted(mapping.items())]


def main():
    output_names = [group["output"] for group in TARGET_GROUPS] + [MAIN_OUTPUT]
    output_paths = [OUTPUT_DIR / f"{name}.glb" for name in output_names] + [REPORT]
    for path in output_paths:
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite existing output: {path}")

    source = inspect_glb(SOURCE)
    if source["bytes"] != EXPECTED_SOURCE_BYTES or source["sha256"] != EXPECTED_SOURCE_SHA256:
        raise ValueError("Source size or SHA256 does not match the verified F06.ue.glb")
    source_doc = source["document"]
    source_hierarchy(source_doc)
    source_triangles = mesh_triangles(source_doc)
    if sum(source_triangles) != EXPECTED_UNIQUE_TRIANGLES:
        raise ValueError("Source unique triangle count changed")
    source_instanced = sum(
        source_triangles[node["mesh"]] for node in source_doc["nodes"] if "mesh" in node
    )
    if source_instanced != EXPECTED_INSTANCED_TRIANGLES:
        raise ValueError("Source instanced triangle count changed")
    if len(source_doc["meshes"]) != 14 or len(TARGET_MESHES) != len(TARGET_GROUPS):
        raise ValueError("Source mesh layout or target group layout changed")

    group_nodes = {}
    for group in TARGET_GROUPS:
        mesh_index = group["mesh"]
        if source_doc["meshes"][mesh_index].get("name") != group["mesh_name"]:
            raise ValueError(f"Mesh name mismatch for target mesh {mesh_index}")
        if source_triangles[mesh_index] != group["triangles"]:
            raise ValueError(f"Triangle count mismatch for target mesh {mesh_index}")
        nodes = [
            index for index, node in enumerate(source_doc["nodes"])
            if node.get("mesh") == mesh_index
        ]
        names = tuple(source_doc["nodes"][index].get("name") for index in nodes)
        if names != group["node_names"]:
            raise ValueError(f"Node label mismatch for target mesh {mesh_index}: {names}")
        group_nodes[group["output"]] = nodes

    builds = {
        group["output"]: build_document(source, target_mesh=group["mesh"])
        for group in TARGET_GROUPS
    }
    builds[MAIN_OUTPUT] = build_document(source)
    source_mesh_nodes = {
        index for index, node in enumerate(source_doc["nodes"]) if "mesh" in node
    }
    for old, node in enumerate(source_doc["nodes"]):
        has_light = "light" in node.get("extensions", {}).get("KHR_lights_punctual", {})
        if ("camera" in node or has_light) and old not in builds[MAIN_OUTPUT]["node_map"]:
            raise ValueError("A source camera or light would be omitted from main")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    created = []
    try:
        inspected = {}
        for name in output_names:
            path = OUTPUT_DIR / f"{name}.glb"
            target_mesh = next(
                (group["mesh"] for group in TARGET_GROUPS if group["output"] == name), None
            )
            write_glb(path, builds[name]["document"], source, created)
            inspected[name] = inspect_glb(path)
            validate_output(source, inspected[name], builds[name], target_mesh=target_mesh)

        covered_mesh_nodes = set()
        for name in output_names:
            mesh_nodes = {
                old for old, new in builds[name]["node_map"].items()
                if "mesh" in inspected[name]["document"]["nodes"][new]
            }
            if covered_mesh_nodes & mesh_nodes:
                raise ValueError(f"Source mesh-bearing node duplicated in {name}")
            covered_mesh_nodes |= mesh_nodes
        if covered_mesh_nodes != source_mesh_nodes:
            raise ValueError("Not every source mesh-bearing node was retained exactly once")

        source_metrics = file_metrics(source)
        output_metrics = {}
        for name in output_names:
            info = inspected[name]
            info["source_mesh_indices"] = {
                old: source_doc["nodes"][old].get("mesh") for old in builds[name]["source_indices"]
            }
            output_metrics[name] = file_metrics(info, builds[name]["source_indices"])
            output_metrics[name]["index_maps"] = {
                key: mapping_entries(builds[name][key])
                for key in ("node_map", "mesh_map", "material_map", "texture_map", "image_map", "camera_map", "light_map")
            }

        instanced_sum = sum(item["instanced_triangles"] for item in output_metrics.values())
        unique_sum = sum(item["unique_triangles"] for item in output_metrics.values())
        if instanced_sum != source_instanced:
            raise ValueError("Output instanced triangle counts do not sum to the source")
        if unique_sum != sum(source_triangles):
            raise ValueError("Output unique triangle counts do not sum to the source")

        report = {
            "scene_id": "F06",
            "operation": "V2 split of meshes 1, 9, and 11 into separate GLB import batches; no geometry or transform simplification",
            "source": source_metrics,
            "target_groups": [
                {
                    "output": f"{group['output']}.glb",
                    "source_mesh_index": group["mesh"],
                    "name": group["mesh_name"],
                    "unique_triangles": source_triangles[group["mesh"]],
                    "instance_count": len(group_nodes[group["output"]]),
                    "source_node_indices": group_nodes[group["output"]],
                    "source_node_names": list(group["node_names"]),
                }
                for group in TARGET_GROUPS
            ],
            "outputs": output_metrics,
            "validation": {
                "source_size_and_sha256_match": True,
                "target_mesh_names_node_labels_and_triangle_counts_match": True,
                "glb_headers_declared_lengths_and_chunks_valid": True,
                "single_actual_source_scene_retained": True,
                "scene_roots_and_node_references_valid": True,
                "source_unreferenced_nodes_retained_without_adding_scene_roots": True,
                "bin_chunks_byte_identical_by_length_and_sha256": True,
                "buffers_bufferViews_accessors_and_samplers_unchanged": True,
                "node_transforms_and_extras_unchanged": True,
                "material_alpha_doubleSided_and_extras_retained": True,
                "each_source_mesh_bearing_node_retained_exactly_once": True,
                "source_mesh_bearing_node_count": len(source_mesh_nodes),
                "instanced_triangle_sum_matches_source": instanced_sum == source_instanced,
                "unique_triangle_sum_matches_source": unique_sum == sum(source_triangles),
                "non_main_batches_have_no_camera_or_light": True,
                "main_preserves_all_source_camera_and_light_nodes": True,
                "meshes_materials_textures_images_pruned_to_references": True,
            },
            "ue_import_status": "NOT_RUN",
        }
        with REPORT.open("x", encoding="utf-8", newline="\n") as handle:
            created.append(REPORT)
            json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
    except Exception:
        for path in created:
            if path.exists():
                path.unlink()
        raise

    print(json.dumps({
        "report": str(REPORT.resolve()),
        "outputs": {
            name: {
                "path": str((OUTPUT_DIR / f"{name}.glb").resolve()),
                "instanced_triangles": output_metrics[name]["instanced_triangles"],
            }
            for name in output_names
        },
        "source_instanced_triangles": source_instanced,
        "validation": "PASSED",
        "ue_import_status": "NOT_RUN",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
