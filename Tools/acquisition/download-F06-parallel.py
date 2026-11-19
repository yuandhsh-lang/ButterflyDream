"""Resume F06 from its preserved prefix using ranges on Blendkit's official delivery URL."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import time
import urllib.parse
import uuid

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "Evidence" / "acquisition"
FINAL = ROOT / "SourceScenes" / "Original" / "F06" / "F06.blend"
OLD_PART = FINAL.with_suffix(".blend.part")
CACHE = ROOT / "Downloads" / "Blendkit" / "F06-segments"
PREFIX = CACHE / "prefix.bin"
RECEIPT = EVIDENCE / "F06-download-receipt.json"
WORKERS = 6
CHUNK = 8 * 1024 * 1024


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    value = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def save_receipt(data):
    pending = RECEIPT.with_suffix(".json.pending")
    pending.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pending.replace(RECEIPT)


def download_segment(url, start, end):
    target = CACHE / f"segment-{start:010d}.bin"
    expected = end - start + 1
    if target.exists() and target.stat().st_size == expected:
        return target
    if target.exists():
        raise RuntimeError(f"Unexpected completed-segment length at offset {start}")
    partial = target.with_suffix(".bin.part")
    existing = partial.stat().st_size if partial.exists() else 0
    if existing > expected:
        invalid = partial.with_name(partial.name + ".invalid-retry")
        if invalid.exists():
            raise RuntimeError(f"Invalid retry segment already exists at offset {start}")
        partial.replace(invalid)
        existing = 0
    for attempt in range(3):
        existing = partial.stat().st_size if partial.exists() else 0
        if existing == expected:
            break
        with partial.open("ab") as handle:
            result = subprocess.run([
                "curl.exe", "--fail", "--location", "--silent", "--show-error",
                "--proto", "=https", "--proto-redir", "=https",
                "--connect-timeout", "15", "--max-time", "900",
                "--speed-limit", "1024", "--speed-time", "60",
                "--range", f"{start + existing}-{end}", url,
            ], stdout=handle, stderr=subprocess.PIPE)
        if result.returncode and attempt == 2:
            raise RuntimeError(f"Official range download failed at offset {start}, curl exit {result.returncode}")
        if result.returncode:
            time.sleep(2 * (attempt + 1))
    if partial.stat().st_size != expected:
        raise RuntimeError(f"Range length mismatch at offset {start}")
    partial.replace(target)
    print(f"F06 segment complete: {start}-{end}", flush=True)
    return target


receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
receipt.pop("error", None)
metadata = json.loads((EVIDENCE / "F06-metadata.json").read_text(encoding="utf-8"))
entry = next(item for item in metadata["files"] if item["fileType"] == "blend" and not item.get("isThumbnail"))
expected_bytes = entry["fileUploadSize"]
try:
    if FINAL.exists():
        if FINAL.stat().st_size != expected_bytes:
            raise RuntimeError("Existing F06 final file has the wrong length")
        receipt.update({"status": "DOWNLOADED", "downloaded": True, "actual_bytes": expected_bytes,
                        "sha256": digest(FINAL), "completed_at": stamp()})
        save_receipt(receipt)
        print("F06 already downloaded; no network request", flush=True)
        raise SystemExit(0)

    CACHE.mkdir(parents=True, exist_ok=True)
    if OLD_PART.exists():
        if PREFIX.exists():
            raise RuntimeError("Both old part and preserved prefix exist; refusing to choose between them")
        OLD_PART.replace(PREFIX)
    prefix_size = PREFIX.stat().st_size if PREFIX.exists() else 0
    if prefix_size > expected_bytes:
        raise RuntimeError("Preserved prefix exceeds expected source length")
    if shutil.disk_usage(ROOT).free < expected_bytes + 10 * 1024**3:
        raise RuntimeError("Insufficient free space")

    ranges = [(start, min(start + CHUNK, expected_bytes) - 1)
              for start in range(prefix_size, expected_bytes, CHUNK)]
    receipt.update({"status": "DOWNLOADING", "download_method": "Parallel HTTP ranges from the official Blendkit delivery URL",
                    "parallel_workers": WORKERS, "prefix_bytes_reused": prefix_size,
                    "signed_url_recorded": False, "updated_at": stamp()})
    save_receipt(receipt)
    if ranges:
        delivery_url = f"{entry['downloadUrl']}?{urllib.parse.urlencode({'scene_uuid': str(uuid.uuid4())})}"
        response = subprocess.run([
            "curl.exe", "--fail", "--location", "--silent", "--show-error",
            "--proto", "=https", "--proto-redir", "=https", "--retry", "3",
            "--retry-delay", "3", "--connect-timeout", "15", "--max-time", "90", delivery_url,
        ], capture_output=True)
        if response.returncode:
            raise RuntimeError(f"Official delivery request failed with curl exit {response.returncode}")
        delivery = json.loads(response.stdout)
        url = delivery["filePath"]
        if urllib.parse.urlsplit(url).scheme != "https":
            raise RuntimeError("Official delivery did not provide an HTTPS URL")
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            segments = list(pool.map(lambda item: download_segment(url, *item), ranges))
    else:
        segments = []

    assembling = FINAL.with_suffix(".blend.assemble")
    with assembling.open("wb") as output:
        if PREFIX.exists():
            with PREFIX.open("rb") as source:
                shutil.copyfileobj(source, output, 8 * 1024 * 1024)
        for segment in segments:
            with segment.open("rb") as source:
                shutil.copyfileobj(source, output, 8 * 1024 * 1024)
    if assembling.stat().st_size != expected_bytes:
        raise RuntimeError("Assembled source length mismatch")
    with assembling.open("rb") as handle:
        magic = handle.read(12)
    if not magic.startswith((b"BLENDER", b"\x28\xb5\x2f\xfd", b"\x1f\x8b")):
        raise RuntimeError("Assembled file is not a Blender container")
    source_sha256 = digest(assembling)
    assembling.replace(FINAL)
    receipt.update({"status": "DOWNLOADED", "downloaded": True, "opened": False,
                    "local_path": FINAL.relative_to(ROOT).as_posix(), "actual_bytes": expected_bytes,
                    "sha256": source_sha256, "magic_hex": magic.hex(), "completed_at": stamp(),
                    "baseline_status": "NOT_TESTED", "engine_import_status": "NOT_TESTED",
                    "build_whitelist": False})
    save_receipt(receipt)
    print(f"F06: DOWNLOADED {expected_bytes:,} bytes SHA256={source_sha256}", flush=True)
except SystemExit:
    raise
except Exception as error:
    receipt.update({"status": "DOWNLOAD_BLOCKED", "downloaded": False,
                    "error": str(error), "updated_at": stamp()})
    save_receipt(receipt)
    print(f"F06: {error}", flush=True)
    raise
