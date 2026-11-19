"""Restore MSI file names and directories after raw CAB extraction, with E-only roots."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import msilib
from pathlib import Path, PurePath
import shutil
import sys

msi = Path(sys.argv[1]).resolve()
raw_root = Path(sys.argv[2]).resolve()
output_root = Path(sys.argv[3]).resolve()
install_root = Path(sys.argv[4]).resolve()
if not output_root.is_absolute() or not install_root.is_absolute():
    raise ValueError("Output roots must be absolute")
if output_root.drive.lower() != "e:" or install_root.drive.lower() != "e:":
    raise ValueError("This recovery tool is restricted to E-drive outputs")
database = msilib.OpenDatabase(str(msi), 0)

def rows(table):
    view = database.OpenView(f"SELECT * FROM {table}")
    view.Execute(None)
    result = []
    for record in iter(view.Fetch, None):
        result.append([record.GetString(index) for index in range(1, record.GetFieldCount() + 1)])
    return result

directories = {row[0]: (row[1], row[2]) for row in rows("Directory")}
components = {row[0]: row[2] for row in rows("Component")}
files = rows("File")
root_map = {
    "TARGETDIR": raw_root,
    "INSTALLDIR": install_root,
    "EPICAPPDATA": output_root / "ProgramData",
    "APPDATA": output_root / "AppData",
    "ProgramMenuFolder": output_root / "Shortcuts" / "Programs",
    "DesktopFolder": output_root / "Shortcuts" / "Desktop",
}
cache = {}

def directory_path(key):
    if key in cache:
        return cache[key]
    if key in root_map:
        return root_map[key]
    if key not in directories:
        raise KeyError(f"Unknown MSI directory: {key}")
    parent, name = directories[key]
    name = name.split("|")[-1]
    if not parent:
        result = output_root / "OtherRoots" / key
    else:
        base = directory_path(parent)
        result = base if name == "." else base / name
    resolved = result.resolve()
    allowed = [output_root.resolve(), install_root.resolve(), raw_root.resolve()]
    if not any(resolved == root or root in resolved.parents for root in allowed):
        raise ValueError(f"MSI directory escapes approved output roots: {key}")
    cache[key] = resolved
    return resolved

mapped = []
missing = []
size_mismatches = []
def file_hash(path):
    value = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()

reused_existing_count = 0
for file_key, component_key, file_name, expected_size, *_ in files:
    raw = raw_root / file_key
    if not raw.is_file():
        missing.append(file_key)
        continue
    if component_key not in components:
        raise KeyError(f"Unknown component for {file_key}")
    actual_size = raw.stat().st_size
    if actual_size != int(expected_size):
        size_mismatches.append({"file": file_key, "expected": int(expected_size), "actual": actual_size})
        continue
    short_name = file_name.split("|")[-1]
    if not short_name or short_name in {".", ".."} or Path(short_name).name != short_name:
        raise ValueError(f"Unsafe MSI filename: {file_name}")
    destination = directory_path(components[component_key]) / short_name
    reused = False
    if destination.exists():
        if file_hash(destination) != file_hash(raw):
            raise FileExistsError(f"Existing destination differs from MSI payload: {destination}")
        reused = True
        reused_existing_count += 1
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(raw, destination)
    mapped.append({"file_key": file_key, "destination": str(destination), "bytes": actual_size, "reused": reused})

launcher = install_root / "Launcher" / "Portal" / "Binaries" / "Win64" / "EpicGamesLauncher.exe"
report = {
    "created_at": datetime.now(timezone.utc).isoformat(),
    "msi": str(msi),
    "raw_root": str(raw_root),
    "output_root": str(output_root),
    "install_root": str(install_root),
    "msi_file_rows": len(files),
    "mapped_file_count": len(mapped),
    "reused_existing_count": reused_existing_count,
    "missing_raw_count": len(missing),
    "missing_raw_files": missing,
    "size_mismatches": size_mismatches,
    "launcher": str(launcher),
    "launcher_exists": launcher.is_file(),
    "status": "FILES_RESTORED_NOT_INSTALLED",
    "mapped_files": mapped,
}
report_path = output_root / "file-layout-restoration.json"
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("MSI_LAYOUT_RESTORED", json.dumps({"mapped": len(mapped), "missing": len(missing),
      "size_mismatches": len(size_mismatches), "launcher_exists": launcher.is_file()}), flush=True)
