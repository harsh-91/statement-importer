# Created by Harsh (@harsh-91) | Made in India
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .version import __version__


REPOSITORY = "harsh-91/statement-importer"
LATEST_RELEASE_API = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
UPDATE_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "StatementImporter" / "updates"
CACHE_PATH = UPDATE_DIR / "latest.json"
READY_PATH = UPDATE_DIR / "ready.json"
MAX_INSTALLER_BYTES = 250 * 1024 * 1024
MAX_METADATA_BYTES = 512 * 1024
ALLOWED_HOSTS = {
    "api.github.com", "github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"
}
HIDDEN_PROCESS = 0x08000000 if os.name == "nt" else 0


class UpdateError(RuntimeError):
    pass


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, new_url):
        _validate_url(new_url)
        return super().redirect_request(request, fp, code, msg, headers, new_url)


OPENER = urllib.request.build_opener(SafeRedirectHandler())


def _validate_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS or parsed.username or parsed.password:
        raise UpdateError("The update service returned an untrusted download address")


def _open(url: str, timeout: int = 15):
    _validate_url(url)
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"StatementImporter/{__version__}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        return OPENER.open(request, timeout=timeout)
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise UpdateError(f"Could not reach the official update service: {error}") from error


def _read_limited(response, limit: int) -> bytes:
    payload = response.read(limit + 1)
    if len(payload) > limit:
        raise UpdateError("The update service response exceeded the safety limit")
    return payload


