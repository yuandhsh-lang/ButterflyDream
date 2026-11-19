import json
import time
from pathlib import Path

import unreal


ROOT = Path(r'E:\紫萱2版')
OUT = ROOT / 'Evidence' / 'Unreal' / 'FourRealms_20261119' / 'static-audit.json'
MAPS = [
    '/Game/Maps/Lux_StarSeaDream',
    '/Game/Maps/Lux_InkCloudDream',
    '/Game/Maps/Lux_CrystalMirageDream',
    '/Game/Maps/Lux_TaijiAwakeningDream',
]
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
REPORT = {
    'status': 'RUNNING',
    'engine_version': unreal.SystemLibrary.get_engine_version(),
    'started_at': time.strftime('%Y-%m-%d %H:%M:%S'),
    'maps': [],
    'errors': [],
    'warnings': [],
}


def vec(value):
    return [round(float(value.x), 3), round(float(value.y), 3), round(float(value.z), 3)]


def rot(value):
    return [round(float(value.pitch), 3), round(float(value.yaw), 3), round(float(value.roll), 3)]


def prop(obj, name):
    return obj.get_editor_property(name)


def finish(status):
    REPORT['status'] = status
    REPORT['finished_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log(f'FOUR_REALM_AUDIT status={status} report={OUT}')
    unreal.SystemLibrary.quit_editor()


def audit_map(map_path):
    row = {'map': map_path, 'gates': [], 'errors': [], 'warnings': []}
    if not LEVELS.load_level(map_path):
        raise RuntimeError(f'Could not load {map_path}')
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    starts = [actor for actor in actors if isinstance(actor, unreal.PlayerStart)]
    row['player_starts'] = [{'label': a.get_actor_label(), 'location': vec(a.get_actor_location()), 'rotation': rot(a.get_actor_rotation())} for a in starts]
    if len(starts) != 1:
        row['errors'].append(f'Expected exactly one PlayerStart, found {len(starts)}')

    gates = [actor for actor in actors if isinstance(actor, unreal.ButterflyDreamGateActor)]
    if len(gates) != 2:
        row['errors'].append(f'Expected two dream gates, found {len(gates)}')
    for gate in gates:
        target = str(prop(gate, 'target_map_package_name'))
        gate_row = {
            'label': gate.get_actor_label(),
            'title': str(prop(gate, 'gate_title')),
            'target': target,
            'target_exists': ASSETS.does_asset_exist(target),
            'location': vec(gate.get_actor_location()),
            'rotation': rot(gate.get_actor_rotation()),
            'scale': vec(gate.get_actor_scale3d()),
            'box_collision_components': len(gate.get_components_by_class(unreal.BoxComponent)),
            'niagara_components': len(gate.get_components_by_class(unreal.NiagaraComponent)),
        }
        if 'F06_SakuraDream' in target:
            gate_row['errors'] = ['F06 target is forbidden']
            row['errors'].append(f'{gate.get_actor_label()} still targets F06')
        if not gate_row['target_exists']:
            row['errors'].append(f'{gate.get_actor_label()} target does not exist: {target}')
        if gate_row['box_collision_components'] == 0:
            row['errors'].append(f'{gate.get_actor_label()} has no simplified collision boxes')
        if gate_row['niagara_components'] == 0:
            row['errors'].append(f'{gate.get_actor_label()} has no Niagara component')
        niagara_assets = []
        for component in gate.get_components_by_class(unreal.NiagaraComponent):
            system = component.get_asset()
            niagara_assets.append(system.get_path_name() if system else None)
            if not isinstance(system, unreal.NiagaraSystem):
                row['errors'].append(f'{gate.get_actor_label()}/{component.get_name()} has no NiagaraSystem')
        gate_row['niagara_assets'] = niagara_assets
        row['gates'].append(gate_row)

    mesh_count = 0
    niagara_count = 0
    sky_rows = []
    nanite_meshes = set()
    rendered_triangles = 0
    for actor in actors:
        niagara_count += len(actor.get_components_by_class(unreal.NiagaraComponent))
        for comp in actor.get_components_by_class(unreal.StaticMeshComponent):
            mesh = comp.get_editor_property('static_mesh')
            if not mesh:
                continue
            mesh_count += 1
            rendered_triangles += mesh.get_num_triangles(0)
            path = mesh.get_path_name()
            if '/Game/ThirdParty/F06' in path or 'F06_SakuraDream' in path:
                row['errors'].append(f'Forbidden F06 mesh reference: {path}')
            if mesh.get_editor_property('nanite_settings').get_editor_property('enabled'):
                nanite_meshes.add(path)
        if actor.get_actor_label().endswith('_SkyDome'):
            smc = actor.static_mesh_component
            material = smc.get_material(0) if smc else None
            sky_rows.append({
                'actor': actor.get_actor_label(),
                'material': material.get_path_name() if material else None,
                'is_sky': bool(material and material.get_editor_property('is_sky')),
            })
    row['static_mesh_components'] = mesh_count
    row['base_mesh_triangles'] = rendered_triangles
    row['niagara_components'] = niagara_count
    row['sky'] = sky_rows
    if not sky_rows:
        row['errors'].append('No _SkyDome actor found')
    for sky in sky_rows:
        if not sky['is_sky']:
            row['errors'].append(f'Sky material is not marked IsSky: {sky["actor"]}')
    row['nanite_enabled_meshes'] = sorted(nanite_meshes)
    if niagara_count == 0:
        row['errors'].append('No Niagara components found in map')
    return row


try:
    if ASSETS.does_asset_exist('/Game/Maps/F06_SakuraDream'):
        REPORT['errors'].append('F06 map still exists in active Content')
    for map_path in MAPS:
        if not ASSETS.does_asset_exist(map_path):
            REPORT['errors'].append(f'Missing required map: {map_path}')
            continue
        try:
            REPORT['maps'].append(audit_map(map_path))
        except Exception as exc:
            REPORT['errors'].append(f'{map_path}: {exc}')
    for row in REPORT['maps']:
        REPORT['errors'].extend(f'{row["map"]}: {message}' for message in row['errors'])
        REPORT['warnings'].extend(f'{row["map"]}: {message}' for message in row['warnings'])
    finish('SUCCEEDED' if not REPORT['errors'] else 'FAILED')
except Exception as exc:
    REPORT['errors'].append(str(exc))
    finish('FAILED')
