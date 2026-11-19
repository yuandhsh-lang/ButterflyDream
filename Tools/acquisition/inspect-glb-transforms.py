"""Inspect GLB node transforms, mesh bounds, and camera/AABB intersections without GPU assets."""
import json
from math import sqrt
from pathlib import Path
import struct
import sys

source = Path(sys.argv[1])
out = Path(sys.argv[2])
with source.open("rb") as handle:
    magic, version, length = struct.unpack("<III", handle.read(12))
    if magic != 0x46546C67 or version != 2:
        raise ValueError("Not a GLB 2 file")
    json_length, chunk_type = struct.unpack("<II", handle.read(8))
    if chunk_type != 0x4E4F534A:
        raise ValueError("First GLB chunk is not JSON")
    document = json.loads(handle.read(json_length))

nodes = document.get("nodes", [])
parents = {child: index for index, node in enumerate(nodes) for child in node.get("children", [])}

def identity():
    return [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]

def multiply(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]

def local_matrix(node):
    if "matrix" in node:
        m = node["matrix"]
        return [[m[0], m[4], m[8], m[12]], [m[1], m[5], m[9], m[13]], [m[2], m[6], m[10], m[14]], [m[3], m[7], m[11], m[15]]]
    translation = node.get("translation", [0, 0, 0])
    rotation = node.get("rotation", [0, 0, 0, 1])
    scale = node.get("scale", [1, 1, 1])
    x, y, z, w = rotation
    result = identity()
    rotation_rows = [
        [1 - 2 * (y*y + z*z), 2 * (x*y - z*w), 2 * (x*z + y*w)],
        [2 * (x*y + z*w), 1 - 2 * (x*x + z*z), 2 * (y*z - x*w)],
        [2 * (x*z - y*w), 2 * (y*z + x*w), 1 - 2 * (x*x + y*y)],
    ]
    for i in range(3):
        for j in range(3):
            result[i][j] = rotation_rows[i][j] * scale[j]
        result[i][3] = translation[i]
    return result

world_cache = {}
def world(index):
    if index not in world_cache:
        matrix = local_matrix(nodes[index])
        world_cache[index] = multiply(world(parents[index]), matrix) if index in parents else matrix
    return world_cache[index]

def transform_point(matrix, point):
    return [sum(matrix[i][j] * point[j] for j in range(3)) + matrix[i][3] for i in range(3)]

def transform_direction(matrix, vector):
    return [sum(matrix[i][j] * vector[j] for j in range(3)) for i in range(3)]

def ray_box(origin, direction, minimum, maximum):
    near, far = 0.0, float("inf")
    for i in range(3):
        if abs(direction[i]) < 1e-12:
            if origin[i] < minimum[i] or origin[i] > maximum[i]:
                return None
            continue
        a, b = (minimum[i] - origin[i]) / direction[i], (maximum[i] - origin[i]) / direction[i]
        if a > b:
            a, b = b, a
        near, far = max(near, a), min(far, b)
        if near > far:
            return None
    return near

mesh_bounds = []
for index, node in enumerate(nodes):
    if "mesh" not in node:
        continue
    for primitive in document["meshes"][node["mesh"]].get("primitives", []):
        position_index = primitive.get("attributes", {}).get("POSITION")
        if position_index is None:
            continue
        accessor = document["accessors"][position_index]
        if "min" not in accessor or "max" not in accessor:
            continue
        low, high = accessor["min"], accessor["max"]
        corners = [[x, y, z] for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]
        transformed = [transform_point(world(index), point) for point in corners]
        mesh_bounds.append({"node": index, "name": node.get("name"),
                            "min": [min(point[i] for point in transformed) for i in range(3)],
                            "max": [max(point[i] for point in transformed) for i in range(3)]})
if not mesh_bounds:
    raise RuntimeError("No mesh POSITION accessor bounds found")
global_min = [min(item["min"][i] for item in mesh_bounds) for i in range(3)]
global_max = [max(item["max"][i] for item in mesh_bounds) for i in range(3)]
cameras = []
for index, node in enumerate(nodes):
    if "camera" not in node:
        continue
    matrix = world(index)
    origin = [matrix[i][3] for i in range(3)]
    direction = transform_direction(matrix, [0, 0, -1])
    direction = [value / sqrt(sum(x*x for x in direction)) for value in direction]
    hits = []
    for item in mesh_bounds:
        distance = ray_box(origin, direction, item["min"], item["max"])
        if distance is not None:
            hits.append({"node": item["node"], "name": item["name"], "aabb_distance": distance})
    cameras.append({"node": index, "name": node.get("name"), "position": origin, "forward": direction,
                    "nearest_aabb_hits": sorted(hits, key=lambda item: item["aabb_distance"])[:12]})
report = {"file": str(source), "source_sha256_scope": "JSON node/transform inspection only",
          "mesh_primitive_bounds_count": len(mesh_bounds), "bounds_min": global_min, "bounds_max": global_max,
          "cameras": cameras}
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"bounds_min": global_min, "bounds_max": global_max, "cameras": cameras}, ensure_ascii=False), flush=True)
