# Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0
import unittest
from unittest.mock import Mock, patch

import app as web_app
import desktop
from statement_importer import database


class DatabaseConnectionTimeoutTests(unittest.TestCase):
    def test_every_database_connection_has_a_five_second_timeout(self):
        settings = {
            "POSTGRES_HOST": "unreachable.invalid", "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "statements", "POSTGRES_USER": "user", "POSTGRES_PASSWORD": "secret",
        }
        with patch.object(database.psycopg, "connect", return_value="connection") as connect:
            self.assertEqual(database.connect(settings), "connection")
        self.assertEqual(connect.call_args.kwargs["connect_timeout"], 5)
        self.assertEqual(connect.call_args.kwargs["application_name"], "statement-importer")

    def test_connection_error_is_bounded_and_actionable(self):
        message = web_app.friendly_database_error(Exception("connection timed out\nextra diagnostics"))
        self.assertIn("within 5 seconds", message)
        self.assertIn("Check the host", message)
        self.assertNotIn("extra diagnostics", message)

    def test_desktop_server_is_threaded(self):
        fake_server = Mock()
        fake_server.server_port = 8765
        with patch.object(desktop, "make_server", return_value=fake_server) as make_server:
            desktop.LocalServer()
        make_server.assert_called_once_with("127.0.0.1", 8765, desktop.app, threaded=True)

    def test_failed_manual_connection_returns_to_wizard(self):
        client = web_app.app.test_client()
        with client.session_transaction() as session:
            session["csrf_token"] = "test-token"
        form = {
            "csrf_token": "test-token", "mode": "manual", "host": "unreachable.invalid",
            "port": "5432", "database": "statements", "user": "user", "password": "secret",
        }
        with patch.object(
            web_app, "provision_database",
            side_effect=web_app.psycopg.OperationalError("connection timed out\ninternal detail"),
        ):
            response = client.post("/setup", data=form)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Could not connect", response.data)
        self.assertIn(b"within 5 seconds", response.data)
        self.assertNotIn(b"internal detail", response.data)


if __name__ == "__main__":
    unittest.main()
