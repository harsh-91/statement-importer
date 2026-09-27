# Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0
import unittest
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch

from statement_importer import local_postgres


class LocalPostgresTests(unittest.TestCase):
    def test_choose_port_uses_first_available_dedicated_port(self):
        with patch.object(local_postgres, "_port_is_available", side_effect=[False, False, True]):
            self.assertEqual(local_postgres.choose_port(55432, 3), 55434)

    def test_choose_port_fails_when_range_is_exhausted(self):
        with patch.object(local_postgres, "_port_is_available", return_value=False):
            with self.assertRaisesRegex(local_postgres.LocalPostgresError, "No free local PostgreSQL port"):
                local_postgres.choose_port(55432, 2)

    def test_generated_application_settings_are_local_and_least_privilege(self):
        settings = local_postgres._settings("55432", "secret")
        self.assertEqual(settings["POSTGRES_HOST"], "127.0.0.1")
        self.assertEqual(settings["POSTGRES_USER"], "statement_app")
        self.assertEqual(settings["POSTGRES_DB"], "account_statements")

    def test_version_key_is_numeric(self):
        self.assertGreater(
            local_postgres._version_key(Path("C:/Program Files/PostgreSQL/17/bin/initdb.exe")),
            local_postgres._version_key(Path("C:/Program Files/PostgreSQL/9.6/bin/initdb.exe")),
        )

    def test_explicit_bundled_postgres_path_has_priority(self):
        with tempfile.TemporaryDirectory() as folder:
            binary = Path(folder)
            for name in ("initdb.exe", "pg_ctl.exe", "postgres.exe"):
                (binary / name).touch()
            with patch.dict("os.environ", {"STATEMENT_IMPORTER_POSTGRES_BIN": str(binary)}):
                self.assertEqual(local_postgres.find_postgres_bin(), binary.resolve())

    def test_server_start_does_not_capture_inherited_output_pipes(self):
        with patch.object(local_postgres.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            local_postgres._run(["pg_ctl.exe", "start"], capture_output=False)
        self.assertEqual(run.call_args.kwargs["stdout"], subprocess.DEVNULL)
        self.assertEqual(run.call_args.kwargs["stderr"], subprocess.DEVNULL)
        self.assertNotIn("capture_output", run.call_args.kwargs)

    def test_start_uses_noncapturing_process_runner(self):
        with patch.object(local_postgres.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)):
            with patch.object(local_postgres, "_port_is_available", return_value=True):
                with patch.object(local_postgres, "_run") as run:
                    local_postgres._start(Path("C:/test-postgres/bin"), 55432)
        self.assertEqual(run.call_args.kwargs["timeout"], 75)
        self.assertIs(run.call_args.kwargs["capture_output"], False)


if __name__ == "__main__":
    unittest.main()
