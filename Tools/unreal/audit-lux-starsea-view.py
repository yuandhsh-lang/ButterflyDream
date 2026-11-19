import json
from pathlib import Path
import unreal

out = Path(r'E:\紫萱2版\Evidence\Unreal\LuxRecovery_20261117\view-audit.json')
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {'status': 'STARTED', 'actors': [], 'errors': []}
try:
    if not level.load_level('/Game/Maps/Lux_StarSeaDream'):
        raise RuntimeError('Could not load StarSea map')
    for actor in actors.get_all_level_actors():
        origin, extent = actor.get_actor_bounds(False)
        loc = actor.get_actor_location()
        report['actors'].append({'name': actor.get_actor_label(), 'class': actor.get_class().get_name(), 'location': [loc.x,loc.y,loc.z], 'origin': [origin.x,origin.y,origin.z], 'extent': [extent.x,extent.y,extent.z]})
    report['status'] = 'SUCCEEDED'
except Exception as exc:
    report['status'] = 'FAILED'
    report['errors'].append(str(exc))
finally:
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
