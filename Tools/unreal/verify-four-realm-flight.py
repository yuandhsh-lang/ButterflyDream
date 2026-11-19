import json
import math
import os
import statistics
import time
from pathlib import Path

import unreal


ROOT = Path(r'E:\紫萱2版')
RUN_ID = time.strftime('%Y%m%d_%H%M%S') + f'-{os.getpid()}'
OUT = ROOT / 'Evidence' / 'Unreal' / 'FourRealms_20261119' / f'flight-verification-{RUN_ID}.json'
MAX_WALL_SECONDS = float(os.environ.get('FOUR_REALM_TEST_WALL_SECONDS', '1800'))
SHOT_DIR = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())) / 'Screenshots' / 'WindowsEditor'
MAX_TRANSITIONS = int(os.environ.get('FOUR_REALM_TEST_TRANSITIONS', '20'))
START_MAP = '/Game/Maps/Lux_StarSeaDream'
KEY_NAMES = {'w': 'W', 'shift': 'LeftShift', 's': 'S', 'tab': 'Tab', 'e': 'E', 'r': 'R', 'space': 'SpaceBar', 'c': 'C'}
FORWARD = ['Lux_InkCloudDream', 'Lux_CrystalMirageDream', 'Lux_TaijiAwakeningDream', 'Lux_StarSeaDream']
REVERSE = ['Lux_TaijiAwakeningDream', 'Lux_CrystalMirageDream', 'Lux_InkCloudDream', 'Lux_StarSeaDream']
NEXT_MAPS = FORWARD * 4 + REVERSE
EDITOR = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
LEVEL = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
STATE = {
    'phase': 'startup',
    'phase_t0': 0.0,
    't0': time.monotonic(),
    'current_map': None,
    'gate': None,
    'transition_index': 0,
    'callback': None,
    'keys': {'w': False, 'shift': False, 's': False, 'tab': False, 'e': False, 'r': False, 'space': False, 'c': False},
    'shots_before': sorted(os.listdir(SHOT_DIR)) if SHOT_DIR.is_dir() else [],
    'shots': [],
    'shot_labels': set(),
    'finished': False,
    'last_local_y': None,
    'position_at_phase': None,
    'map_sample_start': None,
    'last_frame_wall': None,
    'frame_samples': {},
    'report': {
        'status': 'RUNNING',
        'input_method': 'PlayerController.InputKey simulated via DreamTestInputKey, through EnhancedInput',
        'teleport_used_for_acceptance': False,
        'requested_transitions': MAX_TRANSITIONS,
        'max_wall_seconds': MAX_WALL_SECONDS,
        'completed_transitions': 0,
        'events': [],
        'phases': [],
        'map_checks': [],
        'shots': [],
    },
}


def log(message):
    entry = {'t': round(time.monotonic() - STATE['t0'], 2), 'phase': STATE['phase'], 'message': message}
    STATE['report']['events'].append(entry)
    unreal.log(f'FOUR_FLIGHT {message}')


def set_phase(name):
    STATE['phase'] = name
    STATE['phase_t0'] = time.monotonic()
    STATE['position_at_phase'] = None
    STATE['report']['phases'].append({'phase': name, 't': round(time.monotonic() - STATE['t0'], 2)})
    log(f'phase -> {name}')


def record_frame():
    now = time.monotonic()
    previous = STATE['last_frame_wall']
    STATE['last_frame_wall'] = now
    started = STATE['map_sample_start']
    if previous is None or started is None or now - started < 8.0:
        return
    elapsed_ms = (now - previous) * 1000.0
    if 0.0 < elapsed_ms < 5000.0:
        STATE['frame_samples'].setdefault(STATE['current_map'], []).append(elapsed_ms)


