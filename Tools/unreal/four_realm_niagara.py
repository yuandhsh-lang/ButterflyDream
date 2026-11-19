"""Niagara authoring and runtime binding for create-four-realm-fx.py.

The stock UE 5.8 C++ Niagara authoring functions are not Python UFUNCTIONs.
An editor-only bridge can be supplied to main(); it must implement the methods in
REQUIRED_BRIDGE_METHODS using UNiagaraSystemFactoryNew::InitializeSystem,
FNiagaraEditorUtilities::AddEmitterToSystem, the real stack graph, and
UNiagaraSystem::RequestCompile. No runtime NiagaraEditor dependency is allowed.
"""

from __future__ import annotations

from typing import Any

import unreal


RIBBON_TEMPLATE = "/Niagara/DefaultAssets/Templates/Emitters/LocationBasedRibbon"
MESH_TEMPLATE = "/Niagara/DefaultAssets/Templates/Emitters/UpwardMeshBurst"
SAMPLE_STATIC_MESH = "/Niagara/Modules/Spawn/MeshInterface/SampleStaticMesh"
DEFAULT_RIBBON_MATERIAL = "/Niagara/DefaultAssets/DefaultRIbbonMaterial"
RIBBON_SYSTEM = "/Game/FX/NS_Butterfly_WingRibbon"
GATE_SYSTEM = "/Game/FX/NS_Gate_MeshSwarm"

REQUIRED_BRIDGE_METHODS = (
    "create_system_from_emitter",
    "ensure_user_parameter",
    "find_module",
    "add_module",
    "set_expression_input",
    "set_static_mesh_sampler_input",
    "add_set_parameters",
    "configure_mesh_renderer",
    "configure_ribbon_renderer",
    "get_system_evidence",
    "request_compile",
    "wait_for_compilation_complete",
    "get_compile_state",
)

SUCCESSFUL_COMPILE_STATES = {
    "uptodate",
    "uptodatewithwarnings",
    "computeuptodatewithwarnings",
}


class NiagaraBridgeError(RuntimeError):
    pass


def _callable(owner: Any, name: str) -> Any:
    value = getattr(owner, name, None)
    return value if callable(value) else None


def probe_native_niagara_apis(asset_subsystem: Any) -> dict[str, Any]:
    factory = getattr(unreal, "NiagaraSystemFactoryNew", None)
    editor_utilities = getattr(unreal, "NiagaraEditorUtilities", None)
    external = getattr(unreal, "NiagaraExternalEditUtilities", None)
    system_class = getattr(unreal, "NiagaraSystem", None)
    component_class = getattr(unreal, "NiagaraComponent", None)
    external_methods = (
        "create_niagara_system",
        "add_emitter",
        "add_module",
        "add_set_parameters_module",
        "set_stack_input_data",
        "get_system_summary",
        "get_emitter_topology",
    )
    assets = {}
    for path, expected_class in (
        (RIBBON_TEMPLATE, unreal.NiagaraEmitter),
        (MESH_TEMPLATE, unreal.NiagaraEmitter),
        (SAMPLE_STATIC_MESH, unreal.NiagaraScript),
        (DEFAULT_RIBBON_MATERIAL, unreal.MaterialInterface),
    ):
        record: dict[str, Any] = {"exists": bool(asset_subsystem.does_asset_exist(path))}
        if record["exists"]:
            asset = asset_subsystem.load_asset(path)
            record["loaded_type"] = asset.get_class().get_name() if asset else None
            record["expected_type"] = expected_class.get_name()
            record["type_valid"] = isinstance(asset, expected_class)
        assets[path] = record
    return {
        "assets": assets,
        "UNiagaraSystemFactoryNew": {
            "class_visible": factory is not None,
            "initialize_system_callable": _callable(factory, "initialize_system") is not None,
        },
        "FNiagaraEditorUtilities": {
            "class_visible": editor_utilities is not None,
            "add_emitter_to_system_callable": _callable(editor_utilities, "add_emitter_to_system") is not None,
        },
        "UNiagaraExternalEditUtilities": {
            "class_visible": external is not None,
            "callable_methods": [name for name in external_methods if _callable(external, name)],
            "missing_methods": [name for name in external_methods if not _callable(external, name)],
        },
        "UNiagaraSystem": {
            "request_compile_callable": _callable(system_class, "request_compile") is not None,
            "wait_for_compilation_complete_callable": _callable(system_class, "wait_for_compilation_complete") is not None,
        },
        "UNiagaraComponent": {
            name: _callable(component_class, name) is not None
            for name in ("set_variable_float", "set_variable_vec3", "set_variable_static_mesh")
        },
        "injected_bridge_class_visible": getattr(unreal, "FourRealmNiagaraEditorBridge", None) is not None,
        "note": (
            "C++ symbols and UCLASS visibility do not prove Python callability. "
            "The stock UE 5.8 InitializeSystem, AddEmitterToSystem and RequestCompile declarations are not UFUNCTIONs."
        ),
    }


