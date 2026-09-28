# Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet

from statement_importer import config, local_postgres


@unittest.skipUnless(sys.platform == "darwin", "macOS beta checks")
class MacSupportTests(unittest.TestCase):
    def test_secret_round_trip_uses_authenticated_encryption(self):
        key = Fernet.generate_key()
        with patch.object(config, "_mac_key", return_value=key):
            protected = config._protect("private password")
            self.assertTrue(protected.startswith("fernet:"))
            self.assertNotIn("private password", protected)
            self.assertEqual(config._unprotect(protected), "private password")
            with self.assertRaises(config.ConfigError):
                config._unprotect("fernet:tampered")

    def test_postgres_override_accepts_native_mac_tools(self):
        with tempfile.TemporaryDirectory() as folder:
            binary = Path(folder)
            for name in ("initdb", "pg_ctl", "postgres"):
                (binary / name).touch()
            with patch.dict("os.environ", {"STATEMENT_IMPORTER_POSTGRES_BIN": str(binary)}):
                self.assertEqual(local_postgres.find_postgres_bin(), binary.resolve())
                self.assertEqual(local_postgres._tool(binary, "pg_ctl"), binary / "pg_ctl")

    def test_user_data_uses_application_support(self):
        self.assertEqual(config.CONFIG_DIR, Path.home() / "Library" / "Application Support" / "StatementImporter")
        self.assertEqual(local_postgres.LOCAL_STATE_DIR, config.CONFIG_DIR)


if __name__ == "__main__":
    unittest.main()
