# Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg import sql

from .config import load_settings
from .parsers import ParsedStatement, icici_fingerprint, indusind_fingerprint, sbi_fingerprint


TABLES = {
    "sbi": {
        "bank_name": "State Bank of India",
        "table": "bank_sbi_transactions",
        "columns": [
            "account_number", "statement_date", "statement_period_start", "statement_period_end",
            "source_file", "source_row", "transaction_date", "details", "reference_number",
            "debit", "credit", "balance", "statement_metadata", "transaction_fingerprint",
        ],
        "fingerprint_columns": [
            "account_number", "transaction_date", "details", "reference_number", "debit", "credit", "balance"
        ],
        "fingerprint": sbi_fingerprint,
    },
    "icici": {
        "bank_name": "ICICI Bank",
        "table": "bank_icici_transactions",
        "columns": [
            "account_number", "statement_period_start", "statement_period_end", "source_file", "source_sheet",
            "source_row", "serial_number", "value_date", "transaction_date", "cheque_number",
            "transaction_remarks", "withdrawal_amount", "deposit_amount", "balance", "statement_metadata",
            "transaction_fingerprint",
        ],
        "fingerprint_columns": [
            "account_number", "value_date", "transaction_date", "cheque_number", "transaction_remarks",
            "withdrawal_amount", "deposit_amount", "balance",
        ],
        "fingerprint": icici_fingerprint,
    },
    "indusind": {
        "bank_name": "IndusInd Bank",
        "table": "bank_indusind_transactions",
        "columns": [
            "account_number", "statement_period_start", "statement_period_end", "source_file", "source_sheet",
            "source_row", "serial_number", "transaction_date", "transaction_type", "description", "debit", "credit",
            "balance", "statement_metadata", "transaction_fingerprint",
        ],
        "fingerprint_columns": [
            "account_number", "transaction_date", "transaction_type", "description", "debit", "credit", "balance"
        ],
        "fingerprint": indusind_fingerprint,
    },
}

DATABASE_CONNECT_TIMEOUT_SECONDS = 5


def connect(settings: dict[str, str] | None = None):
    settings = settings or load_settings()
    return psycopg.connect(
        host=settings["POSTGRES_HOST"], port=int(settings["POSTGRES_PORT"]),
        dbname=settings["POSTGRES_DB"], user=settings["POSTGRES_USER"],
        password=settings["POSTGRES_PASSWORD"],
        connect_timeout=DATABASE_CONNECT_TIMEOUT_SECONDS,
        application_name="statement-importer",
    )


