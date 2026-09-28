# Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import base64
import ctypes
import json
import os
import sys
from ctypes import wintypes
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = (Path.home() / "Library" / "Application Support" / "StatementImporter"
              if sys.platform == "darwin" else Path(os.environ.get("APPDATA", Path.home())) / "StatementImporter")
CONFIG_PATH = CONFIG_DIR / "config.json"
REQUIRED = {"POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"}


class ConfigError(RuntimeError):
    pass


def _mac_key() -> bytes:
    """Keep the data-encryption key in the current user's macOS Keychain."""
    import keyring
    from cryptography.fernet import Fernet

    service = "com.harsh91.statement-importer"
    account = "local-data-key"
    try:
        value = keyring.get_password(service, account)
        if value is None:
            value = Fernet.generate_key().decode("ascii")
            keyring.set_password(service, account, value)
        return value.encode("ascii")
    except Exception as error:
        raise ConfigError("Mac Keychain is unavailable; unlock your login Keychain and retry") from error


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob(data: bytes) -> tuple[DATA_BLOB, ctypes.Array]:
    buffer = ctypes.create_string_buffer(data)
    return DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))), buffer


def _protect(value: str) -> str:
    if sys.platform == "darwin":
        from cryptography.fernet import Fernet
        return "fernet:" + Fernet(_mac_key()).encrypt(value.encode("utf-8")).decode("ascii")
    if os.name != "nt":
        raise ConfigError("Protected storage is unavailable on this operating system")
    source, keepalive = _blob(value.encode("utf-8"))
    output = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(source), "StatementImporter", None, None, None, 0, ctypes.byref(output)
    ):
        raise ctypes.WinError()
    try:
        protected = ctypes.string_at(output.pbData, output.cbData)
        return base64.b64encode(protected).decode("ascii")
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)


def _unprotect(value: str) -> str:
    if sys.platform == "darwin":
        from cryptography.fernet import Fernet, InvalidToken
        if not value.startswith("fernet:"):
            raise ConfigError("The saved secret is not protected by this Mac's Keychain")
        try:
            return Fernet(_mac_key()).decrypt(value.removeprefix("fernet:").encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError) as error:
            raise ConfigError("The saved secret could not be decrypted with this Mac's Keychain") from error
    protected = base64.b64decode(value)
    if os.name != "nt":
        raise ConfigError("Protected storage is unavailable on this operating system")
    source, keepalive = _blob(protected)
    output = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(source), None, None, None, None, 0, ctypes.byref(output)
    ):
        raise ConfigError("The saved database password could not be decrypted for this Windows user")
    try:
        return ctypes.string_at(output.pbData, output.cbData).decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)


def protect_bytes(value: bytes) -> bytes:
    """Protect local temporary data for the current OS user."""
    encoded = base64.b64encode(value).decode("ascii")
    return _protect(encoded).encode("ascii")


def unprotect_bytes(value: bytes) -> bytes:
    try:
        encoded = _unprotect(value.decode("ascii"))
        return base64.b64decode(encoded, validate=True)
    except (UnicodeDecodeError, ValueError) as error:
        raise ConfigError("Protected local data is invalid or belongs to another Windows user") from error


def _read_env_file() -> dict[str, str]:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return {}
    result: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    result.setdefault("POSTGRES_HOST", "127.0.0.1")
    return result


def load_settings() -> dict[str, str]:
    environment = {key: os.environ[key] for key in REQUIRED if os.environ.get(key)}
    if REQUIRED <= environment.keys():
        return environment
    if CONFIG_PATH.exists():
        try:
            saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            saved["POSTGRES_PASSWORD"] = _unprotect(saved.pop("POSTGRES_PASSWORD_PROTECTED"))
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
            raise ConfigError(f"Saved database configuration is invalid: {error}") from error
        if REQUIRED <= saved.keys():
            return saved
    settings = _read_env_file()
    missing = sorted(REQUIRED - settings.keys())
    if missing:
        raise ConfigError("Database connection is not configured")
    return settings


def saved_connection_fields() -> dict[str, str]:
    try:
        settings = load_settings()
    except ConfigError:
        return {
            "POSTGRES_HOST": "127.0.0.1", "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "account_statements", "POSTGRES_USER": "postgres",
        }
    return {key: settings[key] for key in ("POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER")}


def save_settings(settings: dict[str, str]) -> None:
    missing = sorted(REQUIRED - settings.keys())
    if missing:
        raise ConfigError(f"Missing connection settings: {', '.join(missing)}")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        CONFIG_DIR.chmod(0o700)
    payload = {key: settings[key] for key in REQUIRED if key != "POSTGRES_PASSWORD"}
    payload["POSTGRES_PASSWORD_PROTECTED"] = _protect(settings["POSTGRES_PASSWORD"])
    CONFIG_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if os.name != "nt":
        CONFIG_PATH.chmod(0o600)
