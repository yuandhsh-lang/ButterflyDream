"""Audit, restore, or roll back GLB-authored Lux materials in UE 5.8.

Run inside Unreal/ButterflyDream with LUX_MATERIAL_RECOVERY_MODE:
  dump (default): read-only; writes a timestamped JSON snapshot.
  apply: requires a clean dump from the same current material state.
  rollback: requires LUX_MATERIAL_REPORT pointing to an apply report.

No mesh/map deletion, reimport, BaseColor-to-Emissive binding, blanket white
BaseColorFactor, AO reset to zero, or editor shutdown is performed here.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import struct
import traceback
from datetime import datetime, timezone
from pathlib import Path

import unreal


ROOT = Path(__file__).resolve().parents[2]
PROJECT_DIR = ROOT / "Unreal" / "ButterflyDream"
LUX_ROOT = ROOT / "Assets" / "LuxGenerated"
REPORT_DIR = ROOT / "Evidence" / "Unreal" / "FourRealms_20261119"
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{os.getpid()}"
MODE = os.environ.get("LUX_MATERIAL_RECOVERY_MODE", "dump").strip().lower()

ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
MATERIALS = unreal.MaterialEditingLibrary

# The explicit UE mesh mapping is intentional: a same-named material in another
# package is never enough to associate it with a GLB.
MESH_SOURCES = {
    "/Game/LuxGenerated/Butterfly_B01/Butterfly_Body": "ReconstructedButterfly_20261119/Ready/Butterfly_Body.glb",
    "/Game/LuxGenerated/Butterfly_B01/Wing_L": "ReconstructedButterfly_20261119/Ready/Wing_L.glb",
    "/Game/LuxGenerated/Butterfly_B01/Wing_R": "ReconstructedButterfly_20261119/Ready/Wing_R.glb",
    "/Game/LuxGenerated/Gate_G01/Gate_Frame": "V2_Gates/Ready/Gate_Frame.glb",
    "/Game/LuxGenerated/Gate_G01/Gate_Leaf_L": "V2_Gates/Ready/Gate_Leaf_L.glb",
    "/Game/LuxGenerated/Gate_G01/Gate_Leaf_R": "V2_Gates/Ready/Gate_Leaf_R.glb",
    "/Game/LuxGenerated/Gate_G03/StarGate_OuterRing": "V2_Gates/Ready/StarGate_OuterRing.glb",
    "/Game/LuxGenerated/Gate_G03/StarGate_InnerRing": "V2_Gates/Ready/StarGate_InnerRing.glb",
    "/Game/LuxGenerated/Tunnel_T01/Tunnel_Ring": "V2_Gates/Ready/Tunnel_Ring.glb",
    "/Game/LuxGenerated/Pavilion_S01/Floating_Pavilion": "V2_Sanctuary/Ready/Floating_Pavilion.glb",
    "/Game/LuxGenerated/Sanctuary/Celestial_Bridge": "V2_Sanctuary/Ready/Celestial_Bridge.glb",
    "/Game/LuxGenerated/Sanctuary/Celestial_Guardian": "V2_Sanctuary/Ready/Celestial_Guardian.glb",
    "/Game/LuxGenerated/Sanctuary/Dragon_Pillar": "V2_Sanctuary/Ready/Dragon_Pillar.glb",
    "/Game/LuxGenerated/Props/Floating_Lantern": "V2_Sanctuary/Ready/Floating_Lantern.glb",
    "/Game/LuxGenerated/Props/Crystal_Lotus": "V2_Sanctuary/Ready/Crystal_Lotus.glb",
    "/Game/LuxGenerated/Extra/Ink_Cloud_Mountain_Complex": "V2_Extra/Ready/Ink_Cloud_Mountain_Complex.glb",
    "/Game/LuxGenerated/Extra/Luminous_Guqin_Bridge": "V2_Extra/Ready/Luminous_Guqin_Bridge.glb",
    "/Game/LuxGenerated/Extra/Seven_Tier_Crystal_Pagoda": "V2_Extra/Ready/Seven_Tier_Crystal_Pagoda.glb",
    "/Game/LuxGenerated/Extra/Floating_Crystal_Garden": "V2_Extra/Ready/Floating_Crystal_Garden.glb",
    "/Game/LuxGenerated/Extra/Taiji_Star_Sphere": "V2_Extra/Ready/Taiji_Star_Sphere.glb",
    "/Game/LuxGenerated/Extra/Celestial_Scroll_Gate": "V2_Extra/Ready/Celestial_Scroll_Gate.glb",
    "/Game/LuxGenerated/Extra/Ink_Ripple_Portal": "V2_Extra/Ready/Ink_Ripple_Portal.glb",
    "/Game/LuxGenerated/Extra/Crystal_Prism_Portal": "V2_Extra/Ready/Crystal_Prism_Portal.glb",
    "/Game/LuxGenerated/Extra/Celestial_Spirit_Koi": "V2_Extra/Ready/Celestial_Spirit_Koi.glb",
    "/Game/LuxGenerated/Extra/Sakura_Spirit_Swirl": "V2_Extra/Ready/Sakura_Spirit_Swirl.glb",
    "/Game/LuxGenerated/Scale_T02/Dream_Scale_Blade": "Ready/Dream_Scale_Blade.glb",
}

# No GLB in scope declares KHR_materials_iridescence. These are deliberately
# small authored caps for wing membranes and a few crystal assets, not a global
# iridescence boost. Every other source gets exactly zero.
CURATED_IRIDESCENCE = {
    "Wing_L": (0.16, 320.0),
    "Wing_R": (0.16, 320.0),
    "Crystal_Lotus": (0.10, 280.0),
    "Seven_Tier_Crystal_Pagoda": (0.10, 280.0),
    "Floating_Crystal_Garden": (0.10, 280.0),
    "Crystal_Prism_Portal": (0.10, 280.0),
}

REQUIRED_SCALARS = (
    "MetallicFactor",
    "RoughnessFactor",
    "OcclusionStrength",
    "EmissiveStrength",
)
REQUIRED_VECTORS = ("BaseColorFactor", "EmissiveFactor")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_glb_json(path: Path) -> dict:
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError(f"GLB is too short: {path}")
    magic, version, declared_length = struct.unpack_from("<III", raw, 0)
    if magic != 0x46546C67 or version != 2 or declared_length != len(raw):
        raise ValueError(f"Not a complete glTF 2.0 GLB: {path}")
    offset = 12
    document = None
    while offset + 8 <= len(raw):
        chunk_length, chunk_type = struct.unpack_from("<II", raw, offset)
        offset += 8
        chunk = raw[offset : offset + chunk_length]
        if len(chunk) != chunk_length:
            raise ValueError(f"Truncated GLB chunk: {path}")
        if chunk_type == 0x4E4F534A:
            document = json.loads(chunk.decode("utf-8"))
        offset += chunk_length
    if document is None:
        raise ValueError(f"GLB has no JSON chunk: {path}")
    return document


def normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def linear_list(value: unreal.LinearColor) -> list[float]:
    return [float(value.r), float(value.g), float(value.b), float(value.a)]


def object_path(value: object) -> str | None:
    return value.get_path_name() if value else None


def values_equal(left: object, right: object) -> bool:
    if isinstance(left, (float, int)) and isinstance(right, (float, int)):
        return abs(float(left) - float(right)) <= 0.0001
    if isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
        return all(values_equal(a, b) for a, b in zip(left, right))
    if isinstance(left, dict) and isinstance(right, dict) and left.keys() == right.keys():
        return all(values_equal(left[key], right[key]) for key in left)
    return left == right


def manifest_sha(folder: str, ready_name: str, manifest: dict) -> str:
    ready_key = f"Ready/{ready_name}"
    relative = f'{folder}/{ready_key}'
    if folder in {'V2_Butterfly', 'ReconstructedButterfly_20261119'}:
        return manifest["ready_meshes"][ready_key]["sha256"]
    if folder == "V2_Gates":
        return manifest["hashes"][ready_key]["sha256"]
    if folder == "Ready":
        for record in manifest["records"]:
            if ready_key in record.get("hashes", {}):
                return record["hashes"][ready_key]["sha256"]
    for asset in manifest["assets"]:
        if asset["readyFile"] == ready_key:
            return asset["hashes"][ready_key]["sha256"]
    raise KeyError(f"{ready_key} is not declared by {folder}/manifest.json")


def texture_source(document: dict, reference: dict | None, mesh_stem: str) -> dict | None:
    if reference is None:
        return None
    texture_index = int(reference["index"])
    texture = document["textures"][texture_index]
    image_index = int(texture["source"])
    image = document["images"][image_index]
    image_name = image.get("name") or f"{mesh_stem}_texture_{texture_index}"
    return {
        "texture_index": texture_index,
        "image_index": image_index,
        "expected_ue_texture_name": image_name,
    }


def build_source_catalog() -> dict[str, dict]:
    catalog = {}
    for mesh_path, relative in MESH_SOURCES.items():
        folder = relative.split("/", 1)[0]
        source_path = LUX_ROOT / relative
        manifest_path = LUX_ROOT / "lux-generation-ledger.json" if folder == "Ready" else LUX_ROOT / folder / "manifest.json"
        if not source_path.is_file():
            raise FileNotFoundError(f"Missing source GLB: {source_path}")
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Missing source manifest: {manifest_path}")
        document = read_glb_json(source_path)
        materials = document.get("materials", [])
        primitives = [
            primitive
            for mesh in document.get("meshes", [])
            for primitive in mesh.get("primitives", [])
        ]
        if len(materials) != 1 or not primitives:
            raise ValueError(f"Expected one material and primitives in {source_path}")
        if {int(primitive.get("material", 0)) for primitive in primitives} != {0}:
            raise ValueError(f"Ambiguous primitive/material mapping in {source_path}")

        source_material = materials[0]
        pbr = source_material.get("pbrMetallicRoughness", {})
        emissive_factor = list(source_material.get("emissiveFactor", [0.0, 0.0, 0.0]))
        emissive_texture = source_material.get("emissiveTexture")
        emissive_extension = source_material.get("extensions", {}).get(
            "KHR_materials_emissive_strength", {}
        )
        has_emissive = emissive_texture is not None or any(abs(float(v)) > 0.0 for v in emissive_factor)
        stem = source_path.stem
        actual_sha = sha256_file(source_path)
        expected_sha = manifest_sha(folder, source_path.name, load_json(manifest_path))
        iridescence_extension = source_material.get("extensions", {}).get(
            "KHR_materials_iridescence", {}
        )
        if "iridescenceFactor" in iridescence_extension:
            iridescence = float(iridescence_extension["iridescenceFactor"])
            iridescence_origin = "KHR_materials_iridescence"
            thickness = float(iridescence_extension.get("iridescenceThicknessMaximum", 0.0))
        else:
            iridescence, thickness = CURATED_IRIDESCENCE.get(stem, (0.0, 0.0))
            iridescence_origin = "curated_cap" if stem in CURATED_IRIDESCENCE else "gltf_default_zero"
        if iridescence > 0.20:
            raise ValueError(f"Refusing non-restrained iridescence {iridescence} in {source_path}")

        catalog[mesh_path] = {
            "mesh_path": mesh_path,
            "source_glb": str(source_path),
            "source_glb_relative": relative,
            "source_sha256": actual_sha,
            "manifest_sha256": expected_sha,
            "source_revision_note": 'Reconstructed from the retained original task GLB and part-split; the authored PBR preparation is not an unmodified original task download.' if folder == 'ReconstructedButterfly_20261119' else None,
            "source_material_name": source_material.get("name", ""),
            "textures": {
                "BaseColorTexture": texture_source(document, pbr.get("baseColorTexture"), stem),
                "MetallicRoughnessTexture": texture_source(
                    document, pbr.get("metallicRoughnessTexture"), stem
                ),
                "EmissiveTexture": texture_source(document, emissive_texture, stem),
                "OcclusionTexture": texture_source(
                    document, source_material.get("occlusionTexture"), stem
                ),
            },
            "has_source_emissive": has_emissive,
            "desired": {
                "scalar": {
                    "MetallicFactor": float(pbr.get("metallicFactor", 1.0)),
                    "RoughnessFactor": float(pbr.get("roughnessFactor", 1.0)),
                    "OcclusionStrength": float(
                        source_material.get("occlusionTexture", {}).get("strength", 1.0)
                    ),
                    "EmissiveStrength": (
                        float(emissive_extension.get("emissiveStrength", 1.0)) if has_emissive else 0.0
                    ),
                    "IridescenceFactor": iridescence,
                    "IridescenceThicknessMaximum": thickness if iridescence > 0.0 else 0.0,
                },
                "vector": {
                    "BaseColorFactor": list(pbr.get("baseColorFactor", [1.0, 1.0, 1.0, 1.0])),
                    "EmissiveFactor": [float(v) for v in emissive_factor] + [1.0],
                },
                "texture": {
                    # A missing source emissive channel must not retain an
                    # uncontrolled BaseColor binding. Source textures themselves
                    # are validated and otherwise left untouched.
                    "EmissiveTexture": None if emissive_texture is None else "__PRESERVE_VALIDATED_SOURCE__",
                },
            },
            "iridescence_origin": iridescence_origin,
        }
    return catalog


def parameter_names(material: unreal.MaterialInstanceConstant) -> dict[str, list[str]]:
    return {
        "scalar": [str(name) for name in MATERIALS.get_scalar_parameter_names(material)],
        "vector": [str(name) for name in MATERIALS.get_vector_parameter_names(material)],
        "texture": [str(name) for name in MATERIALS.get_texture_parameter_names(material)],
    }


def read_parameter(material: unreal.MaterialInstanceConstant, kind: str, name: str) -> object:
    if kind == "scalar":
        return float(MATERIALS.get_material_instance_scalar_parameter_value(material, name))
    if kind == "vector":
        return linear_list(MATERIALS.get_material_instance_vector_parameter_value(material, name))
    if kind == "texture":
        return object_path(MATERIALS.get_material_instance_texture_parameter_value(material, name))
    raise ValueError(f"Unknown parameter kind: {kind}")


def write_parameter(material: unreal.MaterialInstanceConstant, kind: str, name: str, value: object) -> None:
    if kind == "scalar":
        MATERIALS.set_material_instance_scalar_parameter_value(material, name, float(value))
    elif kind == "vector":
        MATERIALS.set_material_instance_vector_parameter_value(material, name, unreal.LinearColor(*value))
    elif kind == "texture":
        MATERIALS.set_material_instance_texture_parameter_value(material, name, value)
    else:
        raise ValueError(f"Unknown parameter kind: {kind}")
    actual = read_parameter(material, kind, name)
    expected = object_path(value) if kind == "texture" else value
    if not values_equal(actual, expected):
        raise RuntimeError(
            f"Read-back mismatch for {material.get_path_name()} {kind}:{name}: "
            f"expected {expected!r}, got {actual!r}"
        )


def snapshot(
    material: unreal.MaterialInstanceConstant, names: dict[str, list[str]]
) -> tuple[dict[str, dict], list[str]]:
    values: dict[str, dict] = {"scalar": {}, "vector": {}, "texture": {}}
    errors = []
    for kind in ("scalar", "vector", "texture"):
        for name in names[kind]:
            try:
                values[kind][name] = read_parameter(material, kind, name)
            except Exception as exc:
                errors.append(
                    f"{material.get_path_name()} read {kind}:{name} failed: {type(exc).__name__}: {exc}"
                )
    return values, errors


def validate_texture_binding(
    material: unreal.MaterialInstanceConstant,
    names: dict[str, list[str]],
    semantic: str,
    expected: dict | None,
) -> list[str]:
    if expected is None:
        return []
    if semantic not in names["texture"]:
        return [f"Required GLB texture parameter {semantic} is not exposed"]
    texture = MATERIALS.get_material_instance_texture_parameter_value(material, semantic)
    if not texture:
        return [f"Required GLB texture parameter {semantic} is null"]
    actual_name = normalized_name(texture.get_name())
    expected_name = normalized_name(expected["expected_ue_texture_name"])
    if actual_name != expected_name:
        return [
            f"{semantic} name mismatch: UE={texture.get_name()} "
            f"GLB={expected['expected_ue_texture_name']}"
        ]
    return []


def collect_materials(catalog: dict[str, dict]) -> tuple[list[dict], list[str], list[str], list[dict]]:
    entries = []
    failures = []
    missing_assets = []
    optional_notes = []
    owners: dict[str, str] = {}

    for mesh_path, source in catalog.items():
        entry = {
            "mesh": mesh_path,
            "source_glb": source["source_glb"],
            "source_glb_relative": source["source_glb_relative"],
            "source_sha256": source["source_sha256"],
            "manifest_sha256": source["manifest_sha256"],
            "source_revision_note": source["source_revision_note"],
            "source_material_name": source["source_material_name"],
            "source_textures": source["textures"],
            "has_source_emissive": source["has_source_emissive"],
            "iridescence_origin": source["iridescence_origin"],
            "desired_values": source["desired"],
            "mapping_errors": [],
            "status": "PENDING",
        }
        entries.append(entry)
        if source['source_revision_note']:
            optional_notes.append({'mesh': mesh_path, 'provenance': source['source_revision_note']})
        try:
            if source["source_sha256"] != source["manifest_sha256"]:
                raise RuntimeError("Actual GLB SHA256 differs from manifest")
            mesh = ASSETS.load_asset(mesh_path)
            if not isinstance(mesh, unreal.StaticMesh):
                raise RuntimeError(f"UE StaticMesh is missing: {mesh_path}")
            slots = mesh.get_editor_property("static_materials")
            if len(slots) != 1:
                raise RuntimeError(f"Expected one UE material slot, found {len(slots)}")
            material = slots[0].material_interface
            if not isinstance(material, unreal.MaterialInstanceConstant):
                raise RuntimeError(
                    f"Expected MaterialInstanceConstant, got {type(material).__name__ if material else 'null'}"
                )
            slot_name = str(slots[0].material_slot_name)
            acceptable_names = {source["source_material_name"], material.get_name()}
            if slot_name not in acceptable_names:
                raise RuntimeError(
                    f"Material slot/name does not confirm GLB mapping: slot={slot_name}, "
                    f"UE={material.get_name()}, GLB={source['source_material_name']}"
                )
            material_path = material.get_path_name()
            previous_owner = owners.setdefault(material_path, mesh_path)
            if previous_owner != mesh_path:
                raise RuntimeError(
                    f"Shared material has ambiguous sources: {previous_owner} and {mesh_path}"
                )
            entry["material"] = material_path
            entry["parent"] = object_path(material.get_editor_property("parent"))
            names = parameter_names(material)
            entry["parameter_names"] = names
            for name in REQUIRED_SCALARS:
                if name not in names["scalar"]:
                    entry["mapping_errors"].append(f"Required scalar parameter is absent: {name}")
            for name in REQUIRED_VECTORS:
                if name not in names["vector"]:
                    entry["mapping_errors"].append(f"Required vector parameter is absent: {name}")
            for semantic in ("BaseColorTexture", "MetallicRoughnessTexture", "EmissiveTexture"):
                entry["mapping_errors"].extend(
                    validate_texture_binding(material, names, semantic, source["textures"][semantic])
                )
            for name in ("IridescenceFactor", "IridescenceThicknessMaximum"):
                if name not in names["scalar"]:
                    optional_notes.append(
                        f"{material_path}: {name} is not exposed; no iridescence write is possible"
                    )
            current, read_errors = snapshot(material, names)
            entry["current_values"] = current
            entry["mapping_errors"].extend(read_errors)
            entry["status"] = "DUMPED" if not entry["mapping_errors"] else "MAPPING_FAILED"
        except Exception as exc:
            entry["mapping_errors"].append(f"{type(exc).__name__}: {exc}")
            entry["status"] = "MAPPING_FAILED"
            if not ASSETS.does_asset_exist(mesh_path):
                missing_assets.append(mesh_path)

        if entry["mapping_errors"]:
            failures.extend(f"{mesh_path}: {error}" for error in entry["mapping_errors"])

    unmapped = []
    for asset_path in ASSETS.list_assets("/Game/LuxGenerated", recursive=True):
        package_path = asset_path.split(".", 1)[0]
        asset = ASSETS.load_asset(package_path)
        if not isinstance(asset, (unreal.Material, unreal.MaterialInstanceConstant)):
            continue
        full_path = asset.get_path_name()
        if full_path not in owners:
            unmapped.append(
                {
                    "material": full_path,
                    "action": "UNCHANGED",
                    "reason": "Not referenced by the explicit V2 Ready GLB/mesh mapping",
                }
            )
    return entries, failures, missing_assets, optional_notes + unmapped


def serialize_unmapped(items: list[object]) -> list[object]:
    return items


def find_input_report(prefix: str, required_explicit: bool) -> Path:
    configured = os.environ.get("LUX_MATERIAL_REPORT", "").strip()
    if configured:
        path = Path(configured).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"LUX_MATERIAL_REPORT does not exist: {path}")
        return path
    if required_explicit:
        raise RuntimeError("Rollback requires LUX_MATERIAL_REPORT pointing to an apply report")
    candidates = sorted(REPORT_DIR.glob(f"{prefix}-*.json"), key=lambda path: path.name)
    if not candidates:
        raise FileNotFoundError(f"No {prefix}-*.json report in {REPORT_DIR}; run dump first")
    return candidates[-1]


def subset(values: dict[str, dict], desired: dict[str, dict]) -> dict[str, dict]:
    result = {"scalar": {}, "vector": {}, "texture": {}}
    for kind in result:
        for name, target in desired[kind].items():
            if target == "__PRESERVE_VALIDATED_SOURCE__":
                continue
            if name in values[kind]:
                result[kind][name] = values[kind][name]
    return result


def apply_recovery(report: dict, catalog: dict[str, dict]) -> None:
    dump_path = find_input_report("material-dump", required_explicit=False)
    dump = load_json(dump_path)
    if dump.get("mode") != "dump" or dump.get("status") != "DUMPED" or dump.get("failures"):
        raise RuntimeError(f"Apply requires a clean, read-only dump; inspect {dump_path}")
    baseline_by_material = {
        entry.get("material"): entry for entry in dump["materials"] if entry.get("material")
    }
    entries, failures, missing, notes = collect_materials(catalog)
    report["materials"] = entries
    report["missing_assets"] = missing
    report["notes"] = serialize_unmapped(notes)
    report["source_dump"] = str(dump_path)
    report["failures"] = failures
    if failures:
        raise RuntimeError("Current material mapping has failures; no recovery writes were attempted")

    for entry in entries:
        material_path = entry["material"]
        baseline = baseline_by_material.get(material_path)
        if not baseline:
            raise RuntimeError(f"Material was not present in source dump: {material_path}")
        if baseline["source_sha256"] != entry["source_sha256"]:
            raise RuntimeError(f"Source GLB changed since dump: {entry['source_glb']}")
        if not values_equal(baseline["current_values"], entry["current_values"]):
            raise RuntimeError(f"Material changed after dump; create a fresh dump: {material_path}")

    recovered_count = 0
    for entry in entries:
        material = ASSETS.load_asset(entry["material"].split(".", 1)[0])
        if not isinstance(material, unreal.MaterialInstanceConstant):
            raise RuntimeError(f"Cannot reload MaterialInstanceConstant: {entry['material']}")
        desired = entry["desired_values"]
        before = subset(entry["current_values"], desired)
        entry["before_values"] = before
        changed = []
        try:
            for kind in ("scalar", "vector", "texture"):
                available = set(entry["parameter_names"][kind])
                for name, target in desired[kind].items():
                    if target == "__PRESERVE_VALIDATED_SOURCE__":
                        continue
                    if name not in available:
                        if name in ("IridescenceFactor", "IridescenceThicknessMaximum"):
                            entry.setdefault("optional_parameters_not_written", []).append(name)
                            continue
                        raise RuntimeError(f"Required parameter disappeared: {kind}:{name}")
                    old_value = read_parameter(material, kind, name)
                    write_parameter(material, kind, name, target)
                    changed.append((kind, name, old_value))
            MATERIALS.update_material_instance(material)
            if not ASSETS.save_loaded_asset(material, False):
                raise RuntimeError(f"save_loaded_asset failed: {entry['material']}")
            entry["recovered_values"] = subset(entry["current_values"], desired)
            for kind in entry["recovered_values"]:
                for name in entry["recovered_values"][kind]:
                    entry["recovered_values"][kind][name] = read_parameter(material, kind, name)
            entry["status"] = "RECOVERED"
            recovered_count += 1
        except Exception as exc:
            rollback_errors = []
            for kind, name, old_value in reversed(changed):
                try:
                    write_parameter(material, kind, name, old_value)
                except Exception as rollback_exc:
                    rollback_errors.append(f"{kind}:{name}: {rollback_exc}")
            try:
                MATERIALS.update_material_instance(material)
                ASSETS.save_loaded_asset(material, False)
            except Exception as rollback_exc:
                rollback_errors.append(f"save rollback: {rollback_exc}")
            entry["status"] = "FAILED_ROLLED_BACK" if not rollback_errors else "FAILED_ROLLBACK_ERRORS"
            entry["write_error"] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
            entry["rollback_errors"] = rollback_errors
            raise

    report["recovered_count"] = recovered_count
    report["status"] = "RECOVERED"


def rollback_recovery(report: dict) -> None:
    apply_path = find_input_report("material-apply", required_explicit=True)
    apply_report = load_json(apply_path)
    if apply_report.get("mode") != "apply" or apply_report.get("status") != "RECOVERED":
        raise RuntimeError(f"Rollback source must be a successful apply report: {apply_path}")
    report["source_apply_report"] = str(apply_path)
    report["materials"] = []
    for source_entry in apply_report["materials"]:
        entry = {
            "material": source_entry["material"],
            "source_glb": source_entry["source_glb"],
            "source_sha256": source_entry["source_sha256"],
            "status": "PENDING",
        }
        report["materials"].append(entry)
        if source_entry.get("status") != "RECOVERED":
            raise RuntimeError(f"Apply report contains an unrecovered material: {entry['material']}")
        material = ASSETS.load_asset(entry["material"].split(".", 1)[0])
        if not isinstance(material, unreal.MaterialInstanceConstant):
            raise RuntimeError(f"Cannot reload for rollback: {entry['material']}")
        desired = source_entry["recovered_values"]
        before = source_entry["before_values"]
        for kind in ("scalar", "vector", "texture"):
            for name, expected_current in desired[kind].items():
                actual = read_parameter(material, kind, name)
                if not values_equal(actual, expected_current):
                    raise RuntimeError(
                        f"Material changed after apply; refusing rollback: {entry['material']} {kind}:{name}"
                    )
        changed = []
        try:
            for kind in ("scalar", "vector", "texture"):
                for name, old_value in before[kind].items():
                    current = read_parameter(material, kind, name)
                    write_parameter(material, kind, name, old_value)
                    changed.append((kind, name, current))
            MATERIALS.update_material_instance(material)
            if not ASSETS.save_loaded_asset(material, False):
                raise RuntimeError(f"Failed saving rollback: {entry['material']}")
            entry["status"] = "ROLLED_BACK"
        except Exception:
            rollback_errors = []
            for kind, name, current in reversed(changed):
                try:
                    write_parameter(material, kind, name, current)
                except Exception as exc:
                    rollback_errors.append(f"{kind}:{name}: {exc}")
            entry["rollback_restore_errors"] = rollback_errors
            entry["status"] = "FAILED"
            raise
    report["status"] = "ROLLED_BACK"


def validate_environment() -> None:
    actual_project = Path(unreal.Paths.project_dir()).resolve()
    if actual_project != PROJECT_DIR.resolve():
        raise RuntimeError(f"Refusing project {actual_project}; expected {PROJECT_DIR.resolve()}")
    version = str(unreal.SystemLibrary.get_engine_version())
    if not version.startswith("5.8"):
        raise RuntimeError(f"UE 5.8 is required, got {version}")


def main() -> None:
    if MODE not in {"dump", "apply", "rollback"}:
        raise ValueError(f"Unknown LUX_MATERIAL_RECOVERY_MODE: {MODE}")
    report_path = REPORT_DIR / f"material-{MODE}-{RUN_ID}.json"
    report = {
        "status": "STARTED",
        "mode": MODE,
        "run_id": RUN_ID,
        "project": str(PROJECT_DIR),
        "engine_version": str(unreal.SystemLibrary.get_engine_version()),
        "read_only": MODE == "dump",
        "failures": [],
        "missing_assets": [],
        "materials": [],
        "notes": [],
    }
    try:
        validate_environment()
        if MODE == "rollback":
            rollback_recovery(report)
        else:
            catalog = build_source_catalog()
            if MODE == "dump":
                entries, failures, missing, notes = collect_materials(catalog)
                report["materials"] = entries
                report["failures"] = failures
                report["missing_assets"] = missing
                report["notes"] = serialize_unmapped(notes)
                report["status"] = "DUMPED" if not failures else "DUMP_FAILED"
                if failures:
                    raise RuntimeError("Dump completed with mapping/read failures; apply is blocked")
            else:
                apply_recovery(report, catalog)
    except Exception as exc:
        if report["status"] in {"STARTED", "DUMPED"}:
            report["status"] = "FAILED" if MODE != "dump" else "DUMP_FAILED"
        report["fatal_error"] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        unreal.log_error(f"FOUR_REALMS_MATERIAL_{MODE.upper()}_FAILED report={report_path}: {exc}")
        raise

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"FOUR_REALMS_MATERIAL_{MODE.upper()} status={report['status']} report={report_path}")


if __name__ == "__main__":
    try:
        main()
    finally:
        if os.environ.get('LUX_RECOVERY_QUIT') == '1':
            unreal.SystemLibrary.quit_editor()