def discover_injected_bridge() -> Any:
    candidate = getattr(unreal, "FourRealmNiagaraEditorBridge", None)
    if candidate is not None and all(_callable(candidate, name) for name in REQUIRED_BRIDGE_METHODS):
        return candidate
    return None


def validate_bridge(bridge: Any) -> None:
    if bridge is None:
        raise NiagaraBridgeError(
            "No editor-only Niagara bridge is available. Systems were not created and no compile success is claimed. "
            "Supply main(niagara_bridge=...) or expose unreal.FourRealmNiagaraEditorBridge with every required method."
        )
    missing = [name for name in REQUIRED_BRIDGE_METHODS if not _callable(bridge, name)]
    if missing:
        raise NiagaraBridgeError(f"Niagara bridge is incomplete; missing callable methods: {missing}")


def _ensure_parameters(bridge: Any, system: Any, specifications: list[dict[str, Any]]) -> dict[str, Any]:
    result = {}
    for specification in specifications:
        name = specification["name"]
        disposition = bridge.ensure_user_parameter(
            system,
            name,
            specification["type"],
            specification.get("default"),
        )
        if disposition not in {"added", "reused"}:
            raise NiagaraBridgeError(f"User.{name} was neither added nor reused: {disposition!r}")
        result[f"User.{name}"] = {
            "type": specification["type"],
            "default": specification.get("default"),
            "disposition": disposition,
        }
    return result


def _require_module(bridge: Any, system: Any, emitter: str, script: str, **query: Any) -> str:
    module = bridge.find_module(system, emitter, script, **query)
    if not module:
        raise NiagaraBridgeError(f"Required module was not found: {emitter}/{script}/{query}")
    return module


def _compile(bridge: Any, system: Any) -> dict[str, Any]:
    accepted = bridge.request_compile(system, True)
    if accepted is not True:
        raise NiagaraBridgeError(f"UNiagaraSystem::RequestCompile(force=True) was not accepted: {accepted!r}")
    bridge.wait_for_compilation_complete(system)
    state = bridge.get_compile_state(system)
    if not isinstance(state, dict):
        raise NiagaraBridgeError(f"Compile state must be a dictionary, got {type(state).__name__}")
    aggregate = str(state.get("aggregate_status", "Unknown"))
    normalized = aggregate.replace("_", "").replace(" ", "").lower()
    if normalized not in SUCCESSFUL_COMPILE_STATES or state.get("has_errors"):
        raise NiagaraBridgeError(f"Niagara compilation did not succeed: {state}")
    return state


def _validate_common(evidence: dict[str, Any], template: str, expected_renderer: str) -> None:
    if evidence.get("template_emitter") != template:
        raise NiagaraBridgeError(f"Template provenance mismatch: {evidence.get('template_emitter')!r} != {template}")
    native_calls = evidence.get("native_calls", {})
    for call in ("InitializeSystem", "AddEmitterToSystem", "RequestCompile"):
        if native_calls.get(call) is not True:
            raise NiagaraBridgeError(f"Missing native-call evidence for {call}: {native_calls}")
    renderers = evidence.get("renderers", [])
    if not any(expected_renderer in str(renderer.get("type", "")) for renderer in renderers):
        raise NiagaraBridgeError(f"Required renderer {expected_renderer} is absent: {renderers}")


