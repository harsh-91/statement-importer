# Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0
import unittest
from unittest.mock import patch

from statement_importer.windows_package import is_msix_package
import app as web_app


class WindowsPackageTests(unittest.TestCase):
    def test_environment_override_is_deterministic(self):
        for value in ("1", "true", "YES"):
            with self.subTest(value=value), patch.dict("os.environ", {"STATEMENT_IMPORTER_MSIX": value}):
                self.assertTrue(is_msix_package())
        with patch.dict("os.environ", {"STATEMENT_IMPORTER_MSIX": "0"}):
            self.assertFalse(is_msix_package())

    def test_store_installation_has_store_managed_update_page(self):
        with patch.object(web_app, "is_msix_package", return_value=True):
            response = web_app.app.test_client().get("/updates")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"STORE-MANAGED UPDATES ACTIVE", response.data)
        self.assertNotIn(b"DOWNLOAD + VERIFY SIGNATURE", response.data)


if __name__ == "__main__":
    unittest.main()
