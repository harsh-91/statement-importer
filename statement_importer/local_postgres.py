# Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import os
import secrets
import shutil
import socket
import subprocess
import tempfile
from pathlib import Path

import psycopg
from psycopg import sql

from .config import CONFIG_DIR, _protect, _unprotect, save_settings
from .database import ensure_schema, test_connection


LOCAL_STATE_DIR = Path(os.environ.get("LOCALAPPDATA", CONFIG_DIR)) / "StatementImporter"
MANAGED_ROOT = LOCAL_STATE_DIR / "managed-postgresql"
DATA_DIR = MANAGED_ROOT / "data"
LOG_PATH = MANAGED_ROOT / "postgresql.log"
METADATA_PATH = MANAGED_ROOT / "cluster.json"
DEFAULT_PORT = 55432
APP_DATABASE = "account_statements"
OWNER_USER = "statement_owner"
APP_USER = "statement_app"
HIDDEN_PROCESS = 0x08000000 if os.name == "nt" else 0


class LocalPostgresError(RuntimeError):
    pass


def _version_key(path: Path) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in path.parent.parent.name.split("."))
    except ValueError:
        return (0,)


def find_postgres_bin() -> Path:
    initdb = shutil.which("initdb")
    if initdb:
        candidate = Path(initdb).resolve().parent
        if all((candidate / name).exists() for name in ("initdb.exe", "pg_ctl.exe")):
            return candidate
    root = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "PostgreSQL"
    candidates = sorted(root.glob("*/bin/initdb.exe"), key=_version_key, reverse=True)
    for candidate in candidates:
        if (candidate.parent / "pg_ctl.exe").exists():
            return candidate.parent
    raise LocalPostgresError(
        "PostgreSQL tools were not found. Install PostgreSQL from the setup wizard, then reopen Statement Importer."
    )


def _port_is_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def choose_port(start: int = DEFAULT_PORT, attempts: int = 31) -> int:
    for port in range(start, start + attempts):
        if _port_is_available(port):
            return port
    raise LocalPostgresError(f"No free local PostgreSQL port was found between {start} and {start + attempts - 1}.")


def _run(command: list[str], *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout,
            creationflags=HIDDEN_PROCESS,
        )
    except subprocess.TimeoutExpired as error:
        raise LocalPostgresError(
            f"PostgreSQL did not finish this step within {timeout} seconds. "
            "You can retry setup. Existing data has been preserved."
        ) from error
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "PostgreSQL command failed").strip()
        raise LocalPostgresError(message)
    return result


def _metadata() -> dict[str, str] | None:
    if not METADATA_PATH.exists():
        return None
    try:
        payload = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        return {
            "port": str(int(payload["port"])),
            "owner_password": _unprotect(payload["owner_password_protected"]),
            "app_password": _unprotect(payload["app_password_protected"]),
            "bin_dir": payload["bin_dir"],
        }
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        raise LocalPostgresError(f"The managed PostgreSQL configuration is damaged: {error}") from error


def _save_metadata(bin_dir: Path, port: int, owner_password: str, app_password: str) -> None:
    MANAGED_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "port": port,
        "bin_dir": str(bin_dir),
        "owner_password_protected": _protect(owner_password),
        "app_password_protected": _protect(app_password),
    }
    temporary = METADATA_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary.replace(METADATA_PATH)


def _settings(port: str, password: str, *, user: str = APP_USER, database: str = APP_DATABASE) -> dict[str, str]:
    return {
        "POSTGRES_HOST": "127.0.0.1",
        "POSTGRES_PORT": port,
        "POSTGRES_DB": database,
        "POSTGRES_USER": user,
        "POSTGRES_PASSWORD": password,
    }


def _start(bin_dir: Path, port: int) -> None:
    pg_ctl = bin_dir / "pg_ctl.exe"
    status = subprocess.run(
        [str(pg_ctl), "status", "-D", str(DATA_DIR)],
        capture_output=True,
        text=True,
        creationflags=HIDDEN_PROCESS,
        timeout=10,
    )
    if status.returncode == 0:
        return
    if not _port_is_available(port):
        raise LocalPostgresError(f"Local port {port} is already in use. Close the conflicting program and try again.")
    _run([
        str(pg_ctl), "start", "-D", str(DATA_DIR), "-l", str(LOG_PATH),
        "-o", f"-p {port} -h 127.0.0.1", "-w", "-t", "60",
    ])


