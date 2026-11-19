"""Acquire selected free scenes through Blendkit's normal endpoint.

Source files are never modified. Signed delivery URLs remain in memory only.
No account tokens, browser cookies, purchases, or AI inputs are used.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import urllib.parse
import uuid

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "Evidence" / "acquisition"
ORIGINAL = ROOT / "SourceScenes" / "Original"
SELECTED = {
    "S01": {
        "base": "a14302f7-af57-42d2-a489-594cbcc51a6c",
        "version": "8d8e827b-91a1-44d1-ad66-b71506b75aba",
        "filename": "Cherry_Blossom_Spring_Village_Scene.blend",
    },
    "S10": {
        "base": "79860bde-017f-47ca-9e1c-d66f9c4afc3d",
        "filename": "Sanctuary_Arch.blend",
    },
    "F06": {
        "base": "7003efc9-d269-4d54-bb07-bd42b30dd200",
        "filename": "F06.blend",
    },
}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(path.name + ".pending")
    pending.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pending.replace(path)


def request_json(url):
    for attempt in range(3):
        process = subprocess.run(
            ["curl.exe", "--fail", "--location", "--silent", "--show-error",
             "--proto", "=https", "--proto-redir", "=https",
             "--connect-timeout", "12", "--max-time", "40", url],
            capture_output=True,
        )
        if process.returncode == 0:
            try:
                return json.loads(process.stdout)
            except (ValueError, UnicodeError):
                pass
        if attempt < 2:
            time.sleep(2)
    raise RuntimeError(f"Official JSON request failed after 3 attempts (curl exit {process.returncode})")


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def acquire(asset_id):
    spec = SELECTED[asset_id]
    receipt_path = EVIDENCE / f"{asset_id}-download-receipt.json"
    receipt = {"id": asset_id, "started_at": stamp(), "downloaded": False, "opened": False}
    try:
        metadata_path = EVIDENCE / f"{asset_id}-metadata.json"
        if metadata_path.exists():
            data = json.loads(metadata_path.read_text(encoding="utf-8"))
        elif spec.get("version"):
            data = request_json(f"https://www.blendkit.com/api/v1/assets/{spec['version']}/")
        else:
            query = urllib.parse.urlencode({"query": f"asset_base_id:{spec['base']}"})
            results = request_json("https://www.blendkit.com/api/v1/search/?" + query)["results"]
            matching = [x for x in results if x.get("assetBaseId") == spec["base"]]
            if len(matching) != 1:
                raise RuntimeError(f"Expected one exact asset, found {len(matching)}")
            data = matching[0]
            data = request_json(f"https://www.blendkit.com/api/v1/assets/{data['id']}/")
        assert data["assetBaseId"] == spec["base"]
        assert data["isFree"] is True and not data.get("isPrivate", False)
        assert data["license"] in {"royalty_free", "cc_zero"}
        write_json(metadata_path, data)
        files = [f for f in data["files"] if f["fileType"] == "blend" and not f.get("isThumbnail")]
        assert len(files) == 1, "Expected one original Blender source"
        entry = files[0]
        folder = ORIGINAL / asset_id
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / spec["filename"]
        expected = entry["fileUploadSize"]
        receipt.update({
            "title": data["name"], "asset_base_id": spec["base"], "asset_version_id": data["id"],
            "source_url": f"https://www.blendkit.com/asset-gallery-detail/{spec['base']}/",
            "license": data["license"], "is_free": True,
            "license_evidence_path": "Evidence/acquisition/" + metadata_path.name,
            "source_app_version": data.get("sourceAppVersion"),
            "expected_bytes": expected, "local_path": path.relative_to(ROOT).as_posix(),
            "download_endpoint": entry["downloadUrl"], "status": "LICENSE_VERIFIED",
        })
        write_json(receipt_path, receipt)
        if not path.exists():
            part = path.with_suffix(path.suffix + ".part")
            if shutil.disk_usage(ROOT).free < expected + 10 * 1024**3:
                raise RuntimeError("Insufficient free space")
            # Same public download endpoint and scene UUID used by the official add-on.
            delivery = request_json(entry["downloadUrl"] + "?" + urllib.parse.urlencode({"scene_uuid": str(uuid.uuid4())}))
            url = delivery["filePath"]
            assert urllib.parse.urlsplit(url).scheme == "https"
            receipt["status"] = "DOWNLOADING"
            write_json(receipt_path, receipt)
            print(f"{asset_id}: downloading {expected:,} bytes", flush=True)
            result = subprocess.run(
                ["curl.exe", "--fail", "--location", "--silent", "--show-error",
                 "--proto", "=https", "--proto-redir", "=https",
                 "--retry", "3", "--retry-delay", "3", "--connect-timeout", "15",
                 "--max-time", "1200", "--speed-limit", "4096", "--speed-time", "60",
                 "--continue-at", "-", "--output", str(part), url],
                capture_output=True,
            )
            if result.returncode:
                raise RuntimeError(f"Delivery failed (curl exit {result.returncode}); partial preserved")
            candidate = part
        else:
            candidate = path
        assert candidate.stat().st_size == expected, "Source length mismatch"
        with candidate.open("rb") as stream:
            magic = stream.read(12)
        assert magic.startswith((b"BLENDER", b"\x28\xb5\x2f\xfd", b"\x1f\x8b")), "Not a Blender container"
        sha = digest(candidate)
        if candidate != path:
            candidate.rename(path)
        receipt.update({"status": "DOWNLOADED", "downloaded": True, "actual_bytes": path.stat().st_size,
                        "sha256": sha, "magic_hex": magic.hex(), "completed_at": stamp(),
                        "baseline_status": "NOT_TESTED", "engine_import_status": "NOT_TESTED",
                        "build_whitelist": False})
        write_json(receipt_path, receipt)
        print(f"{asset_id}: DOWNLOADED {path.stat().st_size:,} bytes SHA256={sha}", flush=True)
    except Exception as error:
        receipt.update({"status": "DOWNLOAD_BLOCKED", "error": str(error), "updated_at": stamp()})
        write_json(receipt_path, receipt)
        print(f"{asset_id}: {receipt['error']}", flush=True)
        return False
    return True


if __name__ == "__main__":
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(acquire, SELECTED))
    raise SystemExit(0 if all(results) else 1)
