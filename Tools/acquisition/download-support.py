"""Download public support files; do not install or execute downloaded code."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import base64
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "Evidence" / "acquisition"
DOWNLOADS = ROOT / "Downloads"


def fetch(job):
    name, url, relative, integrity, kind = job
    target = DOWNLOADS / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    receipt = {"name": name, "source_url": url, "local_path": target.relative_to(ROOT).as_posix(),
               "downloaded": False, "executed": False, "started_at": datetime.now(timezone.utc).isoformat()}
    try:
        candidate = target if target.exists() else target.with_name(target.name + ".part")
        if candidate != target:
            result = subprocess.run(
                ["curl.exe", "--fail", "--location", "--silent", "--show-error",
                 "--proto", "=https", "--proto-redir", "=https", "--retry", "2",
                 "--connect-timeout", "12", "--max-time", "600", "--continue-at", "-",
                 "--output", str(candidate), url], capture_output=True,
            )
            if result.returncode:
                raise RuntimeError(f"curl exit {result.returncode}")
        raw = candidate.read_bytes()
        if integrity:
            algorithm, expected = integrity.split("-", 1)
            assert base64.b64encode(hashlib.new(algorithm, raw).digest()).decode() == expected, "Registry integrity mismatch"
        if kind == "zip":
            with zipfile.ZipFile(candidate) as archive:
                assert archive.testzip() is None, "ZIP CRC failed"
                receipt["archive_file_count"] = len(archive.infolist())
        elif kind == "tgz":
            with tarfile.open(candidate, "r:gz") as archive:
                member = archive.extractfile("package/package.json")
                package = json.load(member)
                receipt.update({"package": package["name"], "version": package["version"],
                                "dependencies": package.get("dependencies", {}), "license": package.get("license")})
        elif kind == "json":
            parsed = json.loads(raw)
            assert "openapi" in parsed or "swagger" in parsed, "Not an OpenAPI schema"
            receipt["schema_version"] = parsed.get("openapi", parsed.get("swagger"))
        elif kind == "html":
            assert b"<html" in raw.lower() or b"<!doctype" in raw.lower(), "Not HTML"
        elif kind == "msi":
            assert raw.startswith(bytes.fromhex("d0cf11e0a1b11ae1")), "Not a Windows Installer container"
        if candidate != target:
            candidate.rename(target)
        receipt.update({"downloaded": True, "status": "DOWNLOADED", "actual_bytes": len(raw),
                        "sha256": hashlib.sha256(raw).hexdigest(), "integrity": integrity,
                        "completed_at": datetime.now(timezone.utc).isoformat()})
        print(f"{name}: DOWNLOADED {len(raw):,} bytes", flush=True)
    except Exception as error:
        receipt.update({"status": "DOWNLOAD_BLOCKED", "error": str(error)})
        print(f"{name}: {receipt['error']}", flush=True)
    (EVIDENCE / (name + "-download-receipt.json")).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt


if __name__ == "__main__":
    page = (EVIDENCE / "blendkit-download-page.html").read_text(encoding="utf-8")
    addons = [html.unescape(x) for x in re.findall(r'href=["\x27]([^"\x27]+\.zip[^"\x27]*)', page)]
    blender_addon = next(x for x in addons if x.startswith("/addon-download/blenderkit.zip"))
    jobs = [("blendkit-addon", "https://www.blendkit.com" + blender_addon,
             "Blendkit/blendkit-v3.21.3.261002.zip", None, "zip")]
    for package, version in [("lux3d", "1.9.0"), ("asset", "1.3.0"), ("core", "1.3.0")]:
        data = json.loads((EVIDENCE / f"aholo-sdk-{package}-{version}-package-metadata.json").read_text(encoding="utf-8"))
        jobs.append((f"aholo-sdk-{package}", data["dist"]["tarball"],
                     f"Aholo/aholo-sdk-{package}-{version}.tgz", data["dist"]["integrity"], "tgz"))
    jobs.extend([
        ("aholo-openapi", "https://labs.aholo.ai/api-docs/en/openapi.json", "Aholo/openapi-2026-11-11.json", None, "json"),
        ("aholo-typescript-docs", "https://labs.aholo.ai/api-docs/en/sdk/typescript", "Aholo/typescript-sdk-2026-11-11.html", None, "html"),
        ("blendkit-license", "https://www.blendkit.com/docs/licenses/", "Licenses/blendkit-license-2026-11-11.html", None, "html"),
    ])
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(fetch, jobs))
    (EVIDENCE / "support-downloads.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(0 if all(x["downloaded"] for x in rows) else 1)
