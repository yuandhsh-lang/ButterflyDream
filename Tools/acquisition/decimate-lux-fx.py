import hashlib
import json
import sys
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[2]
args = sys.argv[sys.argv.index('--') + 1:]
if len(args) not in (1, 2):
    raise ValueError('Usage: blender --python decimate-lux-fx.py -- <new-output-directory> [fx|hero]')
destination = Path(args[0]).resolve()
profile = args[1] if len(args) == 2 else 'fx'
if profile not in ('fx', 'hero'):
    raise ValueError(f'Unknown profile: {profile}')
if destination.exists():
    raise FileExistsError(f'Refusing to overwrite existing {profile} output: {destination}')
destination.mkdir(parents=True)

assets = [
    ('Tunnel_Ring_FX', ROOT / 'Assets/LuxGenerated/V2_Gates/Ready/Tunnel_Ring.glb', 0.05),
    ('Dream_Scale_Blade_FX', ROOT / 'Assets/LuxGenerated/Ready/Dream_Scale_Blade.glb', 0.05),
    ('Celestial_Spirit_Koi_FX', ROOT / 'Assets/LuxGenerated/V2_Extra/Ready/Celestial_Spirit_Koi.glb', 0.05),
]
if profile == 'hero':
    source_root = ROOT / 'Assets/LuxGenerated/ReconstructedButterfly_20261119/Ready'
    assets = [
        ('Butterfly_Body_FX', source_root / 'Butterfly_Body.glb', 0.35),
        ('Wing_L_FX', source_root / 'Wing_L.glb', 0.10),
        ('Wing_R_FX', source_root / 'Wing_R.glb', 0.10),
    ]


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def triangle_count():
    total = 0
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            obj.data.calc_loop_triangles()
            total += len(obj.data.loop_triangles)
    return total


report = {'status': 'RUNNING', 'assets': [], 'errors': []}
for name, source, ratio in assets:
    row = {'name': name, 'source': str(source), 'ratio': ratio, 'status': 'RUNNING'}
    report['assets'].append(row)
    try:
        if not source.is_file():
            raise FileNotFoundError(source)
        row['source_sha256'] = sha256(source)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(source))
        source_triangles = triangle_count()
        if source_triangles == 0:
            raise RuntimeError('Source imported no triangles')
        row['source_triangles'] = source_triangles
        for obj in list(bpy.context.scene.objects):
            if obj.type != 'MESH':
                continue
            if obj.data.users > 1:
                obj.data = obj.data.copy()
            modifier = obj.modifiers.new(name='FX_Decimate', type='DECIMATE')
            modifier.ratio = ratio
            modifier.use_collapse_triangulate = True
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.modifier_apply(modifier=modifier.name)
            obj.select_set(False)
        output_triangles = triangle_count()
        if output_triangles == 0:
            raise RuntimeError('Decimation removed all geometry')
        row['output_triangles'] = output_triangles
        output = destination / f'{name}.glb'
        for obj in bpy.context.scene.objects:
            obj.select_set(obj.type == 'MESH')
        kwargs = {
            'filepath': str(output),
            'export_format': 'GLB',
            'use_selection': True,
            'export_apply': True,
            'export_materials': 'EXPORT',
            'export_yup': True,
            'export_cameras': False,
            'export_lights': False,
            'export_animations': False,
            'export_extras': True,
        }
        available = set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
        bpy.ops.export_scene.gltf(**{key: value for key, value in kwargs.items() if key in available})
        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError('GLB export produced no file')
        row['output'] = str(output)
        row['output_sha256'] = sha256(output)
        row['status'] = 'SUCCEEDED'
    except Exception as exc:
        import traceback
        row['status'] = 'FAILED'
        row['error'] = str(exc)
        row['traceback'] = traceback.format_exc()
        report['errors'].append(f'{name}: {exc}')

report['status'] = 'FAILED' if report['errors'] else 'SUCCEEDED'
report['profile'] = profile
report_path = destination / f'{profile}-decimation-report.json'
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"{profile.upper()}_DECIMATION_DONE status={report['status']} report={report_path}", flush=True)
if report['errors']:
    raise RuntimeError('One or more FX meshes failed; inspect the report before using them')
