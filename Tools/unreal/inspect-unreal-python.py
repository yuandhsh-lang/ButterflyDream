import json
from pathlib import Path
import unreal

root = Path(__file__).resolve().parents[2]
report = {
    "engine_version": unreal.SystemLibrary.get_engine_version(),
    "project": unreal.Paths.get_project_file_path(),
    "unreal_symbols": [name for name in dir(unreal) if any(term in name.lower() for term in ["interchange", "assetimport", "level", "editorapplication", "editorsubsystem"])],
    "status": "PYTHON_API_INSPECTED",
}
for name in [
    "EditorApplication", "EditorLevelLibrary", "EditorAssetLibrary",
    "AssetImportTask", "AssetTools", "AssetToolsHelpers", "SystemLibrary",
    "EditorLevelSubsystem", "EditorAssetSubsystem", "InterchangeManager",
    "InterchangeImport", "EditorInterchangeManager", "InterchangePipelineBase",
]:
    value = getattr(unreal, name, None)
    report[name] = dir(value) if value else None
output = root / "Evidence" / "Unreal" / "python-api-inspection.json"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
unreal.log(f"BUTTERFLY_PYTHON_API_INSPECTED {output}")
quit_editor = getattr(unreal.SystemLibrary, "quit_editor", None)
if quit_editor:
    quit_editor()
else:
    unreal.SystemLibrary.execute_console_command(None, "QUIT_EDITOR")
