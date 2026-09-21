# Created by Harsh (@harsh-91) | Made in India
from __future__ import annotations

import os
import secrets
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from psycopg import sql

from .config import load_settings
from .database import connect


BACKUP_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "StatementImporter" / "backups"


def _postgres_tool(name: str) -> Path:
    executable = shutil.which(name)
    if executable:
        return Path(executable)
    root = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "PostgreSQL"
    candidates = sorted(root.glob(f"*/bin/{name}.exe"), reverse=True)
    if not candidates:
        raise RuntimeError(f"{name}.exe was not found. Install PostgreSQL client tools first.")
    return candidates[0]


def create_backup() -> Path:
    settings = load_settings()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = BACKUP_DIR / f"statement-importer-{stamp}.backup"
    partial = target.with_suffix(".partial")
    environment = os.environ.copy()
    environment["PGPASSWORD"] = settings["POSTGRES_PASSWORD"]
    command = [
        str(_postgres_tool("pg_dump")), "--format=custom", "--no-owner", "--no-privileges",
        "--host", settings["POSTGRES_HOST"], "--port", settings["POSTGRES_PORT"],
        "--username", settings["POSTGRES_USER"], "--file", str(partial), settings["POSTGRES_DB"],
    ]
    try:
        result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=600,
                                creationflags=0x08000000 if os.name == "nt" else 0)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "pg_dump failed")
        verify = subprocess.run([str(_postgres_tool("pg_restore")), "--list", str(partial)],
                                capture_output=True, text=True, timeout=120,
                                creationflags=0x08000000 if os.name == "nt" else 0)
        if verify.returncode != 0 or partial.stat().st_size == 0:
            raise RuntimeError("The backup was created but failed verification")
        partial.replace(target)
        return target
    finally:
        environment["PGPASSWORD"] = ""
        if partial.exists():
            partial.unlink()


def list_backups(limit: int = 25) -> list[dict[str, str | int]]:
    if not BACKUP_DIR.exists():
        return []
    files = sorted(BACKUP_DIR.glob("*.backup"), key=lambda path: path.stat().st_mtime, reverse=True)[:limit]
    return [{"name": path.name, "size": path.stat().st_size,
             "created": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")}
            for path in files]


def create_reporting_user(admin_user: str = "", admin_password: str = "") -> dict[str, str]:
    settings = load_settings()
    from .local_postgres import managed_admin_settings
    admin_settings = managed_admin_settings()
    if admin_settings is None:
        if not admin_user.strip() or not admin_password:
            raise RuntimeError("PostgreSQL administrator username and password are required")
        admin_settings = dict(settings)
        admin_settings["POSTGRES_USER"] = admin_user.strip()
        admin_settings["POSTGRES_PASSWORD"] = admin_password
    username = "statement_reader_" + secrets.token_hex(4)
    password = secrets.token_urlsafe(24)
    with connect(admin_settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT").format(
                sql.Identifier(username), sql.Literal(password)))
            cursor.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                sql.Identifier(settings["POSTGRES_DB"]), sql.Identifier(username)))
            cursor.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(username)))
            cursor.execute(sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}").format(sql.Identifier(username)))
            cursor.execute(sql.SQL("ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public GRANT SELECT ON TABLES TO {}").format(
                sql.Identifier(settings["POSTGRES_USER"]), sql.Identifier(username)))
            cursor.execute("INSERT INTO audit_log(event_type,event_data) VALUES('reporting_user_created',jsonb_build_object('username',%s))",
                           (username,))
    return {"host": settings["POSTGRES_HOST"], "port": settings["POSTGRES_PORT"],
            "database": settings["POSTGRES_DB"], "username": username, "password": password}
