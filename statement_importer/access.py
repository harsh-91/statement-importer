# Created by Harsh (@harsh-91) | Made in India
from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from psycopg import sql

from .database import connect


def json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def rows_as_dicts(cursor) -> list[dict[str, Any]]:
    columns = [item.name for item in cursor.description]
    return [{key: json_safe(value) for key, value in zip(columns, row)} for row in cursor.fetchall()]


def get_setting(key: str, default: Any = None) -> Any:
    with connect() as connection:
        row = connection.execute(
            "SELECT setting_value FROM application_settings WHERE setting_key=%s", (key,)
        ).fetchone()
    return row[0] if row else default


def set_setting(key: str, value: Any) -> None:
    with connect() as connection:
        connection.execute(
            """INSERT INTO application_settings (setting_key, setting_value, updated_at)
               VALUES (%s, %s::jsonb, CURRENT_TIMESTAMP)
               ON CONFLICT (setting_key) DO UPDATE SET setting_value=EXCLUDED.setting_value,
               updated_at=CURRENT_TIMESTAMP""",
            (key, json.dumps(value)),
        )


def service_status() -> dict[str, bool]:
    return {
        "api_enabled": bool(get_setting("api_enabled", False)),
        "mcp_enabled": bool(get_setting("mcp_enabled", False)),
    }


def create_api_key(label: str) -> str:
    token = "si_" + secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with connect() as connection:
        connection.execute(
            "INSERT INTO api_credentials (id, label, key_hash) VALUES (%s,%s,%s)",
            (str(uuid.uuid4()), label.strip() or "Local integration", digest),
        )
        connection.execute(
            "INSERT INTO audit_log (event_type,event_data) VALUES ('api_key_created',%s::jsonb)",
            (json.dumps({"label": label.strip() or "Local integration"}),),
        )
    return token


def verify_api_key(token: str | None) -> bool:
    if not token or not token.startswith("si_"):
        return False
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with connect() as connection:
        row = connection.execute(
            "SELECT id FROM api_credentials WHERE key_hash=%s AND revoked_at IS NULL", (digest,)
        ).fetchone()
        if row:
            connection.execute("UPDATE api_credentials SET last_used_at=CURRENT_TIMESTAMP WHERE id=%s", (row[0],))
    return bool(row)


def list_api_keys() -> list[dict[str, Any]]:
    with connect() as connection:
        cursor = connection.execute(
            "SELECT id,label,created_at,last_used_at,revoked_at FROM api_credentials ORDER BY created_at DESC"
        )
        return rows_as_dicts(cursor)


def revoke_api_key(key_id: str) -> None:
    with connect() as connection:
        connection.execute(
            "UPDATE api_credentials SET revoked_at=CURRENT_TIMESTAMP WHERE id=%s AND revoked_at IS NULL",
            (key_id,),
        )
        connection.execute(
            "INSERT INTO audit_log (event_type,event_data) VALUES ('api_key_revoked',%s::jsonb)",
            (json.dumps({"credential_id": key_id}),),
        )


def list_banks() -> list[dict[str, Any]]:
    with connect() as connection:
        return rows_as_dicts(connection.execute(
            "SELECT bank_key,bank_name,table_name,parser_type,enabled,created_at FROM bank_registry ORDER BY bank_name"
        ))


def list_accounts() -> list[dict[str, Any]]:
    with connect() as connection:
        return rows_as_dicts(connection.execute(
            """SELECT bank_name,
                      repeat('*',greatest(length(account_number)-4,0)) || right(account_number,4) AS account,
                      count(*) AS transaction_count, min(transaction_date) AS first_transaction,
                      max(transaction_date) AS last_transaction
               FROM unified_bank_transactions GROUP BY bank_name,account_number ORDER BY bank_name,account_number"""
        ))


def search_transactions(filters: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    page = max(1, int(filters.get("page", 1)))
    page_size = min(500, max(1, int(filters.get("page_size", 100))))
    conditions = []
    parameters: list[Any] = []
    mappings = {
        "bank": ("bank_name = %s", str),
        "account_last4": ("right(account_number,4) = %s", str),
        "date_from": ("transaction_date >= %s", str),
        "date_to": ("transaction_date <= %s", str),
        "direction": ("transaction_direction = %s", str),
        "amount_min": ("abs(amount) >= %s", Decimal),
        "amount_max": ("abs(amount) <= %s", Decimal),
    }
    for key, (clause, converter) in mappings.items():
        if filters.get(key) not in (None, ""):
            conditions.append(clause)
            parameters.append(converter(filters[key]))
    if filters.get("search"):
        conditions.append("(description ILIKE %s OR COALESCE(reference_number,'') ILIKE %s)")
        pattern = f"%{filters['search']}%"
        parameters.extend([pattern, pattern])
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    with connect() as connection:
        total = connection.execute("SELECT COUNT(*) FROM unified_bank_transactions" + where, parameters).fetchone()[0]
        cursor = connection.execute(
            """SELECT bank_name,
                      repeat('*',greatest(length(account_number)-4,0)) || right(account_number,4) AS account,
                      transaction_date,value_date,description,reference_number,debit,credit,amount,
                      transaction_direction,balance,currency,source_file,imported_at
               FROM unified_bank_transactions""" + where +
            " ORDER BY transaction_date DESC, imported_at DESC LIMIT %s OFFSET %s",
            parameters + [page_size, (page - 1) * page_size],
        )
        return rows_as_dicts(cursor), total


def list_imports(limit: int = 100) -> list[dict[str, Any]]:
    with connect() as connection:
        return rows_as_dicts(connection.execute(
            """SELECT id,status,file_count,parsed_count,inserted_count,duplicate_count,rejected_count,
                      started_at,completed_at FROM import_batches ORDER BY started_at DESC LIMIT %s""",
            (min(500, max(1, limit)),),
        ))


def account_balances() -> list[dict[str, Any]]:
    with connect() as connection:
        return rows_as_dicts(connection.execute(
            """SELECT DISTINCT ON (bank_name,account_number) bank_name,
                      repeat('*',greatest(length(account_number)-4,0)) || right(account_number,4) AS account,
                      transaction_date,balance,currency
               FROM unified_bank_transactions
               ORDER BY bank_name,account_number,transaction_date DESC,imported_at DESC"""
        ))


def schema_summary() -> list[dict[str, Any]]:
    with connect() as connection:
        return rows_as_dicts(connection.execute(
            """SELECT table_name,column_name,data_type,is_nullable
               FROM information_schema.columns
               WHERE table_schema='public' AND (table_name LIKE 'bank_%_transactions' OR table_name='unified_bank_transactions')
               ORDER BY table_name,ordinal_position"""
        ))
