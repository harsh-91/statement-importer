# Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import os
import platform
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import webbrowser
import zipfile
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from urllib.parse import quote

from .config import CONFIG_PATH, load_settings
from .database import test_connection
from .local_postgres import DATA_DIR, LOCAL_STATE_DIR, LOG_PATH, METADATA_PATH, choose_port, find_postgres_bin
from .version import __version__

DIAGNOSTIC_DIR = LOCAL_STATE_DIR / "diagnostics"
EVENT_LOG = DIAGNOSTIC_DIR / "setup-events.jsonl"
REPORT_DIR = Path.home() / "Documents" / "Statement Importer Reports"
MAX_EVENT_LOG_BYTES = 512 * 1024
_event_lock = threading.Lock()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sanitize_text(value: object) -> str:
    """Remove credentials and user-specific paths before support data is written."""
    text = str(value or "")
    home = str(Path.home())
    if home:
        text = re.sub(re.escape(home), "%USERPROFILE%", text, flags=re.IGNORECASE)
    username = os.environ.get("USERNAME") or os.environ.get("USER")
    if username:
        text = re.sub(re.escape(username), "[WINDOWS_USER]", text, flags=re.IGNORECASE)
    text = re.sub(r"(?i)postgres(?:ql)?://[^\s@]+@", "postgresql://[REDACTED]@", text)
    text = re.sub(
        r"(?i)\b(password|passwd|pwd|secret|token|api[_ -]?key)\b\s*[:=]\s*[^\s,;]+",
        lambda match: f"{match.group(1)}=[REDACTED]",
        text,
    )
    text = re.sub(
        r"\b(?!127\.0\.0\.1\b)(?!0\.0\.0\.0\b)(?:\d{1,3}\.){3}\d{1,3}\b",
        "[REMOTE_ADDRESS]",
        text,
    )
    text = re.sub(r'(?i)\b(user|database)\s+"[^"]+"', lambda match: f'{match.group(1)} "[REDACTED]"', text)
    text = re.sub(r'(?i)\bserver at "[^"]+"', 'server at "[REDACTED]"', text)
    return text[:4000]


