# Created by Harsh (@harsh-91) | Made in India
from __future__ import annotations

import tempfile
import sys
from pathlib import Path
from unittest.mock import patch

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from statement_importer import local_postgres


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="statement-importer-postgres-") as folder:
        root = Path(folder)
        data = root / "data"
        with (
            patch.object(local_postgres, "MANAGED_ROOT", root),
            patch.object(local_postgres, "DATA_DIR", data),
            patch.object(local_postgres, "LOG_PATH", root / "postgresql.log"),
            patch.object(local_postgres, "METADATA_PATH", root / "cluster.json"),
            patch.object(local_postgres, "save_settings"),
        ):
            settings = local_postgres.provision_managed_postgres()
            repeated = local_postgres.provision_managed_postgres()
            assert settings == repeated
            with psycopg.connect(
                host=settings["POSTGRES_HOST"], port=int(settings["POSTGRES_PORT"]),
                dbname=settings["POSTGRES_DB"], user=settings["POSTGRES_USER"],
                password=settings["POSTGRES_PASSWORD"],
            ) as connection:
                role = connection.execute(
                    "SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname=current_user"
                ).fetchone()
                assert role == (False, False, False)
                assert connection.execute("SELECT COUNT(*) FROM bank_registry").fetchone()[0] >= 3
            metadata = local_postgres._metadata()
            bin_dir = Path(metadata["bin_dir"])
            local_postgres._run([
                str(bin_dir / "pg_ctl.exe"), "stop", "-D", str(data), "-m", "fast", "-w"
            ], timeout=60)
    print({"managed_postgres": "verified", "least_privilege": True, "repeatable": True})


if __name__ == "__main__":
    main()
