"""Scripted PIE traversal verification for the ButterflyDream dream gates.

Loads a map, starts PIE, flies the real butterfly pawn along the gate's local
+Y axis (portal normal), requests wing boost through a dev-only hook, then
crosses the doorway, follows the tunnel to its exit and waits for the scene
switch. All gate state is read through BlueprintPure accessors so the report
reflects the runtime state machine, not a re-implementation of it.

Config: E:\\紫萱2版\\Tools\\unreal\\traversal-config.json
"""

raise RuntimeError(
    "Disabled: this legacy script references F06, obsolete APIs and teleports the pawn. "
    "Use the four-realm input-driven verification instead."
)

import json
import math
import os
import time
import traceback
from pathlib import Path
import unreal

CFG_PATH = Path(r'E:\紫萱2版\Tools\unreal\traversal-config.json')
DEFAULT_CFG = {
    'map': '/Game/Maps/F06_SakuraDream',
    'out': r'E:\紫萱2版\Evidence\Unreal\Traversal\traversal.json',
    'shot_dir': r'E:\ButterflyDream_LuxWork\Saved\Screenshots\WindowsEditor',
    'step_cm': 6.0,
    'approach_cm': 1500.0,
    'charge_offset_cm': 380.0,
    'charge_timeout': 45.0,
    'traverse_timeout': 150.0,
    'transition_timeout': 150.0,
    'warmup': 8.0,
}
CFG = dict(DEFAULT_CFG)
if CFG_PATH.exists():
    CFG.update(json.loads(CFG_PATH.read_text(encoding='utf-8')))

OUT = Path(CFG['out'])
SHOT_DIR = Path(CFG['shot_dir'])
EDITOR = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
LEVEL = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)

STATE = {
    'callback': None,
    'phase': 'warmup',
    't0': time.monotonic(),
    'phase_t0': time.monotonic(),
    'finished': False,
    'shots_before': sorted(os.listdir(SHOT_DIR)) if SHOT_DIR.is_dir() else [],
    'shots': [],
    'report': {
        'status': 'RUNNING',
        'map': CFG['map'],
        'events': [],
        'phases': [],
        'gate': {},
        'route': {},
        'samples': [],
    },
}


def log_event(message):
    entry = {'t': round(time.monotonic() - STATE['t0'], 2), 'phase': STATE['phase'], 'message': message}
    STATE['report']['events'].append(entry)
    unreal.log(f'DREAM_TRAVERSAL {message}')


def write_report(status):
    STATE['report']['status'] = status
    STATE['report']['phase'] = STATE['phase']
    STATE['report']['elapsed'] = round(time.monotonic() - STATE['t0'], 2)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(STATE['report'], ensure_ascii=False, indent=2), encoding='utf-8')


def shot(world, label):
    try:
        STATE['shots'].append({'label': label, 't': round(time.monotonic() - STATE['t0'], 2)})
        unreal.SystemLibrary.execute_console_command(world, 'HighResShot 1')
        log_event(f'shot {label}')
    except Exception as exc:
        log_event(f'shot failed {label}: {exc}')


def set_phase(name):
    STATE['report']['phases'].append({'phase': name, 't': round(time.monotonic() - STATE['t0'], 2)})
    STATE['phase'] = name
    STATE['phase_t0'] = time.monotonic()
    log_event(f'phase -> {name}')


def prop(obj, names, default=None):
    for name in names:
        try:
            value = obj.get_editor_property(name)
            return value
        except Exception:
            continue
    return default


def vec(value):
    return [round(float(value.x), 3), round(float(value.y), 3), round(float(value.z), 3)]


def get_gate_state(gate):
    def call(names, default):
        for name in names:
            fn = getattr(gate, name, None)
            if callable(fn):
                try:
                    return fn()
                except Exception:
                    continue
        return default

    return {
        'near': bool(call(['is_player_near_gate'], False)),
        'resonance': round(float(call(['get_resonance_progress'], 0.0)), 4),
        'ready': bool(call(['is_resonance_ready'], False)),
        'open_alpha': round(float(call(['get_current_open_alpha'], 0.0)), 4),
        'traversing': bool(call(['is_traversing'], False)),
        'transition_failed': bool(call(['has_transition_failure'], False)),
    }