BASE_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS bank_sbi_transactions (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        account_number TEXT NOT NULL, statement_date DATE NOT NULL,
        statement_period_start DATE NOT NULL, statement_period_end DATE NOT NULL,
        source_file TEXT NOT NULL, source_row INTEGER NOT NULL, transaction_date DATE NOT NULL,
        details TEXT NOT NULL, reference_number TEXT, debit NUMERIC(18,2), credit NUMERIC(18,2),
        balance NUMERIC(18,2) NOT NULL, statement_metadata JSONB NOT NULL,
        imported_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        transaction_fingerprint TEXT, import_batch_id UUID
    )""",
    """CREATE TABLE IF NOT EXISTS bank_icici_transactions (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        account_number TEXT NOT NULL, statement_period_start DATE NOT NULL,
        statement_period_end DATE NOT NULL, source_file TEXT NOT NULL, source_sheet TEXT NOT NULL,
        source_row INTEGER NOT NULL, serial_number INTEGER NOT NULL, value_date DATE NOT NULL,
        transaction_date DATE NOT NULL, cheque_number TEXT, transaction_remarks TEXT NOT NULL,
        withdrawal_amount NUMERIC(18,2) NOT NULL, deposit_amount NUMERIC(18,2) NOT NULL,
        balance NUMERIC(18,2) NOT NULL, statement_metadata JSONB NOT NULL,
        imported_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        transaction_fingerprint TEXT, import_batch_id UUID
    )""",
    """CREATE TABLE IF NOT EXISTS bank_indusind_transactions (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        account_number TEXT NOT NULL, statement_period_start DATE NOT NULL,
        statement_period_end DATE NOT NULL, source_file TEXT NOT NULL, source_sheet TEXT NOT NULL,
        source_row INTEGER NOT NULL, serial_number INTEGER NOT NULL, transaction_date DATE NOT NULL,
        transaction_type TEXT NOT NULL, description TEXT NOT NULL, debit NUMERIC(18,2),
        credit NUMERIC(18,2), balance NUMERIC(18,2) NOT NULL, statement_metadata JSONB NOT NULL,
        imported_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        transaction_fingerprint TEXT, import_batch_id UUID
    )""",
    """CREATE TABLE IF NOT EXISTS bank_registry (
        bank_key TEXT PRIMARY KEY, bank_name TEXT NOT NULL, table_name TEXT NOT NULL UNIQUE,
        parser_type TEXT NOT NULL, enabled BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS bank_format_profiles (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, bank_key TEXT NOT NULL REFERENCES bank_registry(bank_key),
        profile_name TEXT NOT NULL, signature JSONB NOT NULL, column_mapping JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(bank_key, profile_name)
    )""",
    """CREATE TABLE IF NOT EXISTS import_batches (
        id UUID PRIMARY KEY, status TEXT NOT NULL, file_count INTEGER NOT NULL DEFAULT 0,
        parsed_count INTEGER NOT NULL DEFAULT 0, inserted_count INTEGER NOT NULL DEFAULT 0,
        duplicate_count INTEGER NOT NULL DEFAULT 0, rejected_count INTEGER NOT NULL DEFAULT 0,
        started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, completed_at TIMESTAMPTZ
    )""",
    """CREATE TABLE IF NOT EXISTS import_files (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, batch_id UUID NOT NULL REFERENCES import_batches(id),
        source_file TEXT NOT NULL, bank_key TEXT, account_masked TEXT, statement_period_start DATE,
        statement_period_end DATE, status TEXT NOT NULL, parsed_count INTEGER NOT NULL DEFAULT 0,
        inserted_count INTEGER NOT NULL DEFAULT 0, duplicate_count INTEGER NOT NULL DEFAULT 0,
        error_message TEXT, reconciliation JSONB, created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS import_errors (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, batch_id UUID REFERENCES import_batches(id),
        source_file TEXT, source_row INTEGER, error_code TEXT NOT NULL, error_message TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS audit_log (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, event_type TEXT NOT NULL,
        event_data JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS application_settings (
        setting_key TEXT PRIMARY KEY, setting_value JSONB NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS api_credentials (
        id UUID PRIMARY KEY, label TEXT NOT NULL, key_hash TEXT NOT NULL UNIQUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        last_used_at TIMESTAMPTZ, revoked_at TIMESTAMPTZ
    )""",
]


def _relation_kind(cursor, name: str) -> str | None:
    cursor.execute("SELECT relkind FROM pg_class WHERE oid = to_regclass(%s)", (f"public.{name}",))
    row = cursor.fetchone()
    return row[0] if row else None


def _rename_legacy_tables(cursor) -> None:
    legacy = {
        "bank_transactions": "bank_sbi_transactions",
        "icici_bank_transactions": "bank_icici_transactions",
        "indusind_bank_transactions": "bank_indusind_transactions",
    }
    for old_name, new_name in legacy.items():
        if _relation_kind(cursor, old_name) == "r" and _relation_kind(cursor, new_name) is None:
            cursor.execute(
                sql.SQL("ALTER TABLE {} RENAME TO {}").format(sql.Identifier(old_name), sql.Identifier(new_name))
            )


def _register_known_banks(cursor) -> None:
    for bank_key, configuration in TABLES.items():
        cursor.execute(
            """INSERT INTO bank_registry (bank_key, bank_name, table_name, parser_type)
               VALUES (%s, %s, %s, 'built_in')
               ON CONFLICT (bank_key) DO UPDATE SET bank_name=EXCLUDED.bank_name, table_name=EXCLUDED.table_name""",
            (bank_key, configuration["bank_name"], configuration["table"]),
        )


def refresh_unified_view(cursor) -> None:
    known_query = """
        SELECT 'State Bank of India'::text AS bank_name, account_number, transaction_date,
               transaction_date AS value_date, details AS description, reference_number,
               debit, credit, COALESCE(credit, -debit) AS amount,
               CASE WHEN credit IS NOT NULL THEN 'credit' ELSE 'debit' END::text AS transaction_direction,
               balance, 'INR'::text AS currency, source_file, import_batch_id, imported_at
        FROM bank_sbi_transactions
        UNION ALL
        SELECT 'ICICI Bank', account_number, transaction_date, value_date,
               transaction_remarks, cheque_number, withdrawal_amount, deposit_amount,
               CASE WHEN deposit_amount <> 0 THEN deposit_amount ELSE -withdrawal_amount END,
               CASE WHEN deposit_amount <> 0 THEN 'credit' ELSE 'debit' END,
               balance, 'INR', source_file, import_batch_id, imported_at
        FROM bank_icici_transactions
        UNION ALL
        SELECT 'IndusInd Bank', account_number, transaction_date, transaction_date,
               description, NULL::text, debit, credit, COALESCE(credit, -debit),
               CASE WHEN credit IS NOT NULL THEN 'credit' ELSE 'debit' END,
               balance, 'INR', source_file, import_batch_id, imported_at
        FROM bank_indusind_transactions"""
    cursor.execute("SELECT bank_name,table_name FROM bank_registry WHERE parser_type='mapped' AND enabled ORDER BY bank_key")
    query_parts: list[sql.Composable] = [sql.SQL(known_query)]
    for bank_name, table_name in cursor.fetchall():
        query_parts.append(sql.SQL("""SELECT {}::text,account_number,transaction_date,value_date,description,
            reference_number,debit,credit,COALESCE(credit,-debit),
            CASE WHEN credit IS NOT NULL THEN 'credit' ELSE 'debit' END,
            balance,currency,source_file,import_batch_id,imported_at FROM {}""").format(
                sql.Literal(bank_name), sql.Identifier(table_name)
            ))
    cursor.execute("DROP VIEW IF EXISTS unified_bank_transactions")
    cursor.execute(sql.SQL("CREATE VIEW unified_bank_transactions AS ") + sql.SQL(" UNION ALL ").join(query_parts))


def register_mapped_bank(bank_name: str, profile_name: str, headers: list[str], mapping: dict[str, Any]) -> tuple[str, str]:
    bank_key = re.sub(r"[^a-z0-9]+", "_", bank_name.lower()).strip("_")
    if not bank_key:
        raise ValueError("Bank name must contain letters or numbers")
    table_name = f"bank_{bank_key}_transactions"
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql.SQL("""CREATE TABLE IF NOT EXISTS {} (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, account_number TEXT NOT NULL,
                transaction_date DATE NOT NULL,value_date DATE NOT NULL,description TEXT NOT NULL,
                reference_number TEXT,debit NUMERIC(18,2),credit NUMERIC(18,2),balance NUMERIC(18,2) NOT NULL,
                currency TEXT NOT NULL DEFAULT 'INR',source_file TEXT NOT NULL,source_sheet TEXT NOT NULL,
                source_row INTEGER NOT NULL,transaction_fingerprint TEXT NOT NULL UNIQUE,
                import_batch_id UUID,imported_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""").format(sql.Identifier(table_name)))
            cursor.execute("""INSERT INTO bank_registry(bank_key,bank_name,table_name,parser_type)
                VALUES(%s,%s,%s,'mapped') ON CONFLICT(bank_key) DO UPDATE SET bank_name=EXCLUDED.bank_name,
                table_name=EXCLUDED.table_name,parser_type='mapped'""", (bank_key,bank_name,table_name))
            cursor.execute("""INSERT INTO bank_format_profiles(bank_key,profile_name,signature,column_mapping)
                VALUES(%s,%s,%s::jsonb,%s::jsonb) ON CONFLICT(bank_key,profile_name) DO UPDATE SET
                signature=EXCLUDED.signature,column_mapping=EXCLUDED.column_mapping""",
                (bank_key,profile_name,json.dumps({"headers":headers}),json.dumps(mapping)))
            refresh_unified_view(cursor)
    return bank_key, table_name


def import_mapped_statement_atomic(mapped: dict[str, Any], profile_name: str) -> tuple[str, str, str, int, int]:
    """Create/update a mapped bank, import rows, and write audit data in one transaction."""
    bank_name = mapped["bank_name"]
    bank_key = re.sub(r"[^a-z0-9]+", "_", bank_name.lower()).strip("_")
    if not bank_key:
        raise ValueError("Bank name must contain letters or numbers")
    table_name = f"bank_{bank_key}_transactions"
    batch_id = str(uuid.uuid4())
    columns = ["account_number","transaction_date","value_date","description","reference_number","debit","credit",
               "balance","currency","source_file","source_sheet","source_row","transaction_fingerprint","import_batch_id"]
    insert = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT(transaction_fingerprint) DO NOTHING").format(
        sql.Identifier(table_name), sql.SQL(",").join(map(sql.Identifier, columns)),
        sql.SQL(",").join(sql.Placeholder() for _ in columns))
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (f"statement-import:{bank_key}",))
            cursor.execute("INSERT INTO import_batches (id,status,file_count) VALUES (%s,'processing',1)", (batch_id,))
            cursor.execute(sql.SQL("""CREATE TABLE IF NOT EXISTS {} (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, account_number TEXT NOT NULL,
                transaction_date DATE NOT NULL,value_date DATE NOT NULL,description TEXT NOT NULL,
                reference_number TEXT,debit NUMERIC(18,2),credit NUMERIC(18,2),balance NUMERIC(18,2) NOT NULL,
                currency TEXT NOT NULL DEFAULT 'INR',source_file TEXT NOT NULL,source_sheet TEXT NOT NULL,
                source_row INTEGER NOT NULL,transaction_fingerprint TEXT NOT NULL UNIQUE,
                import_batch_id UUID,imported_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""").format(sql.Identifier(table_name)))
            cursor.execute("""INSERT INTO bank_registry(bank_key,bank_name,table_name,parser_type)
                VALUES(%s,%s,%s,'mapped') ON CONFLICT(bank_key) DO UPDATE SET bank_name=EXCLUDED.bank_name,
                table_name=EXCLUDED.table_name,parser_type='mapped'""", (bank_key, bank_name, table_name))
            cursor.execute("""INSERT INTO bank_format_profiles(bank_key,profile_name,signature,column_mapping)
                VALUES(%s,%s,%s::jsonb,%s::jsonb) ON CONFLICT(bank_key,profile_name) DO UPDATE SET
                signature=EXCLUDED.signature,column_mapping=EXCLUDED.column_mapping""",
                (bank_key, profile_name, json.dumps({"headers": mapped["headers"]}), json.dumps(mapped["mapping"])))
            inserted = 0
            for row in mapped["rows"]:
                cursor.execute(insert, [row.get(column) if column != "import_batch_id" else batch_id for column in columns])
                inserted += cursor.rowcount
            skipped = len(mapped["rows"]) - inserted
            account = mapped["account_number"]
            masked = "*" * max(0, len(account) - 4) + account[-4:]
            reconciliation = [f"Running balances reconcile across {len(mapped['rows'])} mapped transactions"]
            cursor.execute("""INSERT INTO import_files
                (batch_id,source_file,bank_key,account_masked,statement_period_start,statement_period_end,
                 status,parsed_count,inserted_count,duplicate_count,reconciliation)
                VALUES(%s,%s,%s,%s,%s,%s,'success',%s,%s,%s,%s::jsonb)""",
                (batch_id, mapped["filename"], bank_key, masked, mapped["period_start"], mapped["period_end"],
                 len(mapped["rows"]), inserted, skipped, json.dumps(reconciliation)))
            cursor.execute("""UPDATE import_batches SET status='complete',parsed_count=%s,inserted_count=%s,
                duplicate_count=%s,rejected_count=0,completed_at=CURRENT_TIMESTAMP WHERE id=%s""",
                (len(mapped["rows"]), inserted, skipped, batch_id))
            cursor.execute("INSERT INTO audit_log(event_type,event_data) VALUES('mapped_statement_imported',%s::jsonb)",
                           (json.dumps({"bank_key": bank_key, "batch_id": batch_id, "parsed": len(mapped["rows"]),
                                        "inserted": inserted, "duplicates": skipped}),))
            refresh_unified_view(cursor)
    return bank_key, table_name, batch_id, inserted, skipped


def import_mapped_transactions(table_name: str, rows: list[dict[str, Any]], batch_id: str | None) -> tuple[int, int]:
    columns = ["account_number","transaction_date","value_date","description","reference_number","debit","credit",
               "balance","currency","source_file","source_sheet","source_row","transaction_fingerprint","import_batch_id"]
    insert = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT(transaction_fingerprint) DO NOTHING").format(
        sql.Identifier(table_name),sql.SQL(",").join(map(sql.Identifier,columns)),
        sql.SQL(",").join(sql.Placeholder() for _ in columns))
    inserted = 0
    with connect() as connection:
        with connection.cursor() as cursor:
            for row in rows:
                cursor.execute(insert,[row.get(column) if column != "import_batch_id" else batch_id for column in columns])
                inserted += cursor.rowcount
            refresh_unified_view(cursor)
    return inserted,len(rows)-inserted


def ensure_schema(settings: dict[str, str] | None = None) -> None:
    with connect(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout = '10s'")
            cursor.execute("SET LOCAL statement_timeout = '120s'")
            _rename_legacy_tables(cursor)
            for statement in BASE_SCHEMA:
                cursor.execute(statement)
            for configuration in TABLES.values():
                table = configuration["table"]
                cursor.execute(
                    sql.SQL("ALTER TABLE {} ADD COLUMN IF NOT EXISTS transaction_fingerprint TEXT").format(sql.Identifier(table))
                )
                cursor.execute(
                    sql.SQL("ALTER TABLE {} ADD COLUMN IF NOT EXISTS import_batch_id UUID").format(sql.Identifier(table))
                )
                columns = configuration["fingerprint_columns"]
                cursor.execute(
                    sql.SQL("SELECT id, {} FROM {} WHERE transaction_fingerprint IS NULL ORDER BY id").format(
                        sql.SQL(", ").join(map(sql.Identifier, columns)), sql.Identifier(table)
                    )
                )
                updates: list[tuple[str, int]] = []
                seen: set[str] = set()
                for record in cursor.fetchall():
                    row = dict(zip(columns, record[1:]))
                    value = configuration["fingerprint"](row)
                    if value in seen:
                        raise RuntimeError(f"Existing duplicate transactions prevent migration of {table}")
                    seen.add(value)
                    updates.append((value, record[0]))
                if updates:
                    cursor.executemany(
                        sql.SQL("UPDATE {} SET transaction_fingerprint=%s WHERE id=%s").format(sql.Identifier(table)),
                        updates,
                    )
                cursor.execute(
                    sql.SQL("CREATE UNIQUE INDEX IF NOT EXISTS {} ON {} (transaction_fingerprint)").format(
                        sql.Identifier(f"{table}_fingerprint_unique"), sql.Identifier(table)
                    )
                )
                cursor.execute(
                    sql.SQL("ALTER TABLE {} ALTER COLUMN transaction_fingerprint SET NOT NULL").format(sql.Identifier(table))
                )
            _register_known_banks(cursor)
            cursor.execute("""UPDATE import_batches SET status='interrupted', completed_at=CURRENT_TIMESTAMP
                              WHERE status='processing' AND started_at < CURRENT_TIMESTAMP - INTERVAL '1 hour'""")
            refresh_unified_view(cursor)


def ensure_base_schema(settings: dict[str, str] | None = None) -> None:
    ensure_schema(settings)


def ensure_fingerprint_schema(settings: dict[str, str] | None = None) -> None:
    ensure_schema(settings)


def test_connection(settings: dict[str, str]) -> str:
    with connect(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            return cursor.fetchone()[0]


def provision_database(settings: dict[str, str]) -> str:
    try:
        return test_connection(settings)
    except psycopg.errors.InvalidCatalogName:
        maintenance = dict(settings)
        maintenance["POSTGRES_DB"] = "postgres"
        with connect(maintenance) as connection:
            connection.autocommit = True
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(settings["POSTGRES_DB"])))
        return test_connection(settings)


def create_import_batch(file_count: int) -> str:
    import uuid
    batch_id = str(uuid.uuid4())
    with connect() as connection:
        connection.execute(
            "INSERT INTO import_batches (id, status, file_count) VALUES (%s, 'processing', %s)",
            (batch_id, file_count),
        )
    return batch_id


def record_import_file(batch_id: str, result: dict[str, Any]) -> None:
    account = result.get("account") or ""
    masked = ("*" * max(0, len(account) - 4) + account[-4:]) if account else None
    with connect() as connection:
        connection.execute(
            """INSERT INTO import_files
               (batch_id, source_file, bank_key, account_masked, statement_period_start,
                statement_period_end, status, parsed_count, inserted_count, duplicate_count,
                error_message, reconciliation)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)""",
            (
                batch_id, result.get("file"), result.get("bank_key"), masked,
                result.get("period_start"), result.get("period_end"), result["status"],
                result.get("parsed", 0), result.get("inserted", 0), result.get("skipped", 0),
                result.get("message"), json.dumps(result.get("reconciliations", [])),
            ),
        )


def complete_import_batch(batch_id: str, results: list[dict[str, Any]]) -> None:
    parsed = sum(item.get("parsed", 0) for item in results)
    inserted = sum(item.get("inserted", 0) for item in results)
    duplicates = sum(item.get("skipped", 0) for item in results)
    rejected = sum(item.get("status") != "success" for item in results)
    status = "complete" if rejected == 0 else ("partial" if inserted else "failed")
    with connect() as connection:
        connection.execute(
            """UPDATE import_batches SET status=%s, parsed_count=%s, inserted_count=%s,
               duplicate_count=%s, rejected_count=%s, completed_at=%s WHERE id=%s""",
            (status, parsed, inserted, duplicates, rejected, datetime.now(timezone.utc), batch_id),
        )


def import_statement(statement: ParsedStatement, batch_id: str | None = None) -> tuple[int, int]:
    configuration = TABLES[statement.bank_key]
    columns: list[str] = list(configuration["columns"])
    if batch_id:
        columns.append("import_batch_id")
    insert = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT (transaction_fingerprint) DO NOTHING").format(
        sql.Identifier(configuration["table"]), sql.SQL(", ").join(map(sql.Identifier, columns)),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
    )
    inserted = 0
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (f"statement-import:{statement.bank_key}",))
            for row in statement.rows:
                values = [row[column] for column in configuration["columns"]]
                if batch_id:
                    values.append(batch_id)
                cursor.execute(insert, values)
                inserted += cursor.rowcount
    return inserted, len(statement.rows) - inserted


def import_statement_with_audit(statement: ParsedStatement, batch_id: str) -> tuple[int, int]:
    """Import one known statement and its success audit record atomically."""
    configuration = TABLES[statement.bank_key]
    columns = list(configuration["columns"]) + ["import_batch_id"]
    insert = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT (transaction_fingerprint) DO NOTHING").format(
        sql.Identifier(configuration["table"]), sql.SQL(", ").join(map(sql.Identifier, columns)),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
    )
    inserted = 0
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (f"statement-import:{statement.bank_key}",))
            for row in statement.rows:
                cursor.execute(insert, [row[column] for column in configuration["columns"]] + [batch_id])
                inserted += cursor.rowcount
            skipped = len(statement.rows) - inserted
            account = statement.account_number
            masked = "*" * max(0, len(account) - 4) + account[-4:]
            cursor.execute("""INSERT INTO import_files
                (batch_id,source_file,bank_key,account_masked,statement_period_start,statement_period_end,
                 status,parsed_count,inserted_count,duplicate_count,reconciliation)
                VALUES(%s,%s,%s,%s,%s,%s,'success',%s,%s,%s,%s::jsonb)""",
                (batch_id, statement.source_file, statement.bank_key, masked, statement.period_start,
                 statement.period_end, len(statement.rows), inserted, skipped,
                 json.dumps(statement.reconciliations)))
            cursor.execute("INSERT INTO audit_log(event_type,event_data) VALUES('statement_imported',%s::jsonb)",
                           (json.dumps({"bank_key": statement.bank_key, "batch_id": batch_id,
                                        "parsed": len(statement.rows), "inserted": inserted,
                                        "duplicates": skipped}),))
    return inserted, skipped


def table_counts() -> dict[str, int]:
    result: dict[str, int] = {}
    with connect() as connection:
        with connection.cursor() as cursor:
            for configuration in TABLES.values():
                table = configuration["table"]
                cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
                result[table] = cursor.fetchone()[0]
    return result


def dashboard_stats() -> dict[str, Any]:
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*), COUNT(DISTINCT bank_name), COUNT(DISTINCT account_number) FROM unified_bank_transactions")
            transactions, banks, accounts = cursor.fetchone()
            cursor.execute("SELECT completed_at FROM import_batches ORDER BY started_at DESC LIMIT 1")
            last = cursor.fetchone()
            return {
                "transactions": transactions, "banks": banks, "accounts": accounts,
                "last_import": last[0] if last else None,
            }
