import json
import math
import os
import time
import traceback
from pathlib import Path
import unreal

EVIDENCE = Path(r'E:\ButterflyDream_LuxWork\Saved\Evidence')
OUT = EVIDENCE / 'runtime-view-audit-v2.json'
SHOT_DIR = Path(r'E:\ButterflyDream_LuxWork\Saved\Screenshots\WindowsEditor')
EDITOR = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
LEVEL = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
START = time.monotonic()
STATE = {'callback': None, 'finished': False, 'captured_at': None, 'shots_before': [], 'report': None}


def xyz(v):
    return [round(float(v.x), 3), round(float(v.y), 3), round(float(v.z), 3)]


def ray_box(pos, direction, center, extents):
    tmin, tmax = 0.0, 1e9
    for i in range(3):
        lo = center[i] - extents[i]
        hi = center[i] + extents[i]
        if abs(direction[i]) < 1e-9:
            if pos[i] < lo or pos[i] > hi:
                return None
            continue
        a = (lo - pos[i]) / direction[i]
        b = (hi - pos[i]) / direction[i]
        tmin = max(tmin, min(a, b))
        tmax = min(tmax, max(a, b))
        if tmax < tmin:
            return None
    return round(tmin, 2)


def view_dir(pitch_deg, yaw_deg):
    p = math.radians(pitch_deg)
    y = math.radians(yaw_deg)
    return [math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p)]


def component_bounds(comp):
    """USystemLibrary::GetComponentBounds may return a tuple or a struct depending on the
    Python binding, so normalise both shapes into (origin, extent, radius)."""
    got = unreal.SystemLibrary.get_component_bounds(comp)
    if isinstance(got, tuple):
        origin, extent = got[0], got[1]
        radius = got[2] if len(got) > 2 else 0.0
        return origin, extent, radius
    return got.origin, got.box_extent, getattr(got, 'sphere_radius', 0.0)


def component_scale(comp):
    for name in ('get_component_scale', 'get_world_scale'):
        fn = getattr(comp, name, None)
        if callable(fn):
            try:
                return xyz(fn())
            except Exception:
                continue
    return [0.0, 0.0, 0.0]


def snapshot_components(world):
    rows = []
    for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        try:
            comps = actor.get_components_by_class(unreal.StaticMeshComponent)
        except Exception:
            comps = []
        for comp in comps:
            try:
                mesh = comp.get_editor_property('static_mesh')
                origin, extent, _sphere = component_bounds(comp)
                rows.append({
                    'actor': actor.get_name(),
                    'actor_class': actor.get_class().get_name(),
                    'component': comp.get_name(),
                    'mesh': mesh.get_path_name() if mesh else None,
                    'origin': xyz(origin),
                    'extent': xyz(extent),
                    'component_location': xyz(comp.get_world_location()),
                })
            except Exception as exc:
                rows.append({'actor': actor.get_name(), 'component': comp.get_name(), 'error': str(exc)})
    return rows