def make_plan(gate):
    rot = gate.get_actor_rotation()
    loc = gate.get_actor_location()
    scale = gate.get_actor_scale3d()
    pitch = float(rot.pitch)
    yaw = float(rot.yaw)
    roll = float(rot.roll)
    sy, cy = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    # Gate geometry opens in local X/Z and passes along local +Y; these gates are yaw-only.
    forward = (-sy, cy, 0.0)
    offset = prop(gate, ['PortalCenterLocalOffset', 'portal_center_local_offset'], unreal.Vector(0, 0, 0))
    ox, oy, oz = float(offset.x) * float(scale.x), float(offset.y) * float(scale.y), float(offset.z) * float(scale.z)
    center = (float(loc.x) + (ox * cy - oy * sy),
              float(loc.y) + (ox * sy + oy * cy),
              float(loc.z) + oz)
    rotary = bool(prop(gate, ['bUseRotaryInnerRingMode', 'use_rotary_inner_ring_mode'], False))
    exit_local_y = 315.0 if rotary else 860.0
    exit_world_cm = exit_local_y * float(scale.y)
    plan = {
        'actor_location': vec(loc),
        'actor_rotation': [pitch, yaw, roll],
        'actor_scale': vec(scale),
        'rotary_mode': rotary,
        'portal_center': [round(v, 2) for v in center],
        'local_forward_world': [round(v, 4) for v in forward],
        'exit_world_cm': round(exit_world_cm, 1),
        'opening_half_width_local': 17.0 if rotary else 90.0,
        'opening_half_height_local': 17.0 if rotary else 105.0,
        'opening_half_width_world': round((17.0 if rotary else 90.0) * float(scale.x), 1),
        'opening_half_height_world': round((17.0 if rotary else 105.0) * float(scale.z), 1),
        'pitch_roll_clean': abs(pitch) < 0.01 and abs(roll) < 0.01,
        'target_map': str(prop(gate, ['TargetMapPackageName', 'target_map_package_name'], '')),
    }
    return plan, center, forward


def point_at(center, forward, distance_cm):
    return unreal.Vector(center[0] + forward[0] * distance_cm,
                         center[1] + forward[1] * distance_cm,
                         center[2] + forward[2] * distance_cm)


def begin():
    if not LEVEL.load_level(CFG['map']):
        raise RuntimeError(f'Could not load {CFG["map"]}')
    STATE['callback'] = unreal.register_slate_post_tick_callback(on_tick)
    LEVEL.editor_request_begin_play()


def finish(status):
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
        if SHOT_DIR.is_dir():
            new_shots = [f for f in sorted(os.listdir(SHOT_DIR)) if f not in STATE['shots_before']]
            STATE['report']['new_screenshots'] = new_shots
            STATE['report']['shot_requests'] = STATE['shots']
    finally:
        write_report(status)
        unreal.SystemLibrary.quit_editor()


