# Created by Harsh (@harsh-91) | Made in India
import re
import sys
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psycopg import sql

from app import app
from statement_importer.database import connect, refresh_unified_view


def csrf(body: str) -> str:
    return re.search(r'name="csrf_token" value="([^"]+)"', body).group(1)


def main():
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('public.bank_codex_test_bank_transactions')")
            if cursor.fetchone()[0]:
                cursor.execute("SELECT DISTINCT batch_id FROM import_files WHERE source_file='test-bank.csv'")
                stale_batches = [row[0] for row in cursor.fetchall()]
                cursor.execute("DELETE FROM bank_format_profiles WHERE bank_key='codex_test_bank'")
                cursor.execute("DELETE FROM bank_registry WHERE bank_key='codex_test_bank'")
                cursor.execute("DELETE FROM audit_log WHERE event_data->>'bank_key'='codex_test_bank'")
                cursor.execute("DELETE FROM import_files WHERE source_file='test-bank.csv'")
                for batch_id in stale_batches:
                    cursor.execute("DELETE FROM import_batches WHERE id=%s", (batch_id,))
                refresh_unified_view(cursor)
                cursor.execute(sql.SQL("DROP TABLE {}").format(sql.Identifier("bank_codex_test_bank_transactions")))
    client = app.test_client()
    home = client.get("/")
    token = csrf(home.get_data(as_text=True))
    content = b"Date,Description,Debit,Credit,Balance\n01/01/2026,Opening,,1000,1000\n02/01/2026,Coffee,100,,900\n"
    upload = client.post(
        "/import", data={"csrf_token": token, "statements": (BytesIO(content), "test-bank.csv")},
        content_type="multipart/form-data",
    )
    match = re.search(r'href="(/map/[^"]+)"', upload.get_data(as_text=True))
    assert upload.status_code == 200 and match
    mapping_url = match.group(1)
    preview = client.get(mapping_url)
    assert preview.status_code == 200 and "Coffee" in preview.get_data(as_text=True)
    mapped = client.post(mapping_url, data={
        "csrf_token": token, "action": "import", "bank_name": "Codex Test Bank",
        "account_number": "TEST0001", "profile_name": "Smoke", "currency": "INR",
        "header_row": "1", "date_column": "1", "description_column": "2",
        "debit_column": "3", "credit_column": "4", "balance_column": "5",
        "date_format": "%d/%m/%Y", "order": "oldest_first",
    })
    body = mapped.get_data(as_text=True)
    assert mapped.status_code == 200 and "2 new rows" in body
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM bank_codex_test_bank_transactions")
            assert cursor.fetchone()[0] == 2
            cursor.execute("SELECT COUNT(*) FROM unified_bank_transactions WHERE bank_name='Codex Test Bank'")
            assert cursor.fetchone()[0] == 2
            cursor.execute("SELECT DISTINCT batch_id FROM import_files WHERE source_file='test-bank.csv'")
            batch_ids = [row[0] for row in cursor.fetchall()]
            cursor.execute("DELETE FROM bank_format_profiles WHERE bank_key='codex_test_bank'")
            cursor.execute("DELETE FROM bank_registry WHERE bank_key='codex_test_bank'")
            cursor.execute("DELETE FROM audit_log WHERE event_data->>'bank_key'='codex_test_bank'")
            cursor.execute("DELETE FROM import_files WHERE source_file='test-bank.csv'")
            for batch_id in batch_ids:
                cursor.execute("DELETE FROM import_batches WHERE id=%s", (batch_id,))
            refresh_unified_view(cursor)
            cursor.execute(sql.SQL("DROP TABLE {} ").format(sql.Identifier("bank_codex_test_bank_transactions")))
    print({"unknown_upload": upload.status_code, "preview": preview.status_code, "mapped_rows": 2, "cleanup": "complete"})


if __name__ == "__main__":
    main()