def capture():
    world = EDITOR.get_game_world()
    if not world:
        return False
    controller = unreal.GameplayStatics.get_player_controller(world, 0)
    cam = unreal.GameplayStatics.get_player_camera_manager(world, 0)
    pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
    if not controller or not cam or not pawn or time.monotonic() - START < 12:
        return False

    loc = cam.get_camera_location()
    rot = cam.get_camera_rotation()
    pos = xyz(loc)
    center_dir = view_dir(float(rot.pitch), float(rot.yaw))
    samples = {
        'center': (float(rot.pitch), float(rot.yaw)),
        'up25': (float(rot.pitch) + 25.0, float(rot.yaw)),
        'down25': (float(rot.pitch) - 25.0, float(rot.yaw)),
        'left25': (float(rot.pitch), float(rot.yaw) - 25.0),
        'right25': (float(rot.pitch), float(rot.yaw) + 25.0),
        'left50': (float(rot.pitch), float(rot.yaw) - 50.0),
        'right50': (float(rot.pitch), float(rot.yaw) + 50.0),
        'up50': (float(rot.pitch) + 50.0, float(rot.yaw)),
        'down50': (float(rot.pitch) - 50.0, float(rot.yaw)),
    }

    comps = snapshot_components(world)
    hits = {}
    for label, (pitch, yaw) in samples.items():
        direction = view_dir(pitch, yaw)
        rows = []
        for row in comps:
            if 'error' in row:
                continue
            d = ray_box(pos, direction, row['origin'], row['extent'])
            if d is not None:
                rows.append({**row, 'distance': d})
        rows.sort(key=lambda r: r['distance'])
        hits[label] = rows[:12]

    # Nearby components, regardless of direction: helps identify the butterfly wings.
    near = []
    for row in comps:
        if 'error' in row:
            continue
        center = row['origin']
        dist = math.sqrt(sum((center[i] - pos[i]) ** 2 for i in range(3)))
        near.append({**row, 'bounds_center_distance': round(dist, 1),
                     'bounds_min_distance': round(max(0.0, dist - math.sqrt(sum(e * e for e in row['extent']))), 1)})
    near.sort(key=lambda r: r['bounds_center_distance'])

    camera_rotation = [float(rot.pitch), float(rot.yaw), float(rot.roll)]
    pawn_loc = xyz(pawn.get_actor_location())
    report = {
        'status': 'SUCCEEDED',
        'time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'map': world.get_name(),
        'pawn': pawn.get_name(),
        'pawn_location': pawn_loc,
        'pawn_scale': xyz(pawn.get_actor_scale3d()),
        'camera_location': pos,
        'camera_rotation': camera_rotation,
        'camera_forward': center_dir,
        'sample_hits': hits,
        'nearest_components': near[:15],
        'component_count': len(comps),
    }

    # Butterfly detail: show each pawn component with bounds and distance from camera.
    pawn_rows = []
    for comp in pawn.get_components_by_class(unreal.StaticMeshComponent):
        try:
            mesh = comp.get_editor_property('static_mesh')
            origin, extent, _s = component_bounds(comp)
            c = xyz(origin)
            dist = math.sqrt(sum((c[i] - pos[i]) ** 2 for i in range(3)))
            pawn_rows.append({'component': comp.get_name(),
                              'mesh': mesh.get_path_name() if mesh else None,
                              'origin': c, 'extent': xyz(extent),
                              'world_scale': component_scale(comp),
                              'bounds_min_distance': round(max(0.0, dist - math.sqrt(sum(e * e for e in xyz(extent)))), 1),
                              'distance_to_camera': round(dist, 1)})
        except Exception as exc:
            pawn_rows.append({'component': comp.get_name(), 'error': str(exc)})
    report['pawn_components'] = pawn_rows

    STATE['shots_before'] = sorted(os.listdir(SHOT_DIR)) if SHOT_DIR.is_dir() else []
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    STATE['report'] = report
    unreal.SystemLibrary.execute_console_command(world, 'HighResShot 1')
    STATE['captured_at'] = time.monotonic()
    return True


def finish():
    if STATE['finished']:
        return
    STATE['finished'] = True
    try:
        if LEVEL.is_in_play_in_editor():
            LEVEL.editor_request_end_play()
    except Exception:
        pass
    try:
        if STATE['callback'] is not None:
            unreal.unregister_slate_post_tick_callback(STATE['callback'])
    except Exception:
        pass
    try:
        if STATE['report'] is not None and SHOT_DIR.is_dir():
            new_shots = [f for f in sorted(os.listdir(SHOT_DIR)) if f not in STATE['shots_before']]
            STATE['report']['new_screenshots'] = new_shots[-3:]
            OUT.write_text(json.dumps(STATE['report'], ensure_ascii=False, indent=2), encoding='utf-8')
    finally:
        unreal.SystemLibrary.quit_editor()


def on_tick(delta):
    try:
        if STATE['captured_at'] is None:
            if time.monotonic() - START > 240:
                EVIDENCE.mkdir(parents=True, exist_ok=True)
                OUT.write_text(json.dumps({'status': 'FAILED', 'error': 'Timed out waiting for PIE camera'}, indent=2))
                finish()
                return
            if capture():
                pass
        elif time.monotonic() - STATE['captured_at'] > 12:
            finish()
    except Exception as exc:
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({'status': 'FAILED', 'error': str(exc), 'traceback': traceback.format_exc()}, ensure_ascii=False, indent=2), encoding='utf-8')
        finish()


try:
    if not LEVEL.load_level('/Game/Maps/Lux_StarSeaDream'):
        raise RuntimeError('Could not load StarSea map')
    STATE['callback'] = unreal.register_slate_post_tick_callback(on_tick)
    LEVEL.editor_request_begin_play()
except Exception as exc:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({'status': 'FAILED', 'error': str(exc), 'traceback': traceback.format_exc()}, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
