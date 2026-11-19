import json
import math
import time
from pathlib import Path

import unreal
import four_realm_scene_utils as scene


ROOT = Path(r'E:\紫萱2版')
PROJECT = ROOT / 'Unreal' / 'ButterflyDream'
BACKUP = ROOT / 'Evidence' / 'Unreal' / 'Backups' / '20261119_1135_PreContinuation'
REPORT_DIR = ROOT / 'Evidence' / 'Unreal' / 'FourRealms_20261119'
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
REPORT = {'status': 'RUNNING', 'started_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'maps': [], 'errors': []}
MAPS = [
    '/Game/Maps/Lux_StarSeaDream',
    '/Game/Maps/Lux_InkCloudDream',
    '/Game/Maps/Lux_CrystalMirageDream',
    '/Game/Maps/Lux_TaijiAwakeningDream',
]


def vector_list(value):
    return [round(float(value.x), 3), round(float(value.y), 3), round(float(value.z), 3)]


def clear_map(map_path):
    if not LEVELS.load_level(map_path):
        raise RuntimeError(f'Could not load required map {map_path}')
    for actor in list(ACTORS.get_all_level_actors()):
        ACTORS.destroy_actor(actor)


def save_map(map_path):
    if not LEVELS.save_current_level():
        raise RuntimeError(f'Failed to save {map_path}')


def add_map_report(map_path, spawn, gates):
    REPORT['maps'].append({
        'map': map_path,
        'player_start': vector_list(spawn),
        'actors': len(ACTORS.get_all_level_actors()),
        'gates': [{
            'label': item['actor'].get_actor_label(),
            'target': item['actor'].get_editor_property('target_map_package_name'),
            'location': vector_list(item['actor'].get_actor_location()),
            'scale': item['scale'],
            'aperture': item['actor'].get_editor_property('portal_aperture_half_width'),
            'exit_local_y': item['actor'].get_tunnel_exit_distance(),
        } for item in gates],
    })


def build_starsea():
    path = MAPS[0]
    clear_map(path)
    sky = scene.prepare_sky_material('/Game/LuxGenerated/Materials/M_Lux_StarSeaSkyDome')
    scene.spawn_sky('Lux_StarSea', sky)
    scene.spawn_water('Lux_StarSea_OpenWater', '/Game/LuxGenerated/Materials/M_Lux_StarWater', scene.vec(0, 1200, -80), scene.vec(2400, 2400, 1))
    scene.configure_atmosphere(
        'Lux_StarSea', sky, scene.rot(pitch=-24, yaw=48), 2.2, scene.color(0.82, 0.90, 1.0), 1.2,
        scene.color(0.035, 0.06, 0.11), 0.00028, 6000, -0.15, 0.20, 35.0)
    scene.spawn_static('Lux_StarSea_DistantPavilion', 'pavilion', scene.vec(-1050, 3400, -30), 160, target_height=1800, base_collision=True)
    scene.spawn_static('Lux_StarSea_DiagonalBridge', 'bridge', scene.vec(100, 400, 20), -34, target_span=950, base_collision=True)
    scene.spawn_static('Lux_StarSea_WestGuardian', 'guardian', scene.vec(-1250, 650, 30), 145, target_height=420, base_collision=True)
    scene.spawn_static('Lux_StarSea_EastPillar', 'pillar', scene.vec(1150, 1900, -50), -35, target_height=540, base_collision=True)
    for index, (x, y, z, span) in enumerate(((-850, -500, -60, 320), (650, 250, -55, 260), (-500, 1900, -40, 340), (1000, 3000, -30, 280))):
        scene.spawn_static(f'Lux_StarSea_Islet_{index}', 'lotus', scene.vec(x, y, z), index * 37, target_span=span, base_collision=True)
    scene.spawn_point('Lux_StarSea_PavilionWarmKey', scene.vec(-950, 2900, 900), 95, 2300, scene.color(1.0, 0.78, 0.46), True)
    scene.spawn_point('Lux_StarSea_WaterCyanFill', scene.vec(600, 300, 330), 30, 1300, scene.color(0.38, 0.82, 1.0))
    gates = [
        scene.configure_gate('Lux_StarSea_ForwardGate', '第一仙门 ｜ 太虚星轨（通往水墨云海）', MAPS[1], scene.vec(1500, 1300, 120), -35, 420, 17, resonance_distance=1300),
        scene.configure_gate('Lux_StarSea_ReturnGate', '归返仙门 ｜ 太极归途', MAPS[3], scene.vec(-1400, -400, 80), 35, 330, 17, resonance_distance=1000),
    ]
    spawn = scene.vec(-600, -1600, 350)
    scene.finalize_map(path, spawn, scene.rot(pitch=1.0, yaw=55))
    save_map(path)
    add_map_report(path, spawn, gates)


def build_inkcloud():
    path = MAPS[1]
    clear_map(path)
    sky = scene.create_custom_sky('M_InkCloud_ValleySky', '''
        float3 d = normalize(Dir);
        float h = saturate(d.z * 0.5 + 0.5);
        float horizon = exp(-abs(d.z) * 9.0);
        float3 base = lerp(float3(0.045, 0.052, 0.048), float3(0.12, 0.15, 0.16), h);
        return base + float3(0.18, 0.115, 0.055) * horizon;
    ''')
    scene.spawn_sky('Lux_InkCloud', sky)
    scene.configure_atmosphere(
        'Lux_InkCloud', sky, scene.rot(pitch=-28, yaw=32), 2.0, scene.color(1.0, 0.88, 0.72), 0.9,
        scene.color(0.07, 0.075, 0.065), 0.00075, 3200, -0.10, 0.12, 0.0)
    scene.spawn_static('Lux_InkCloud_WestMountain', 'mountain', scene.vec(-1250, 1150, -250), -32, target_height=2050, base_collision=True)
    scene.spawn_static('Lux_InkCloud_EastMountain', 'mountain', scene.vec(1350, 2350, 150), 142, target_height=2300, base_collision=True)
    scene.spawn_static('Lux_InkCloud_FarSanctuary', 'mountain', scene.vec(-350, 4400, 450), 185, target_height=2600, base_collision=True)
    scene.spawn_static('Lux_InkCloud_GuqinCrossing', 'guqin', scene.vec(0, 450, 80), 82, target_span=1200, base_collision=True)
    scene.spawn_static('Lux_InkCloud_CliffPillar', 'pillar', scene.vec(-650, 900, 350), 30, target_height=460, base_collision=True)
    scene.spawn_static('Lux_InkCloud_RidgePillar', 'pillar', scene.vec(700, 1850, 650), -40, target_height=510, base_collision=True)
    scene.spawn_point('Lux_InkCloud_GuqinWarmth', scene.vec(0, 420, 320), 38, 1350, scene.color(1.0, 0.76, 0.40), True)
    scene.spawn_point('Lux_InkCloud_FarAmber', scene.vec(-350, 3800, 1600), 70, 2400, scene.color(1.0, 0.68, 0.32), True)
    gates = [
        scene.configure_gate('Lux_InkCloud_ForwardGate', '第二仙门 ｜ 水墨涟漪（通往琉璃浮岛）', MAPS[2], scene.vec(0, 2300, 600), 0, 480, 21.5, 'ink_portal', 1200),
        scene.configure_gate('Lux_InkCloud_ReturnGate', '归返仙门 ｜ 星海来处', MAPS[0], scene.vec(-1000, -500, 350), 45, 330, 17, resonance_distance=900),
    ]
    spawn = scene.vec(0, -1500, 400)
    scene.finalize_map(path, spawn, scene.rot(pitch=2.0, yaw=90))
    save_map(path)
    add_map_report(path, spawn, gates)


def build_crystal():
    path = MAPS[2]
    clear_map(path)
    sky = scene.create_custom_sky('M_Crystal_PrismaticVoid', '''
        float3 d = normalize(Dir);
        float h = saturate(d.z * 0.5 + 0.5);
        float band = pow(saturate(sin(d.x * 4.0 + d.y * 3.0 + d.z * 6.0) * 0.5 + 0.5), 8.0);
        float3 base = lerp(float3(0.018, 0.025, 0.055), float3(0.075, 0.04, 0.12), h);
        return base + band * float3(0.035, 0.02, 0.055);
    ''')
    scene.spawn_sky('Lux_Crystal', sky)
    scene.configure_atmosphere(
        'Lux_Crystal', sky, scene.rot(pitch=-35, yaw=64), 1.8, scene.color(0.84, 0.88, 1.0), 0.85,
        scene.color(0.055, 0.035, 0.085), 0.00045, 4200, -0.05, 0.16, 15.0)
    scene.spawn_static('Lux_Crystal_LowGarden', 'garden', scene.vec(-1100, 650, 500), -30, target_span=650, base_collision=True)
    scene.spawn_static('Lux_Crystal_MiddleGarden', 'garden', scene.vec(1100, 1250, 1150), 105, target_span=720, base_collision=True)
    scene.spawn_static('Lux_Crystal_HighGarden', 'garden', scene.vec(-750, 2750, 1550), 175, target_span=680, base_collision=True)
    scene.spawn_static('Lux_Crystal_DistantPagoda', 'pagoda', scene.vec(1050, 4200, 400), 180, target_height=2200, base_collision=True)
    scene.spawn_static('Lux_Crystal_PrismGuardian', 'guardian', scene.vec(700, 600, 550), -25, target_height=380, base_collision=True)
    scene.spawn_water('Lux_Crystal_LocalPool_A', '/Game/LuxGenerated/Materials/M_Lux_CrystalMirrorWater', scene.vec(-1100, 650, 475), scene.vec(520, 520, 1))
    scene.spawn_water('Lux_Crystal_LocalPool_B', '/Game/LuxGenerated/Materials/M_Lux_CrystalMirrorWater', scene.vec(1100, 1250, 1125), scene.vec(560, 560, 1))
    scene.spawn_point('Lux_Crystal_LowerEmerald', scene.vec(-950, 650, 900), 38, 1300, scene.color(0.32, 0.90, 0.80), True)
    scene.spawn_point('Lux_Crystal_UpperAmethyst', scene.vec(900, 1700, 1750), 55, 1900, scene.color(0.74, 0.42, 1.0), True)
    scene.spawn_point('Lux_Crystal_PagodaRuby', scene.vec(1050, 3500, 1150), 60, 2100, scene.color(1.0, 0.38, 0.58), True)
    gates = [
        scene.configure_gate('Lux_Crystal_ForwardGate', '第三仙门 ｜ 棱镜折射（通往太极归一）', MAPS[3], scene.vec(1400, 1800, 1000), -35, 460, 21.8, 'crystal_portal', 1200),
        scene.configure_gate('Lux_Crystal_ReturnGate', '归返仙门 ｜ 墨云来处', MAPS[1], scene.vec(-1400, -100, 500), 45, 330, 17, resonance_distance=900),
    ]
    spawn = scene.vec(0, -1400, 700)
    scene.finalize_map(path, spawn, scene.rot(pitch=3.0, yaw=80))
    save_map(path)
    add_map_report(path, spawn, gates)


def build_taiji():
    path = MAPS[3]
    clear_map(path)
    sky = scene.create_custom_sky('M_Taiji_CosmicVoid', '''
        float3 d = normalize(Dir);
        float h = saturate(d.z * 0.5 + 0.5);
        float horizon = exp(-abs(d.z) * 14.0);
        float3 base = lerp(float3(0.002, 0.003, 0.008), float3(0.012, 0.018, 0.035), h);
        return base + float3(0.12, 0.085, 0.03) * horizon;
    ''')
    scene.spawn_sky('Lux_Taiji', sky)
    scene.configure_atmosphere(
        'Lux_Taiji', sky, scene.rot(pitch=-22, yaw=42), 1.65, scene.color(1.0, 0.90, 0.72), 0.75,
        scene.color(0.025, 0.03, 0.07), 0.00022, 7000, -0.20, 0.12, 0.0)
    sphere_mesh = scene.load_mesh('taiji')
    bounds = sphere_mesh.get_bounding_box()
    scale = 1500.0 / max(float(bounds.max.z - bounds.min.z), 1.0)
    sphere = ACTORS.spawn_actor_from_class(unreal.ButterflyDreamPropActor, scene.vec(0, 2200, 1300), scene.rot())
    sphere.set_actor_label('Lux_Taiji_CentralYinYangSphere')
    sphere.configure_prop(sphere_mesh, scale, True, scene.color(0.90, 0.82, 0.60), 35, 1100)
    sphere.set_editor_property('spin_speed_yaw', 3.0)
    sphere.set_editor_property('bob_amplitude', 8.0)
    sphere.set_editor_property('bob_speed', math.tau * 0.16)
    for index in range(8):
        angle = (index + 0.5) * math.tau / 8.0
        x = math.cos(angle) * 1250
        y = 2200 + math.sin(angle) * 1250
        yaw = math.degrees(math.atan2(2200 - y, -x))
        scene.spawn_static(f'Lux_Taiji_RadialPillar_{index}', 'pillar', scene.vec(x, y, 50), yaw, target_height=620, base_collision=True)
    scene.spawn_point('Lux_Taiji_YinRim', scene.vec(-650, 1700, 1300), 45, 1800, scene.color(0.36, 0.72, 1.0), True)
    scene.spawn_point('Lux_Taiji_YangRim', scene.vec(650, 2500, 1550), 55, 1900, scene.color(1.0, 0.80, 0.40), True)
    gates = [
        scene.configure_gate('Lux_Taiji_ForwardGate', '第四仙门 ｜ 齐物天书（归返星海）', MAPS[0], scene.vec(0, 3400, 500), 0, 500, 18.5, 'scroll_gate', 1300),
        scene.configure_gate('Lux_Taiji_ReturnGate', '归返仙门 ｜ 琉璃来处', MAPS[2], scene.vec(-1500, 500, 350), 33, 340, 17, resonance_distance=900),
    ]
    spawn = scene.vec(0, -1800, 450)
    scene.finalize_map(path, spawn, scene.rot(pitch=4.0, yaw=90))
    save_map(path)
    add_map_report(path, spawn, gates)


def write_report():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT['finished_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
    path = REPORT_DIR / f'four-realms-build-{int(time.time())}.json'
    path.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log(f'FOUR_REALMS_BUILD status={REPORT["status"]} report={path}')


def main(quit_on_finish=True):
    actual_project = Path(unreal.Paths.project_dir()).resolve()
    if actual_project != PROJECT.resolve():
        raise RuntimeError(f'Wrong project: {actual_project}')
    if not BACKUP.is_dir():
        raise RuntimeError(f'Refusing to rebuild without backup: {BACKUP}')
    if not str(unreal.SystemLibrary.get_engine_version()).startswith('5.8'):
        raise RuntimeError('UE 5.8 is required')
    try:
        for path in MAPS:
            if not ASSETS.does_asset_exist(path):
                raise RuntimeError(f'Required existing map missing: {path}')
        for key in scene.MESHES:
            mesh = scene.load_mesh(key)
            if mesh.get_num_triangles(0) == 0:
                raise RuntimeError(f'Required mesh has no render geometry: {mesh.get_path_name()}')
        scene.restore_scene_materials()
        build_starsea()
        build_inkcloud()
        build_crystal()
        build_taiji()
        REPORT['status'] = 'SUCCEEDED'
    except Exception as exc:
        import traceback
        REPORT['status'] = 'FAILED'
        REPORT['errors'].append(f'{exc}\n{traceback.format_exc()}')
        unreal.log_error(traceback.format_exc())
    finally:
        write_report()
        if quit_on_finish:
            unreal.SystemLibrary.quit_editor()
    return REPORT['status'] == 'SUCCEEDED'


if __name__ == '__main__':
    main()
