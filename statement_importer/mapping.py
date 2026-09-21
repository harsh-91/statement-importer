# Created by Harsh (@harsh-91) | Made in India
from __future__ import annotations

import csv
import json
import os
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import StringIO
from pathlib import Path
from typing import Any

from .parsers import StatementError, _load_workbook, clean_text, date_value, fingerprint, money, normalized_text
from .config import ConfigError, protect_bytes, unprotect_bytes


PENDING_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "StatementImporter" / "pending"
PENDING_TTL = timedelta(hours=24)
MAX_MAPPED_ROWS = 200_000
MAX_MAPPED_COLUMNS = 256


def cleanup_pending(now: datetime | None = None) -> int:
    """Delete incomplete or expired pending mappings. Returns removed token count."""
    now = now or datetime.now(timezone.utc)
    if not PENDING_DIR.exists():
        return 0
    removed: set[str] = set()
    for path in PENDING_DIR.iterdir():
        if path.suffix not in {".bin", ".json"}:
            continue
        token = path.stem
        metadata_path = PENDING_DIR / f"{token}.json"
        expired = True
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            created = datetime.fromisoformat(metadata["created_at"])
            expired = now - created.astimezone(timezone.utc) > PENDING_TTL
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            expired = True
        if expired:
            remove_pending(token)
            removed.add(token)
    return len(removed)


def save_pending(data: bytes, filename: str) -> str:
    cleanup_pending()
    token = secrets.token_urlsafe(24)
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    (PENDING_DIR / f"{token}.bin").write_bytes(protect_bytes(data))
    (PENDING_DIR / f"{token}.json").write_text(json.dumps({
        "filename": Path(filename).name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "protected": True,
    }), encoding="utf-8")
    return token


def load_pending(token: str) -> tuple[bytes, str]:
    if not re.fullmatch(r"[A-Za-z0-9_-]{20,80}", token):
        raise StatementError("Invalid mapping token")
    data_path = PENDING_DIR / f"{token}.bin"
    metadata_path = PENDING_DIR / f"{token}.json"
    if not data_path.exists() or not metadata_path.exists():
        raise StatementError("This pending statement has expired or was already imported")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        created = datetime.fromisoformat(metadata["created_at"])
        if datetime.now(timezone.utc) - created.astimezone(timezone.utc) > PENDING_TTL:
            remove_pending(token)
            raise StatementError("This pending statement expired after 24 hours")
        protected = data_path.read_bytes()
        return unprotect_bytes(protected), metadata["filename"]
    except StatementError:
        raise
    except (OSError, ValueError, KeyError, json.JSONDecodeError, ConfigError) as error:
        remove_pending(token)
        raise StatementError("This pending statement is invalid or cannot be decrypted") from error


def remove_pending(token: str) -> None:
    for suffix in (".bin", ".json"):
        path = PENDING_DIR / f"{token}{suffix}"
        if path.exists():
            path.unlink()


def _rows(data: bytes, filename: str, password: str | None) -> tuple[list[list[Any]], str]:
    if filename.lower().endswith(".csv"):
        text = data.decode("utf-8-sig", errors="replace")
        csv.field_size_limit(1_000_000)
        rows = []
        for index, row in enumerate(csv.reader(StringIO(text)), 1):
            if index > MAX_MAPPED_ROWS:
                raise StatementError(f"CSV exceeds the {MAX_MAPPED_ROWS:,} row safety limit")
            if len(row) > MAX_MAPPED_COLUMNS:
                raise StatementError(f"CSV row {index} exceeds the {MAX_MAPPED_COLUMNS} column safety limit")
            rows.append(row)
        return rows, "CSV"
    workbook = _load_workbook(data, password)
    try:
        sheet = workbook.active
        return [list(row) for row in sheet.iter_rows(values_only=True)], sheet.title
    finally:
        workbook.close()


def preview_pending(token: str, password: str | None = None) -> dict[str, Any]:
    data, filename = load_pending(token)
    rows, sheet_name = _rows(data, filename, password)
    preview = [[clean_text(cell) for cell in row[:14]] for row in rows[:30]]
    width = max((len(row) for row in preview), default=0)
    return {"filename": filename, "sheet_name": sheet_name, "rows": preview, "width": width}


