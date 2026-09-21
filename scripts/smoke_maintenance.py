# Created by Harsh (@harsh-91) | Made in India
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psycopg import sql

from statement_importer.database import connect
from statement_importer.maintenance import create_backup


def main():
    backup = create_backup()
    assert backup.exists() and backup.stat().st_size > 0
    try:
        with connect() as connection:
            assert connection.execute("SELECT COUNT(*) FROM unified_bank_transactions").fetchone()[0] >= 4152
    finally:
        backup.unlink()
    print({"backup_verified": True, "cleanup": "complete"})


if __name__ == "__main__":
    main()