def _validate_parameters(evidence: dict[str, Any], expected: dict[str, Any]) -> None:
    actual = evidence.get("parameters", {})
    for runtime_name, specification in expected.items():
        if runtime_name not in actual:
            raise NiagaraBridgeError(f"Runtime parameter {runtime_name} is absent from compiled-system evidence")
        if actual[runtime_name].get("type") != specification["type"]:
            raise NiagaraBridgeError(
                f"Runtime parameter {runtime_name} has type {actual[runtime_name].get('type')!r}; "
                f"expected {specification['type']!r}"
            )


def _module_with_asset(evidence: dict[str, Any], asset_path: str) -> dict[str, Any]:
    matches = [module for module in evidence.get("modules", []) if module.get("asset_path") == asset_path]
    if len(matches) != 1:
        raise NiagaraBridgeError(f"Expected exactly one stack module using {asset_path}: {matches}")
    return matches[0]


def _assignment(evidence: dict[str, Any], module_name: str, target: str) -> dict[str, Any]:
    for module in evidence.get("modules", []):
        if module.get("name") == module_name and module.get("is_set_parameters"):
            assignments = module.get("assignments", {})
            if target in assignments:
                return assignments[target]
    raise NiagaraBridgeError(f"Missing assignment evidence: {module_name} -> {target}")


def _validate_ribbon(evidence: dict[str, Any], material_path: str, parameters: dict[str, Any]) -> None:
    _validate_common(evidence, RIBBON_TEMPLATE, "NiagaraRibbonRendererProperties")
    _validate_parameters(evidence, parameters)
    initialize = _module_with_asset(evidence, "/Niagara/Modules/Spawn/Initialization/V2/InitializeRibbon")
    inputs = initialize.get("inputs", {})
    color_expression = str(inputs.get("Color", {}).get("value", ""))
    width_expression = str(inputs.get("Ribbon Width", {}).get("value", ""))
    for token in ("User.Color", "User.Boost"):
        if token not in color_expression:
            raise NiagaraBridgeError(f"Ribbon Color expression is not connected to {token}: {color_expression}")
    for token in ("User.Width", "User.Boost", "User.WingBeat"):
        if token not in width_expression:
            raise NiagaraBridgeError(f"Ribbon Width expression is not connected to {token}: {width_expression}")
    if not any(material_path in renderer.get("materials", []) for renderer in evidence.get("renderers", [])):
        raise NiagaraBridgeError(f"Ribbon renderer does not reference the local usage-enabled material {material_path}")


def _validate_gate(evidence: dict[str, Any], mesh_path: str, parameters: dict[str, Any]) -> None:
    _validate_common(evidence, MESH_TEMPLATE, "NiagaraMeshRendererProperties")
    _validate_parameters(evidence, parameters)
    sample = _module_with_asset(evidence, SAMPLE_STATIC_MESH)
    static_mesh_input = sample.get("inputs", {}).get("StaticMesh", {})
    if static_mesh_input.get("data_interface") != "NiagaraDataInterfaceStaticMesh":
        raise NiagaraBridgeError(f"SampleStaticMesh is not backed by NiagaraDataInterfaceStaticMesh: {static_mesh_input}")
    if static_mesh_input.get("default_mesh") != mesh_path:
        raise NiagaraBridgeError(f"SampleStaticMesh default mesh is not the derived low mesh: {static_mesh_input}")
    if static_mesh_input.get("mesh_parameter_binding") != "User.TargetMesh":
        raise NiagaraBridgeError(f"SampleStaticMesh is not runtime-bindable through User.TargetMesh: {static_mesh_input}")
    if static_mesh_input.get("lod_index") != 2:
        raise NiagaraBridgeError(f"SampleStaticMesh must sample LOD2, got {static_mesh_input.get('lod_index')}")

    target = _assignment(evidence, "CaptureReformTargets", "Particles.TargetPosition")
    scatter = _assignment(evidence, "CaptureReformTargets", "Particles.ScatterPosition")
    if target.get("mode") != "linked" or target.get("value") != "Particles.Module.MeshPosition":
        raise NiagaraBridgeError(f"MeshPosition is not captured as TargetPosition: {target}")
    if scatter.get("value") != "Particles.Position":
        raise NiagaraBridgeError(f"Template spawn position is not captured as ScatterPosition: {scatter}")
    reform = _assignment(evidence, "ReformFromOpenAlphaResonance", "Particles.Position")
    expression = str(reform.get("value", ""))
    for token in ("Particles.TargetPosition", "Particles.ScatterPosition", "User.OpenAlpha", "User.Resonance"):
        if token not in expression:
            raise NiagaraBridgeError(f"Reform expression is missing {token}: {expression}")
    if not any(
        mesh_path in renderer.get("meshes", []) and renderer.get("forced_lod") == 2
        for renderer in evidence.get("renderers", [])
    ):
        raise NiagaraBridgeError("Mesh Renderer does not reference the derived mesh with forced LOD2")