def mapped_rows(token: str, form: dict[str, str]) -> dict[str, Any]:
    data, filename = load_pending(token)
    rows, sheet_name = _rows(data, filename, form.get("password") or None)
    bank_name = normalized_text(form.get("bank_name"))
    account_number = normalized_text(form.get("account_number"))
    if not bank_name or not account_number:
        raise StatementError("Bank name and account number are required")
    header_row = int(form["header_row"])
    if header_row < 1 or header_row > len(rows):
        raise StatementError("Header row is outside the document")
    columns = {
        key: (int(form[key]) - 1 if form.get(key) else None)
        for key in ("date_column", "value_date_column", "description_column", "reference_column", "debit_column", "credit_column", "balance_column")
    }
    required = ("date_column", "description_column", "balance_column")
    if any(columns[key] is None for key in required):
        raise StatementError("Date, description, and balance columns are required")
    if columns["debit_column"] is None and columns["credit_column"] is None:
        raise StatementError("At least one debit or credit column is required")
    if any(value is not None and (value < 0 or value >= MAX_MAPPED_COLUMNS) for value in columns.values()):
        raise StatementError(f"Mapped columns must be between 1 and {MAX_MAPPED_COLUMNS}")
    formats = [form.get("date_format") or "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d,%m,%Y", "%d %B %Y"]
    parsed_rows = []
    for source_row, row in enumerate(rows[header_row:], header_row + 1):
        def cell(name):
            index = columns[name]
            return row[index] if index is not None and index < len(row) else None
        if not clean_text(cell("date_column")):
            continue
        try:
            transaction_date = date_value(cell("date_column"), *formats)
        except StatementError as error:
            raise StatementError(f"Invalid transaction date at source row {source_row}") from error
        debit = money(cell("debit_column")) if columns["debit_column"] is not None else None
        credit = money(cell("credit_column")) if columns["credit_column"] is not None else None
        if debit is None and credit is None:
            continue
        if (debit is not None and debit < 0) or (credit is not None and credit < 0):
            raise StatementError(f"Negative debit or credit at source row {source_row}")
        if debit not in (None, Decimal(0)) and credit not in (None, Decimal(0)):
            raise StatementError(f"Both debit and credit are populated at source row {source_row}")
        balance = money(cell("balance_column"), allow_blank=False)
        value_date = date_value(cell("value_date_column"), *formats) if clean_text(cell("value_date_column")) else transaction_date
        description = clean_text(cell("description_column"))
        if not description:
            raise StatementError(f"Description is blank at source row {source_row}")
        reference = clean_text(cell("reference_column")) or None
        parsed = {
            "account_number": account_number, "transaction_date": transaction_date, "value_date": value_date,
            "description": description, "reference_number": reference, "debit": debit, "credit": credit,
            "balance": balance, "currency": normalized_text(form.get("currency")) or "INR",
            "source_file": filename, "source_sheet": sheet_name, "source_row": source_row,
        }
        parsed["transaction_fingerprint"] = fingerprint(
            re.sub(r"[^a-z0-9]+", "_", bank_name.lower()).strip("_"), account_number,
            transaction_date, value_date, description, reference, debit, credit, balance,
        )
        parsed_rows.append(parsed)
    if not parsed_rows:
        raise StatementError("No transactions matched this mapping")
    ordered = sorted(parsed_rows, key=lambda item: item["source_row"])
    reverse = form.get("order") == "newest_first"
    chain = list(reversed(ordered)) if reverse else ordered
    mismatches = 0
    for previous, current in zip(chain, chain[1:]):
        expected = previous["balance"] + (current["credit"] or 0) - (current["debit"] or 0)
        if expected.quantize(Decimal("0.01")) != current["balance"].quantize(Decimal("0.01")):
            mismatches += 1
    if mismatches:
        raise StatementError(f"Mapped running-balance reconciliation failed at {mismatches} transition(s)")
    headers = [normalized_text(cell) for cell in rows[header_row - 1]] if header_row <= len(rows) else []
    return {
        "bank_name": bank_name, "account_number": account_number, "filename": filename,
        "sheet_name": sheet_name, "rows": parsed_rows, "period_start": min(r["transaction_date"] for r in parsed_rows),
        "period_end": max(r["transaction_date"] for r in parsed_rows), "headers": headers,
        "mapping": {key: value for key, value in form.items() if key not in {"password", "csrf_token"}},
    }