def record_setup_event(run_id: str, status: str, message: object, *, mode: str | None = None) -> None:
    payload = {
        "timestamp_utc": utc_now(),
        "app_version": __version__,
        "run_id": re.sub(r"[^a-zA-Z0-9-]", "", run_id)[:40],
        "status": status,
        "message": sanitize_text(message),
    }
    if mode in {"automatic", "manual", "startup"}:
        payload["mode"] = mode
    try:
        with _event_lock:
            DIAGNOSTIC_DIR.mkdir(parents=True, exist_ok=True)
            if EVENT_LOG.exists() and EVENT_LOG.stat().st_size > MAX_EVENT_LOG_BYTES:
                tail = EVENT_LOG.read_bytes()[-(MAX_EVENT_LOG_BYTES // 2):]
                first_newline = tail.find(b"\n")
                EVENT_LOG.write_bytes(tail[first_newline + 1:] if first_newline >= 0 else b"")
            with EVENT_LOG.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(payload, ensure_ascii=True) + "\n")
    except OSError:
        pass


def start_setup_run(mode: str) -> str:
    run_id = secrets.token_hex(6)
    record_setup_event(run_id, "started", "Database setup started", mode=mode)
    return run_id


def _package_version(package: str) -> str:
    try:
        return version(package)
    except PackageNotFoundError:
        return "not detected"


def _check(name: str, status: str, detail: str, action: str = "") -> dict[str, str]:
    return {"name": name, "status": status, "detail": sanitize_text(detail), "action": action}


def _managed_metadata() -> tuple[int | None, str]:
    if not METADATA_PATH.exists():
        if DATA_DIR.exists() and any(DATA_DIR.iterdir()):
            return None, "A partial managed PostgreSQL data folder exists, but its app metadata is missing. It was preserved for safety."
        return None, "No app-managed PostgreSQL cluster has been created yet."
    try:
        payload = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        return int(payload["port"]), "Managed PostgreSQL metadata is readable."
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        return None, f"Managed PostgreSQL metadata cannot be read: {error}"


def _port_reachable(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def run_diagnostics() -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    is_windows = os.name == "nt"
    checks.append(_check(
        "Windows compatibility", "pass" if is_windows else "warn",
        f"{platform.system()} {platform.release()} build {platform.version()} ({platform.machine()})",
        "Statement Importer is supported on modern 64-bit Windows." if not is_windows else "",
    ))
    checks.append(_check(
        "Application runtime", "pass",
        f"Statement Importer {__version__}; Python {platform.python_version()}; WebView {_package_version('pywebview')}",
    ))
    try:
        bin_dir = find_postgres_bin()
        executable = bin_dir / ("postgres.exe" if os.name == "nt" else "postgres")
        result = subprocess.run(
            [str(executable), "--version"], capture_output=True, text=True,
            timeout=5, creationflags=0x08000000 if os.name == "nt" else 0,
        )
        detail = (result.stdout or result.stderr or "PostgreSQL tools detected").strip()
        checks.append(_check("PostgreSQL tools", "pass" if result.returncode == 0 else "warn", detail))
    except Exception as error:
        checks.append(_check(
            "PostgreSQL tools", "fail", str(error),
            "Install PostgreSQL, then reopen Statement Importer and retry setup.",
        ))

    port, metadata_detail = _managed_metadata()
    if port is None:
        partial = DATA_DIR.exists() and any(DATA_DIR.iterdir())
        state = "fail" if partial or METADATA_PATH.exists() else "warn"
        action = "Create a report before changing or removing the preserved data folder." if partial else "Retry automatic setup."
        checks.append(_check("Managed database state", state, metadata_detail, action))
        try:
            available_port = choose_port()
            checks.append(_check("Local port availability", "pass", f"Local port {available_port} is available for a managed database."))
        except Exception as error:
            checks.append(_check("Local port availability", "fail", str(error), "Close the conflicting program or choose an existing database."))
    else:
        reachable = _port_reachable(port)
        checks.append(_check(
            "Managed database port", "pass" if reachable else "fail",
            f"Local PostgreSQL port {port} is {'accepting connections' if reachable else 'not accepting connections'}.",
            "Retry setup; if it still fails, restart Windows and create a report." if not reachable else "",
        ))

    try:
        settings = load_settings()
        database_version = test_connection(settings)
        location = "this computer" if settings["POSTGRES_HOST"] in {"127.0.0.1", "localhost", "::1"} else "a remote server"
        checks.append(_check("Saved database connection", "pass", f"Connected to {location}. {database_version}"))
    except Exception as error:
        checks.append(_check(
            "Saved database connection", "fail", str(error),
            "Review Database Settings or retry automatic setup.",
        ))

    try:
        DIAGNOSTIC_DIR.mkdir(parents=True, exist_ok=True)
        probe = DIAGNOSTIC_DIR / ".write-test"
        probe.write_text("ok", encoding="ascii")
        probe.unlink()
        usage = shutil.disk_usage(DIAGNOSTIC_DIR)
        free_gb = usage.free / (1024 ** 3)
        status = "pass" if free_gb >= 1 else "warn"
        checks.append(_check("Local storage", status, f"Diagnostic storage is writable; {free_gb:.1f} GB free."))
    except OSError as error:
        checks.append(_check("Local storage", "fail", str(error), "Check folder permissions and available disk space."))
    return checks


def _safe_events() -> str:
    if not EVENT_LOG.exists():
        return ""
    try:
        lines = EVENT_LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-250:]
        return "\n".join(sanitize_text(line) for line in lines) + "\n"
    except OSError as error:
        return json.dumps({"error": sanitize_text(error)}) + "\n"


def create_diagnostic_bundle(checks: list[dict[str, str]] | None = None) -> Path:
    checks = checks or run_diagnostics()
    report_id = f"SI-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{secrets.token_hex(3).upper()}"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    target = REPORT_DIR / f"StatementImporter-Diagnostics-{report_id}.zip"
    report = {
        "report_id": report_id,
        "created_utc": utc_now(),
        "application_version": __version__,
        "system": {
            "os": platform.system(), "release": platform.release(),
            "build": platform.version(), "architecture": platform.machine(),
            "packaged": bool(getattr(sys, "frozen", False)),
        },
        "checks": checks,
        "evidence": {
            "config_present": CONFIG_PATH.exists(),
            "managed_metadata_present": METADATA_PATH.exists(),
            "managed_data_present": DATA_DIR.exists(),
            "postgres_log_present": LOG_PATH.exists(),
            "postgres_log_size_bytes": LOG_PATH.stat().st_size if LOG_PATH.exists() else 0,
        },
        "privacy": "No statements, transactions, database contents, passwords, API keys, or protected configuration values are included.",
    }
    readme = (
        "Statement Importer diagnostic bundle\n\n"
        "Review diagnostic-report.json and setup-events.jsonl before sharing.\n"
        "This bundle excludes statements, transaction data, database contents, passwords, API keys, "
        "and protected configuration values. PostgreSQL log contents are not collected.\n"
    )
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("diagnostic-report.json", json.dumps(report, indent=2, ensure_ascii=True))
        archive.writestr("setup-events.jsonl", _safe_events())
        archive.writestr("README.txt", readme)
    return target


def open_report_folder() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(REPORT_DIR)  # type: ignore[attr-defined]
    else:
        webbrowser.open(REPORT_DIR.as_uri())


def open_support_draft(bundle: Path) -> None:
    subject = quote(f"Statement Importer database setup report - {bundle.stem}")
    body = quote(
        "Hello Harsh,\n\nDatabase setup did not complete. I reviewed the diagnostic bundle and will attach it to this email.\n\n"
        f"Report file: {bundle.name}\n\nWhat I saw:\n\nSteps I tried:\n"
    )
    open_report_folder()
    webbrowser.open(f"mailto:harshnair02@gmail.com?subject={subject}&body={body}")