def _version_tuple(value: str) -> tuple[int, int, int]:
    clean = value.strip().removeprefix("v")
    parts = clean.split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise UpdateError(f"Unsupported release version: {value}")
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def _asset(release: dict[str, Any], name: str) -> dict[str, Any]:
    assets = release.get("assets", [])
    if not isinstance(assets, list):
        raise UpdateError("The update service returned invalid release assets")
    matches = [
        item for item in assets
        if isinstance(item, dict) and item.get("name") == name and item.get("state") == "uploaded"
    ]
    if len(matches) != 1:
        raise UpdateError(f"Release asset is missing or ambiguous: {name}")
    asset = matches[0]
    _validate_url(str(asset.get("browser_download_url", "")))
    return asset


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def check_latest_release() -> dict[str, Any]:
    try:
        with _open(LATEST_RELEASE_API) as response:
            release = json.loads(_read_limited(response, MAX_METADATA_BYTES).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise UpdateError("The update service returned invalid release metadata") from error
    if not isinstance(release, dict):
        raise UpdateError("The update service returned invalid release metadata")
    version = str(release.get("tag_name", "")).removeprefix("v")
    latest = _version_tuple(version)
    current = _version_tuple(__version__)
    installer_name = f"StatementImporter-{version}-Setup-x64.exe"
    installer = _asset(release, installer_name)
    checksums = _asset(release, "SHA256SUMS.txt")
    result = {
        "current_version": __version__,
        "latest_version": version,
        "update_available": latest > current,
        "release_url": str(release.get("html_url", "")),
        "release_name": str(release.get("name") or release.get("tag_name") or version),
        "published_at": release.get("published_at"),
        "notes": str(release.get("body") or "")[:12000],
        "installer": {
            "name": installer_name,
            "url": installer["browser_download_url"],
            "size": int(installer.get("size") or 0),
            "digest": str(installer.get("digest") or ""),
        },
        "checksums_url": checksums["browser_download_url"],
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    _validate_url(result["release_url"])
    _write_json_atomic(CACHE_PATH, result)
    return result


def cached_update() -> dict[str, Any] | None:
    if not CACHE_PATH.exists():
        return None
    try:
        payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        is_newer = _version_tuple(str(payload.get("latest_version", ""))) > _version_tuple(__version__)
        return payload if is_newer else None
    except (OSError, json.JSONDecodeError, UpdateError):
        return None


def _expected_checksum(text: str, filename: str) -> str:
    matches = []
    for raw_line in text.splitlines():
        parts = raw_line.strip().split()
        if len(parts) >= 2 and parts[-1].lstrip("*") == filename and len(parts[0]) == 64:
            matches.append(parts[0].upper())
    if len(matches) != 1 or any(character not in "0123456789ABCDEF" for character in matches[0]):
        raise UpdateError("The release checksum manifest is missing or invalid")
    return matches[0]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def authenticode_status(path: Path) -> dict[str, str]:
    if os.name != "nt":
        raise UpdateError("Authenticode verification is available only on Windows")
    environment = os.environ.copy()
    environment["STATEMENT_IMPORTER_UPDATE"] = str(path)
    script = (
        "$s=Get-AuthenticodeSignature -LiteralPath $env:STATEMENT_IMPORTER_UPDATE;"
        "[pscustomobject]@{Status=[string]$s.Status;Subject=[string]$s.SignerCertificate.Subject;"
        "Thumbprint=[string]$s.SignerCertificate.Thumbprint}|ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        env=environment, capture_output=True, text=True, timeout=30, creationflags=HIDDEN_PROCESS,
    )
    environment["STATEMENT_IMPORTER_UPDATE"] = ""
    if result.returncode != 0:
        raise UpdateError(result.stderr.strip() or "Authenticode verification failed")
    try:
        signature = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise UpdateError("Windows returned an invalid signature-verification result") from error
    subject = str(signature.get("Subject") or "")
    if signature.get("Status") != "Valid" or "SignPath Foundation" not in subject:
        raise UpdateError("The installer is not validly signed by SignPath Foundation; installation was blocked")
    return {"status": "Valid", "subject": subject, "thumbprint": str(signature.get("Thumbprint") or "")}


def download_verified_update() -> dict[str, Any]:
    release = check_latest_release()
    if not release["update_available"]:
        raise UpdateError("This application is already up to date")
    installer = release["installer"]
    if installer["size"] <= 0 or installer["size"] > MAX_INSTALLER_BYTES:
        raise UpdateError("The installer size is outside the permitted safety range")
    with _open(release["checksums_url"]) as response:
        checksum_text = _read_limited(response, 64 * 1024).decode("utf-8")
    expected = _expected_checksum(checksum_text, installer["name"])
    api_digest = installer["digest"]
    if api_digest and api_digest.lower() != f"sha256:{expected.lower()}":
        raise UpdateError("GitHub's asset digest does not match the published checksum manifest")

    UPDATE_DIR.mkdir(parents=True, exist_ok=True)
    READY_PATH.unlink(missing_ok=True)
    target = UPDATE_DIR / installer["name"]
    partial = target.with_suffix(target.suffix + ".partial")
    digest = hashlib.sha256()
    size = 0
    try:
        with _open(installer["url"], timeout=60) as response, partial.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_INSTALLER_BYTES:
                    raise UpdateError("The downloaded installer exceeded the safety limit")
                digest.update(chunk)
                output.write(chunk)
        if size != installer["size"] or digest.hexdigest().upper() != expected:
            raise UpdateError("The downloaded installer failed SHA-256 verification")
        signature = authenticode_status(partial)
        partial.replace(target)
        ready = {
            "path": str(target), "version": release["latest_version"], "sha256": expected,
            "signature": signature, "verified_at": datetime.now(timezone.utc).isoformat(),
        }
        _write_json_atomic(READY_PATH, ready)
        return ready
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def verified_update() -> dict[str, Any] | None:
    if not READY_PATH.exists():
        return None
    try:
        ready = json.loads(READY_PATH.read_text(encoding="utf-8"))
        path = Path(ready["path"])
        version = str(ready["version"])
        expected_name = f"StatementImporter-{version}-Setup-x64.exe"
        if _version_tuple(version) <= _version_tuple(__version__):
            return None
        if path.name != expected_name or path.resolve().parent != UPDATE_DIR.resolve():
            return None
        checksum = str(ready["sha256"])
        if len(checksum) != 64 or any(character not in "0123456789ABCDEF" for character in checksum):
            return None
        if not path.is_file() or _sha256_file(path) != checksum:
            return None
        authenticode_status(path)
        return ready
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, UpdateError):
        return None


def launch_verified_update() -> None:
    ready = verified_update()
    if not ready:
        raise UpdateError("No verified update is ready to install")
    subprocess.Popen([ready["path"]], cwd=str(Path(ready["path"]).parent))


def start_background_check(enabled: bool) -> None:
    if enabled:
        threading.Thread(target=_background_check, name="update-check", daemon=True).start()


def _background_check() -> None:
    try:
        check_latest_release()
    except UpdateError:
        pass
