# Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0
import unittest
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


if __name__ == "__main__":
    unittest.main()
