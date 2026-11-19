"""Extract the largest embedded MSI stream as a CAB and verify its signature."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Tools" / "acquisition" / "python-deps"))
import olefile

source = Path(sys.argv[1]).resolve()
destination = Path(sys.argv[2]).resolve()
if destination.exists():
    raise FileExistsError(f"Refusing to overwrite existing CAB: {destination}")
ole = olefile.OleFileIO(str(source))
streams = [entry for entry in ole.listdir() if len(entry) == 1]
largest = max(streams, key=lambda entry: ole.get_size(entry))
with ole.openstream(largest) as stream:
    if stream.read(4) != b"MSCF":
        raise RuntimeError("Largest embedded stream is not a CAB")
with ole.openstream(largest) as stream, destination.open("wb") as handle:
    shutil.copyfileobj(stream, handle, 8 * 1024 * 1024)
report = {
    "source": str(source),
    "source_sha256": sha256(source.read_bytes()).hexdigest(),
    "cab": str(destination),
    "actual_bytes": destination.stat().st_size,
    "sha256": sha256(destination.read_bytes()).hexdigest(),
    "embedded_stream_size": ole.get_size(largest),
    "magic": "MSCF",
}
destination.with_suffix(".extract.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("MSI_CAB_EXTRACTED", destination.stat().st_size, report["sha256"], flush=True)
