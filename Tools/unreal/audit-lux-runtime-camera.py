import json
import math
import time
import traceback
from pathlib import Path
import unreal

OUT = Path(r'E:\紫萱2版\Evidence\Unreal\LuxRecovery_20261117\runtime-view-audit.json')
EDITOR = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
LEVEL = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
START = time.monotonic()
STATE = {'captured': False, 'finished': False, 'callback': None, 'capture_time': None}


def xyz(v):
    return [round(float(v.x), 3), round(float(v.y), 3), round(float(v.z), 3)]


def ray_box(pos, direction, center, extents):
    tmin, tmax = 0.0, 1000000.0
    for i in range(3):
        lo = center[i] - extents[i]
        hi = center[i] + extents[i]
        if abs(direction[i]) < 1e-8:
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


def save_report(report):
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


def finish():
    if STATE['finished']:
        return
    STATE['finished'] = True
    if LEVEL.is_in_play_in_editor():
        LEVEL.editor_request_end_play()
    unreal.unregister_slate_post_tick_callback(STATE['callback'])
    unreal.SystemLibrary.quit_editor()


def on_tick(delta):
    try:
        world = EDITOR.get_game_world()
        if not STATE['captured']:
            if time.monotonic() - START > 120:
                save_report({'status':'FAILED','error':'Timed out waiting for PIE camera'})
                finish()
                return
            if not world:
                return
            controller = unreal.GameplayStatics.get_player_controller(world, 0)
            cam = unreal.GameplayStatics.get_player_camera_manager(world, 0)
            pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
            if not controller or not cam or not pawn or time.monotonic() - START < 10:
                return
            camera_location = cam.get_camera_location()
            camera_rotation = cam.get_camera_rotation()
            pos = xyz(camera_location)
            pitch, yaw = math.radians(camera_rotation.pitch), math.radians(camera_rotation.yaw)
            direction = [math.cos(pitch)*math.cos(yaw), math.cos(pitch)*math.sin(yaw), math.sin(pitch)]
            hits = []
            for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
                for comp in actor.get_components_by_class(unreal.StaticMeshComponent):
                    try:
                        if not comp.is_visible() or comp.get_editor_property('hidden_in_game'):
                            continue
                        origin, extent, _ = unreal.SystemLibrary.get_component_bounds(comp)
                        distance = ray_box(pos, direction, xyz(origin), xyz(extent))
                        if distance is not None:
                            mesh = comp.get_editor_property('static_mesh')
                            hits.append({'actor':actor.get_name(),'component':comp.get_name(),'mesh':mesh.get_path_name() if mesh else None,'distance':distance,'origin':xyz(origin),'extent':xyz(extent)})
                    except Exception:
                        continue
            hits.sort(key=lambda x:x['distance'])
            report = {'status':'SUCCEEDED','pawn':pawn.get_name(),'pawn_location':xyz(pawn.get_actor_location()),'camera_location':pos,'camera_rotation':[camera_rotation.pitch,camera_rotation.yaw,camera_rotation.roll],'camera_forward':direction,'ray_hits':hits[:30]}
            save_report(report)
            unreal.SystemLibrary.execute_console_command(world, 'HighResShot 1')
            STATE['captured'] = True
            STATE['capture_time'] = time.monotonic()
        elif time.monotonic() - STATE['capture_time'] > 8:
            finish()
    except Exception as exc:
        save_report({'status':'FAILED','error':str(exc),'traceback':traceback.format_exc()})
        finish()

try:
    if not LEVEL.load_level('/Game/Maps/Lux_StarSeaDream'):
        raise RuntimeError('Could not load StarSea map')
    STATE['callback'] = unreal.register_slate_post_tick_callback(on_tick)
    LEVEL.editor_request_begin_play()
except Exception as exc:
    save_report({'status':'FAILED','error':str(exc),'traceback':traceback.format_exc()})
    unreal.SystemLibrary.quit_editor()