def _initialize(bin_dir: Path, port: int, owner_password: str) -> None:
    if DATA_DIR.exists() and any(DATA_DIR.iterdir()):
        raise LocalPostgresError(
            "A partial local PostgreSQL data folder already exists. It was preserved for safety; see the managed-postgresql log."
        )
    MANAGED_ROOT.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    descriptor, password_path = tempfile.mkstemp(prefix="initdb-", suffix=".pwd", dir=MANAGED_ROOT)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as password_file:
            password_file.write(owner_password)
        _run([
            str(bin_dir / "initdb.exe"), "-D", str(DATA_DIR), "--username", OWNER_USER,
            "--pwfile", password_path, "--auth-host=scram-sha-256", "--auth-local=scram-sha-256",
            "--encoding=UTF8",
        ])
        with (DATA_DIR / "postgresql.conf").open("a", encoding="utf-8") as configuration:
            configuration.write(
                "\n# Statement Importer managed settings\n"
                "listen_addresses = '127.0.0.1'\n"
                f"port = {port}\n"
                "max_connections = 20\n"
            )
    finally:
        try:
            os.unlink(password_path)
        except FileNotFoundError:
            pass


def _create_application_database(port: int, owner_password: str, app_password: str) -> None:
    with psycopg.connect(
        host="127.0.0.1", port=port, dbname="postgres", user=OWNER_USER,
        password=owner_password, autocommit=True, connect_timeout=5,
        application_name="statement-importer-setup",
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (APP_USER,))
            if cursor.fetchone():
                cursor.execute(
                    sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT").format(
                        sql.Identifier(APP_USER), sql.Literal(app_password)
                    )
                )
            else:
                cursor.execute(
                    sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT").format(
                        sql.Identifier(APP_USER), sql.Literal(app_password)
                    )
                )
            cursor.execute("SELECT 1 FROM pg_database WHERE datname=%s", (APP_DATABASE,))
            if not cursor.fetchone():
                cursor.execute(
                    sql.SQL("CREATE DATABASE {} OWNER {} ENCODING 'UTF8'").format(
                        sql.Identifier(APP_DATABASE), sql.Identifier(APP_USER)
                    )
                )


def provision_managed_postgres(progress=lambda message: None) -> dict[str, str]:
    progress("Checking your local database configuration")
    metadata = _metadata()
    if metadata:
        bin_dir = Path(metadata["bin_dir"])
        if not (bin_dir / "pg_ctl.exe").exists():
            bin_dir = find_postgres_bin()
        port = int(metadata["port"])
        progress("Starting your existing local database (up to 60 seconds)")
        _start(bin_dir, port)
        progress("Checking database access and preparing tables")
        _create_application_database(port, metadata["owner_password"], metadata["app_password"])
        settings = _settings(str(port), metadata["app_password"])
        test_connection(settings)
        ensure_schema(settings)
        save_settings(settings)
        return settings

    progress("Finding PostgreSQL tools")
    bin_dir = find_postgres_bin()
    port = choose_port()
    owner_password = secrets.token_urlsafe(32)
    app_password = secrets.token_urlsafe(32)
    progress("Creating local database storage (up to 120 seconds)")
    _initialize(bin_dir, port, owner_password)
    _save_metadata(bin_dir, port, owner_password, app_password)
    progress("Starting your local database (up to 60 seconds)")
    _start(bin_dir, port)
    try:
        progress("Preparing database access and transaction tables")
        _create_application_database(port, owner_password, app_password)
        settings = _settings(str(port), app_password)
        ensure_schema(settings)
        save_settings(settings)
        return settings
    except Exception:
        try:
            _run([str(bin_dir / "pg_ctl.exe"), "stop", "-D", str(DATA_DIR), "-m", "fast", "-w"], timeout=60)
        except LocalPostgresError:
            pass
        raise


def start_managed_postgres_if_present() -> bool:
    metadata = _metadata()
    if not metadata:
        return False
    bin_dir = Path(metadata["bin_dir"])
    if not (bin_dir / "pg_ctl.exe").exists():
        bin_dir = find_postgres_bin()
    _start(bin_dir, int(metadata["port"]))
    return True


def managed_admin_settings() -> dict[str, str] | None:
    metadata = _metadata()
    if not metadata:
        return None
    return _settings(metadata["port"], metadata["owner_password"], user=OWNER_USER)