def record_measurements():
    scope = 'Editor PIE Slate frame wall time; first 8 seconds after map discovery excluded; not a standalone game benchmark'
    report = {'scope': scope, 'maps': {}}
    for name, values in STATE['frame_samples'].items():
        if not values:
            report['maps'][name] = {'status': 'NOT_TESTED'}
            continue
        percentiles = statistics.quantiles(values, n=100, method='inclusive') if len(values) >= 2 else [values[0]] * 99
        report['maps'][name] = {
            'status': 'MEASURED',
            'samples': len(values),
            'median_ms': round(statistics.median(values), 3),
            'mean_ms': round(statistics.mean(values), 3),
            'p95_ms': round(percentiles[94], 3),
            'p99_ms': round(percentiles[98], 3),
            'max_ms': round(max(values), 3),
        }
    STATE['report']['frame_timing'] = report
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ('cb', wintypes.DWORD), ('page_fault_count', wintypes.DWORD),
                ('peak_working_set', ctypes.c_size_t), ('working_set', ctypes.c_size_t),
                ('quota_peak_paged_pool', ctypes.c_size_t), ('quota_paged_pool', ctypes.c_size_t),
                ('quota_peak_nonpaged_pool', ctypes.c_size_t), ('quota_nonpaged_pool', ctypes.c_size_t),
                ('pagefile', ctypes.c_size_t), ('peak_pagefile', ctypes.c_size_t),
            ]
        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        psapi = ctypes.WinDLL('psapi', use_last_error=True)
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessMemoryCounters), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        if psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            STATE['report']['process_memory_at_finish'] = {
                'scope': 'UE editor process including PIE and loaded assets; not a standalone game',
                'working_set_bytes': counters.working_set,
                'peak_working_set_bytes': counters.peak_working_set,
                'pagefile_bytes': counters.pagefile,
                'peak_pagefile_bytes': counters.peak_pagefile,
            }
        else:
            STATE['report']['process_memory_at_finish'] = {'status': 'NOT_MEASURED', 'win32_error': ctypes.get_last_error()}


def finish(status):
    if STATE['finished']:
        return
    STATE['finished'] = True
    for key in STATE['keys']:
        send_key(key, False)
    STATE['report']['status'] = status
    STATE['report']['completed_transitions'] = STATE['transition_index']
    STATE['report']['elapsed_seconds'] = round(time.monotonic() - STATE['t0'], 2)
    if SHOT_DIR.is_dir():
        STATE['report']['new_screenshots'] = [name for name in sorted(os.listdir(SHOT_DIR)) if name not in STATE['shots_before']]
    try:
        record_measurements()
    except Exception as exc:
        STATE['report']['measurement_error'] = str(exc)
        unreal.log_error(f'FOUR_FLIGHT measurement failed: {exc}')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(STATE['report'], ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log(f'FOUR_FLIGHT_FINISHED status={status} transitions={STATE["transition_index"]} report={OUT}')
    try:
        if STATE['callback'] is not None:
            unreal.unregister_slate_post_tick_callback(STATE['callback'])
    except Exception:
        pass
    try:
        if LEVEL.is_in_play_in_editor():
            LEVEL.editor_request_end_play()
    except Exception:
        pass
    unreal.SystemLibrary.quit_editor()


def send_key(name, pressed):
    if STATE['keys'].get(name) == pressed:
        return
    pawn = unreal.GameplayStatics.get_player_pawn(EDITOR.get_game_world(), 0)
    if not pawn:
        return
    try:
        pawn.dream_test_input_key(KEY_NAMES[name], pressed)
        STATE['keys'][name] = pressed
        log(f'input {KEY_NAMES[name]}={pressed}')
    except Exception as exc:
        finish(f'FAILED_INPUT_HOOK: {exc}')


def release_all():
    for key in STATE['keys']:
        send_key(key, False)


def shot(label):
    if os.environ.get('FOUR_REALM_CAPTURE', '1') == '0' or label in STATE['shot_labels']:
        return
    STATE['shot_labels'].add(label)
    world = EDITOR.get_game_world()
    if not world:
        return
    STATE['report']['shots'].append({'label': label, 't': round(time.monotonic() - STATE['t0'], 2)})
    unreal.SystemLibrary.execute_console_command(world, 'HighResShot 1')


def local_position(gate, pawn):
    offset = gate.get_editor_property('portal_center_local_offset')
    return gate.get_actor_transform().inverse_transform_position(pawn.get_actor_location()) - offset


def find_gate(world, target_map):
    gates = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ButterflyDreamGateActor)
    matches = [gate for gate in gates if str(gate.get_editor_property('target_map_package_name')) == target_map]
    if len(matches) != 1:
        raise RuntimeError(f'Expected one gate targeting {target_map}, found {len(matches)}')
    return matches[0]