def _finish_system(bridge: Any, asset_subsystem: Any, system: Any) -> dict[str, Any]:
    compile_state = _compile(bridge, system)
    if not asset_subsystem.save_loaded_asset(system, False):
        raise NiagaraBridgeError(f"Failed to save {system.get_path_name()} after successful compilation")
    evidence = bridge.get_system_evidence(system)
    if not isinstance(evidence, dict):
        raise NiagaraBridgeError("get_system_evidence must return a JSON-serializable dictionary")
    evidence["compile"] = compile_state
    evidence["asset_path"] = system.get_path_name().split(".")[0]
    return evidence


def author_ribbon_system(bridge: Any, asset_subsystem: Any, ribbon_material: Any) -> dict[str, Any]:
    system = bridge.create_system_from_emitter(RIBBON_SYSTEM, RIBBON_TEMPLATE, "ButterflyWingRibbon")
    if not isinstance(system, unreal.NiagaraSystem):
        raise NiagaraBridgeError(f"Ribbon creation did not return UNiagaraSystem: {system!r}")
    parameters = _ensure_parameters(
        bridge,
        system,
        [
            {"name": "Boost", "type": "float", "default": 0.0},
            {"name": "WingBeat", "type": "float", "default": 4.0},
            {"name": "Color", "type": "vec3", "default": [0.45, 0.78, 1.0]},
            {"name": "Width", "type": "float", "default": 12.0},
        ],
    )
    emitter = "ButterflyWingRibbon"
    script = "ParticleSpawnScript"
    initialize = _require_module(bridge, system, emitter, script, name_contains="InitializeRibbon")
    color_expression = "float4(User.Color * (1.0 + 0.25 * max(User.Boost, 0.0)), 1.0)"
    width_expression = (
        "max(0.0, User.Width * (1.0 + 0.25 * max(User.Boost, 0.0) + "
        "0.15 * sin(Engine.Time * 6.2831853 * max(User.WingBeat, 0.0))))"
    )
    bridge.set_expression_input(system, emitter, script, initialize, "Color", color_expression)
    bridge.set_expression_input(system, emitter, script, initialize, "Ribbon Width", width_expression)
    bridge.configure_ribbon_renderer(system, emitter, ribbon_material)
    evidence = _finish_system(bridge, asset_subsystem, system)
    _validate_ribbon(evidence, ribbon_material.get_path_name().split(".")[0], parameters)
    evidence["parameter_wiring"] = {
        "User.Color": f"{initialize}.Color <- {color_expression}",
        "User.Boost": "Color intensity and Ribbon Width gain",
        "User.WingBeat": f"{initialize}.Ribbon Width <- {width_expression}",
        "User.Width": f"{initialize}.Ribbon Width <- {width_expression}",
    }
    evidence["reuse_for_tunnel"] = True
    return evidence


