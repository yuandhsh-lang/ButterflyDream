import json
import time
from pathlib import Path

import unreal


ROOT = Path(r'E:\紫萱2版')
OUT = ROOT / 'Evidence' / 'Unreal' / 'FourRealms_20261119'
SOURCE_DIR = ROOT / 'Assets' / 'LuxGenerated' / 'Optimized' / 'FX_20261119'
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
ASSET_TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
REPORT = {'status': 'RUNNING', 'started_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'imports': [], 'systems': [], 'errors': []}


def load_asset(path, expected_class):
    asset = ASSETS.load_asset(path)
    if not asset or not isinstance(asset, expected_class):
        raise RuntimeError(f'Missing required asset {path}')
    return asset


def import_fx_meshes():
    sources = sorted(SOURCE_DIR.glob('*_FX.glb'))
    sources += sorted((SOURCE_DIR.parent / 'HeroRestored_20261119').glob('*_FX.glb'))
    original_paths = {
        'Tunnel_Ring_FX': '/Game/LuxGenerated/Tunnel_T01/Tunnel_Ring',
        'Dream_Scale_Blade_FX': '/Game/LuxGenerated/Scale_T02/Dream_Scale_Blade',
        'Celestial_Spirit_Koi_FX': '/Game/LuxGenerated/Extra/Celestial_Spirit_Koi',
        'Butterfly_Body_FX': '/Game/LuxGenerated/Butterfly_B01/Butterfly_Body',
        'Wing_L_FX': '/Game/LuxGenerated/Butterfly_B01/Wing_L',
        'Wing_R_FX': '/Game/LuxGenerated/Butterfly_B01/Wing_R',
    }
    if {source.stem for source in sources} != set(original_paths):
        raise RuntimeError(f'Optimized source set is incomplete: {[str(source) for source in sources]}')
    for source in sources:
        name = source.stem
        record = {'source': str(source), 'source_sha256': __import__('hashlib').sha256(source.read_bytes()).hexdigest()}
        REPORT['imports'].append(record)
        asset_path = f'/Game/Optimized/{name}'
        task = unreal.AssetImportTask()
        task.set_editor_property('filename', str(source))
        task.set_editor_property('destination_path', '/Game/Optimized')
        task.set_editor_property('destination_name', name)
        task.set_editor_property('automated', True)
        task.set_editor_property('replace_existing', True)
        task.set_editor_property('save', True)
        ASSET_TOOLS.import_asset_tasks([task])
        optimized = load_asset(asset_path, unreal.StaticMesh)
        original = load_asset(original_paths[name], unreal.StaticMesh)
        for index, slot in enumerate(original.get_editor_property('static_materials')):
            optimized.set_material(index, slot.material_interface)
        settings = optimized.get_editor_property('nanite_settings')
        settings.set_editor_property('enabled', False)
        optimized.set_editor_property('nanite_settings', settings)
        if not ASSETS.save_loaded_asset(optimized, False):
            raise RuntimeError(f'Failed to save inherited material on {asset_path}')
        record.update({
            'asset': asset_path,
            'status': 'IMPORTED',
            'source_mesh': original.get_path_name(),
            'materials': [slot.material_interface.get_path_name() for slot in optimized.get_editor_property('static_materials')],
            'render_triangles': optimized.get_num_triangles(0),
        })


def create_systems():
    bridge = getattr(unreal, 'FourRealmNiagaraEditorBridge', None)
    if not bridge:
        raise RuntimeError('FourRealmNiagaraEditorBridge is unavailable; build the editor module with its editor-only dependencies')
    for method in ('create_wing_ribbon_system', 'create_gate_mesh_swarm_system'):
        if not callable(getattr(bridge, method, None)):
            raise RuntimeError(f'Niagara bridge method is unavailable: {method}')

    reports = {
        'NS_Butterfly_WingRibbon': OUT / 'niagara-wing-ribbon.json',
        'NS_Gate_MeshSwarm': OUT / 'niagara-gate-mesh-swarm.json',
    }
    wing_ok = bridge.create_wing_ribbon_system(str(reports['NS_Butterfly_WingRibbon']))
    wing_report = json.loads(reports['NS_Butterfly_WingRibbon'].read_text(encoding='utf-8'))
    REPORT['systems'].append({'asset': '/Game/FX/NS_Butterfly_WingRibbon', 'status': wing_report.get('status'), 'compile': wing_report.get('compile')})
    if not wing_ok:
        raise RuntimeError(f"Wing Niagara creation failed: {wing_report.get('errors')}")

    target = load_asset('/Game/LuxGenerated/Gate_G03/StarGate_OuterRing', unreal.StaticMesh)
    render = load_asset('/Game/Optimized/Dream_Scale_Blade_FX', unreal.StaticMesh)
    gate_ok = bridge.create_gate_mesh_swarm_system(target, render, str(reports['NS_Gate_MeshSwarm']))
    gate_report = json.loads(reports['NS_Gate_MeshSwarm'].read_text(encoding='utf-8'))
    REPORT['systems'].append({
        'asset': '/Game/FX/NS_Gate_MeshSwarm',
        'status': gate_report.get('status'),
        'compile': gate_report.get('compile'),
        'sampling_mesh': target.get_path_name(),
        'render_mesh': render.get_path_name(),
    })
    if not gate_ok:
        raise RuntimeError(f"Gate Niagara creation failed: {gate_report.get('errors')}")


def write_report():
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT['finished_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
    (OUT / 'fx-assets.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log(f"FOUR_REALM_FX status={REPORT['status']} report={OUT / 'fx-assets.json'}")


def main():
    try:
        if Path(unreal.Paths.project_dir()).resolve() != (ROOT / 'Unreal' / 'ButterflyDream').resolve():
            raise RuntimeError(f'Wrong project: {unreal.Paths.project_dir()}')
        if not str(unreal.SystemLibrary.get_engine_version()).startswith('5.8'):
            raise RuntimeError('UE 5.8 is required')
        import_fx_meshes()
        create_systems()
        REPORT['status'] = 'SUCCEEDED'
    except Exception as exc:
        import traceback
        REPORT['status'] = 'FAILED'
        REPORT['errors'].append(f'{exc}\n{traceback.format_exc()}')
        unreal.log_error(traceback.format_exc())
    finally:
        write_report()
        unreal.SystemLibrary.quit_editor()


if __name__ == '__main__':
    main()