def aim_at_gate(gate):
    pawn = unreal.GameplayStatics.get_player_pawn(EDITOR.get_game_world(), 0)
    controller = unreal.GameplayStatics.get_player_controller(EDITOR.get_game_world(), 0)
    right = gate.get_actor_right_vector()
    yaw = math.degrees(math.atan2(right.y, right.x))
    rot = unreal.Rotator()
    rot.pitch = 0.0
    rot.yaw = yaw
    controller.set_control_rotation(rot)
    STATE['control_yaw'] = yaw


def phase_timeout(default=90.0):
    return time.monotonic() - STATE['phase_t0'] > float(default)


def begin():
    STATE['phase_t0'] = STATE['t0']
    if not LEVEL.load_level(START_MAP):
        raise RuntimeError(f'Could not load {START_MAP}')
    STATE['callback'] = unreal.register_slate_post_tick_callback(on_tick)
    LEVEL.editor_request_begin_play()


def on_tick(_delta):
    if STATE['finished']:
        return
    try:
        if time.monotonic() - STATE['t0'] > MAX_WALL_SECONDS:
            finish('FAILED_WALL_TIMEOUT')
            return
        world = EDITOR.get_game_world()
        if not world:
            return
        map_name = world.get_name()
        if STATE['current_map'] is not None and map_name != STATE['current_map']:
            if STATE['phase'] != 'traverse':
                finish(f'FAILED_UNEXPECTED_MAP: {STATE["current_map"]} -> {map_name} during {STATE["phase"]}')
                return
            target = NEXT_MAPS[STATE['transition_index']]
            if map_name != target:
                finish(f'FAILED_TARGET: expected {target}, reached {map_name}')
                return
            if STATE['last_local_y'] is not None and STATE['last_local_y'] < STATE['exit_y']:
                finish(f'FAILED_EARLY_TRANSITION: localY={STATE["last_local_y"]:.2f}, exit={STATE["exit_y"]:.2f}')
                return
            STATE['report']['map_checks'].append({'from': STATE['current_map'], 'to': map_name, 'result': 'SUCCEEDED'})
            STATE['transition_index'] += 1
            release_all()
            shot(f'after_transition_{STATE["transition_index"]}')
            if STATE['transition_index'] >= MAX_TRANSITIONS:
                finish('SUCCEEDED')
            else:
                STATE['current_map'] = None
                STATE['gate'] = None
                set_phase('warmup')
            return

        if STATE['current_map'] is None:
            STATE['current_map'] = map_name
            if map_name != START_MAP and STATE['transition_index'] == 0:
                finish(f'FAILED_START_MAP: {map_name}')
                return
            STATE['report']['start_map'] = map_name
            STATE['map_sample_start'] = time.monotonic()
            STATE['last_frame_wall'] = None
            set_phase('warmup')
            return

        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        if not pawn:
            return
        now = time.monotonic()
        record_frame()

        if STATE['phase'] == 'warmup':
            if now - STATE['phase_t0'] < 2.0:
                return
            expected = NEXT_MAPS[STATE['transition_index']]
            STATE['gate'] = find_gate(world, expected)
            aim_at_gate(STATE['gate'])
            STATE['exit_y'] = STATE['gate'].get_tunnel_exit_distance()
            STATE['last_local_y'] = None
            shot(f'spawn_{STATE["transition_index"]}')
            set_phase('align_altitude')
            return

        gate = STATE['gate']
        local = local_position(gate, pawn)
        STATE['last_local_y'] = float(local.y)
        position = pawn.get_actor_location()
        if STATE['position_at_phase'] is None:
            STATE['position_at_phase'] = position
        moved = math.sqrt(sum((getattr(position, axis) - getattr(STATE['position_at_phase'], axis)) ** 2 for axis in ('x', 'y', 'z')))

        if STATE['phase'] == 'align_altitude':
            if float(gate.get_resonance_percent()) > 0.01:
                finish('FAILED_ALIGNMENT_WITHOUT_SHIFT_CHARGED')
                return
            if abs(float(local.z)) <= 4.0:
                send_key('space', False)
                send_key('c', False)
                set_phase('test_e' if STATE['transition_index'] == 0 else 'approach_no_shift')
            else:
                send_key('space', float(local.z) > 4.0)
                send_key('c', float(local.z) < -4.0)
                if phase_timeout(30.0):
                    finish(f'FAILED_ALTITUDE_ALIGNMENT: localZ={local.z:.2f}')

        elif STATE['phase'] == 'test_e':
            send_key('e', True)
            send_key('e', False)
            set_phase('test_r')

        elif STATE['phase'] == 'test_r':
            send_key('r', True)
            send_key('r', False)
            set_phase('approach_no_shift')

        elif STATE['phase'] == 'approach_no_shift':
            if float(gate.get_resonance_percent()) > 0.01:
                finish(f'FAILED_PROXIMITY_CHARGE: {gate.get_resonance_percent()}')
                return
            if float(local.y) < -80.0:
                send_key('w', True)
                if phase_timeout(120.0):
                    finish(f'FAILED_APPROACH: stuck at localY={local.y:.2f}, moved={moved:.2f}')
                return
            release_all()
            if float(gate.get_resonance_percent()) > 0.01:
                finish('FAILED_PROXIMITY_CHARGE_AFTER_STOP')
                return
            shot('approach_without_shift')
            set_phase('charge')

        elif STATE['phase'] == 'charge':
            send_key('shift', True)
            if gate.is_resonance_ready():
                shot('resonance_ready')
                set_phase('menu' if STATE['transition_index'] == 0 else 'traverse')
            elif phase_timeout(20.0):
                finish(f'FAILED_CHARGE_TIMEOUT: {gate.get_gate_state_name()} charge={gate.get_resonance_percent()}')

        elif STATE['phase'] == 'menu':
            send_key('tab', True)
            STATE['menu_position'] = position
            STATE['menu_charge'] = float(gate.get_resonance_percent())
            set_phase('menu_open')

        elif STATE['phase'] == 'menu_open':
            if now - STATE['phase_t0'] < 1.0:
                return
            if map_name != STATE['current_map'] or position != STATE['menu_position'] or float(gate.get_resonance_percent()) != STATE['menu_charge']:
                finish('FAILED_MENU_STATE_CHANGED')
                return
            send_key('tab', False)
            set_phase('backout')

        elif STATE['phase'] == 'backout':
            if not gate.is_traversing():
                send_key('w', True)
                if phase_timeout(20.0):
                    finish('FAILED_ENTER_FOR_BACKOUT')
                return
            send_key('w', False)
            send_key('s', True)
            if float(local.y) < -20.0:
                release_all()
                if gate.is_traversing():
                    finish('FAILED_BACKOUT_STATE')
                    return
                shot('backout_ready')
                set_phase('traverse')
            elif phase_timeout(25.0):
                finish('FAILED_BACKOUT_TIMEOUT')

        elif STATE['phase'] == 'traverse':
            if not gate.is_traversing() and float(local.y) < STATE['exit_y']:
                send_key('w', True)
            else:
                send_key('w', False)
            send_key('shift', True)
            if float(local.y) >= STATE['exit_y']:
                shot('tunnel_exit')
            elif phase_timeout(150.0):
                finish(f'FAILED_TRAVERSE_TIMEOUT: localY={local.y:.2f}, exit={STATE["exit_y"]:.2f}, moved={moved:.2f}')
            if float(local.y) > STATE['exit_y'] + 60.0 and not gate.is_traversing():
                if phase_timeout(180.0):
                    finish('FAILED_TRANSITION_TIMEOUT')

    except Exception as exc:
        import traceback
        STATE['report']['fatal_error'] = traceback.format_exc()
        finish(f'FAILED_EXCEPTION: {exc}')


try:
    begin()
except Exception as exc:
    import traceback
    STATE['report']['status'] = 'FAILED_START'
    STATE['report']['fatal_error'] = traceback.format_exc()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(STATE['report'], ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