def on_tick(delta):
    try:
        world = EDITOR.get_game_world()
        if not world:
            return
        now = time.monotonic()

        if STATE['phase'] == 'warmup':
            pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
            if not pawn or now - STATE['phase_t0'] < float(CFG['warmup']):
                return
            gates = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ButterflyDreamGateActor)
            if not gates:
                finish('FAILED_NO_GATE')
                return
            gate = gates[0]
            plan, center, forward = make_plan(gate)
            STATE['gate'] = gate
            STATE['report']['gate'] = plan
            STATE['report']['pawn'] = pawn.get_name()
            STATE['report']['start_location'] = vec(pawn.get_actor_location())
            STATE['report']['world_at_start'] = world.get_name()
            STATE['route'] = {
                'center': center,
                'forward': forward,
                'exit_world_cm': plan['exit_world_cm'],
                'distance': -float(CFG['approach_cm']),
            }
            controller = unreal.GameplayStatics.get_player_controller(world, 0)
            if controller:
                yaw_deg = math.degrees(math.atan2(forward[1], forward[0]))
                rot = unreal.Rotator()
                rot.pitch, rot.yaw, rot.roll = 0.0, yaw_deg, 0.0
                controller.set_control_rotation(rot)
            # Dev-only hook exposed by AButterflyPawn; charges resonance like Shift would.
            try:
                pawn.dream_test_set_boost(True)
                log_event('boost enabled via DreamTestSetBoost hook')
            except Exception as exc:
                log_event(f'boost hook unavailable: {exc}')
            target = point_at(center, forward, -float(CFG['approach_cm']))
            pawn.set_actor_location(target, False, False)
            STATE['report']['approach_target'] = vec(target)
            shot(world, 'approach')
            set_phase('approach')
            return

        if STATE['phase'] == 'approach':
            pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
            if not pawn:
                return
            target = point_at(STATE['route']['center'], STATE['route']['forward'], -float(CFG['charge_offset_cm']))
            pawn.set_actor_location(target, False, False)
            STATE['route']['distance'] = -float(CFG['charge_offset_cm'])
            set_phase('charge')
            return

        if STATE['phase'] == 'charge':
            gate = STATE['gate']
            state = get_gate_state(gate)
            STATE['report']['samples'].append({'phase': 'charge', **state})
            if state['ready'] and state['open_alpha'] >= 0.9:
                shot(world, 'resonance_ready')
                set_phase('traverse')
            elif now - STATE['phase_t0'] > float(CFG['charge_timeout']):
                shot(world, 'charge_timeout')
                finish('FAILED_RESONANCE_TIMEOUT')
            return

        if STATE['phase'] == 'traverse':
            pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
            gate = STATE['gate']
            state = get_gate_state(gate)
            STATE['report']['samples'].append({'phase': 'traverse',
                                               'distance_cm': round(STATE['route']['distance'], 1), **state})
            limit = STATE['route']['exit_world_cm'] + 400.0
            if STATE['route']['distance'] >= limit:
                shot(world, 'tunnel_end')
                STATE['report']['traverse_completed'] = True
                set_phase('await_transition')
                return
            STATE['route']['distance'] = min(STATE['route']['distance'] + float(CFG['step_cm']), limit)
            target = point_at(STATE['route']['center'], STATE['route']['forward'], STATE['route']['distance'])
            pawn.set_actor_location(target, False, False)
            d = STATE['route']['distance']
            if d > 0 and not STATE['report'].get('crossed_portal'):
                STATE['report']['crossed_portal'] = True
                shot(world, 'portal_crossing')
            elif d > STATE['route']['exit_world_cm'] * 0.5 and not STATE['report'].get('mid_tunnel'):
                STATE['report']['mid_tunnel'] = True
                shot(world, 'mid_tunnel')
            if now - STATE['phase_t0'] > float(CFG['traverse_timeout']):
                finish('FAILED_TRAVERSE_TIMEOUT')
            return

        if STATE['phase'] == 'await_transition':
            current_map = world.get_name()
            gate = STATE['gate']
            state = get_gate_state(gate) if gate else {}
            STATE['report']['samples'].append({'phase': 'await', 'map': current_map, **state})
            if current_map != STATE['report'].get('world_at_start'):
                STATE['report']['world_after'] = current_map
                shot(world, 'after_transition')
                log_event(f'world changed to {current_map}')
                set_phase('done')
                finish('SUCCEEDED')
            elif state.get('transition_failed'):
                finish('FAILED_TRANSITION')
            elif now - STATE['phase_t0'] > float(CFG['transition_timeout']):
                finish('FAILED_TRANSITION_TIMEOUT')
            return

        if STATE['phase'] == 'done':
            finish('SUCCEEDED')
    except Exception as exc:
        finish(f'FAILED_EXCEPTION {exc}')
        unreal.log_error(traceback.format_exc())


try:
    begin()
except Exception as exc:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({'status': 'FAILED_START', 'error': str(exc),
                               'traceback': traceback.format_exc()}, ensure_ascii=False, indent=2),
                   encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