def author_gate_system(bridge: Any, asset_subsystem: Any, gate_mesh: Any) -> dict[str, Any]:
    mesh_path = gate_mesh.get_path_name().split(".")[0]
    system = bridge.create_system_from_emitter(GATE_SYSTEM, MESH_TEMPLATE, "GateMeshSwarm")
    if not isinstance(system, unreal.NiagaraSystem):
        raise NiagaraBridgeError(f"Gate creation did not return UNiagaraSystem: {system!r}")
    parameters = _ensure_parameters(
        bridge,
        system,
        [
            {"name": "TargetMesh", "type": "static_mesh", "default": mesh_path},
            {"name": "OpenAlpha", "type": "float", "default": 0.0},
            {"name": "Resonance", "type": "float", "default": 0.0},
            {"name": "DisperseRadius", "type": "float", "default": 250.0},
        ],
    )
    emitter = "GateMeshSwarm"
    spawn = "ParticleSpawnScript"
    update = "ParticleUpdateScript"
    initialize = _require_module(bridge, system, emitter, spawn, name_contains="InitializeParticle")
    sample = bridge.find_module(system, emitter, spawn, module_asset_path=SAMPLE_STATIC_MESH)
    if not sample:
        sample = bridge.add_module(system, emitter, spawn, SAMPLE_STATIC_MESH, after_module=initialize)
    if not sample:
        raise NiagaraBridgeError("Failed to add SampleStaticMesh to ParticleSpawnScript")
    bridge.set_static_mesh_sampler_input(
        system,
        emitter,
        spawn,
        sample,
        "StaticMesh",
        gate_mesh,
        "User.TargetMesh",
        2,
    )
    bridge.add_set_parameters(
        system,
        emitter,
        spawn,
        "CaptureReformTargets",
        after_module=sample,
        entries=[
            {
                "name": "Particles.TargetPosition",
                "type": "position",
                "mode": "linked",
                "value": "Particles.Module.MeshPosition",
            },
            {
                "name": "Particles.ScatterPosition",
                "type": "position",
                "mode": "linked",
                "value": "Particles.Position",
            },
        ],
    )
    solver = _require_module(bridge, system, emitter, update, name_contains="SolveForcesAndVelocity")
    reform_expression = (
        "lerp(Particles.TargetPosition, Particles.TargetPosition + "
        "normalize(Particles.ScatterPosition - Particles.TargetPosition + float3(0.0001, 0.0, 0.0)) * "
        "max(User.DisperseRadius, 0.0), saturate(User.OpenAlpha) * (1.0 - saturate(User.Resonance)))"
    )
    bridge.add_set_parameters(
        system,
        emitter,
        update,
        "ReformFromOpenAlphaResonance",
        after_module=solver,
        entries=[
            {
                "name": "Particles.Position",
                "type": "position",
                "mode": "expression",
                "value": reform_expression,
            }
        ],
    )
    bridge.configure_mesh_renderer(system, emitter, gate_mesh, 2)
    evidence = _finish_system(bridge, asset_subsystem, system)
    _validate_gate(evidence, mesh_path, parameters)
    evidence["parameter_wiring"] = {
        "User.TargetMesh": f"{sample}.StaticMesh -> NiagaraDataInterfaceStaticMesh.MeshParameterBinding; default={mesh_path}; LOD=2",
        "SampleStaticMesh": "Particles.Module.MeshPosition -> CaptureReformTargets.Particles.TargetPosition",
        "User.OpenAlpha": "0 keeps the sampled gate surface; 1 selects the dispersed offset",
        "User.Resonance": "1 suppresses dispersion and returns particles to TargetPosition",
        "User.DisperseRadius": "Radial offset in centimetres from each sampled target",
        "Particles.Position": reform_expression,
    }
    return evidence


def bind_ribbon_component(
    component: Any,
    boost: float,
    wing_beat_hz: float,
    color_rgb: Any,
    width: float,
) -> None:
    if not isinstance(component, unreal.NiagaraComponent):
        raise TypeError("bind_ribbon_component requires UNiagaraComponent")
    component.set_variable_float("User.Boost", float(boost))
    component.set_variable_float("User.WingBeat", float(wing_beat_hz))
    color = color_rgb if isinstance(color_rgb, unreal.Vector) else unreal.Vector(*color_rgb)
    component.set_variable_vec3("User.Color", color)
    component.set_variable_float("User.Width", float(width))


def bind_gate_component(
    component: Any,
    target_mesh: Any,
    open_alpha: float,
    resonance: float,
    disperse_radius: float = 250.0,
) -> None:
    if not isinstance(component, unreal.NiagaraComponent):
        raise TypeError("bind_gate_component requires UNiagaraComponent")
    if not isinstance(target_mesh, unreal.StaticMesh):
        raise TypeError("bind_gate_component requires a UStaticMesh target")
    component.set_variable_static_mesh("User.TargetMesh", target_mesh)
    component.set_variable_float("User.OpenAlpha", float(open_alpha))
    component.set_variable_float("User.Resonance", float(resonance))
    component.set_variable_float("User.DisperseRadius", float(disperse_radius))
