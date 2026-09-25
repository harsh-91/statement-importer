# Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from statement_importer import diagnostics
import app as web


class DiagnosticTests(unittest.TestCase):
    def test_sanitizer_removes_credentials_user_path_and_remote_address(self):
        sample = f"password=hunter2 postgresql://owner:secret@10.1.2.3/db {Path.home()} token=abc123"
        cleaned = diagnostics.sanitize_text(sample)
        for secret in ("hunter2", "owner:secret", "10.1.2.3", str(Path.home()), "abc123"):
            self.assertNotIn(secret, cleaned)
        self.assertIn("[REDACTED]", cleaned)

    def test_bundle_contains_only_expected_support_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            event_log = root / "setup-events.jsonl"
            event_log.write_text('{"message":"password=secret"}\n', encoding="utf-8")
            with patch.object(diagnostics, "REPORT_DIR", root / "reports"), \
                 patch.object(diagnostics, "EVENT_LOG", event_log), \
                 patch.object(diagnostics, "CONFIG_PATH", root / "config.json"), \
                 patch.object(diagnostics, "METADATA_PATH", root / "cluster.json"), \
                 patch.object(diagnostics, "DATA_DIR", root / "data"), \
                 patch.object(diagnostics, "LOG_PATH", root / "postgresql.log"):
                target = diagnostics.create_diagnostic_bundle([
                    {"name": "Test", "status": "pass", "detail": "Ready", "action": ""}
                ])
            with zipfile.ZipFile(target) as archive:
                self.assertEqual(set(archive.namelist()), {"diagnostic-report.json", "setup-events.jsonl", "README.txt"})
                report = json.loads(archive.read("diagnostic-report.json"))
                events = archive.read("setup-events.jsonl").decode()
            self.assertIn("No statements", report["privacy"])
            self.assertNotIn("password=secret", events)
            self.assertIn("[REDACTED]", events)

    def test_diagnostics_page_creates_bundle_with_csrf(self):
        client = web.app.test_client()
        with client.session_transaction() as session:
            session["csrf_token"] = "test-token"
        fake_checks = [{"name": "PostgreSQL tools", "status": "pass", "detail": "Ready", "action": ""}]
        fake_bundle = Path.home() / "Documents" / "Statement Importer Reports" / "report.zip"
        with patch.object(web, "run_diagnostics", return_value=fake_checks), \
             patch.object(web, "create_diagnostic_bundle", return_value=fake_bundle):
            response = client.post("/diagnostics", data={"csrf_token": "test-token", "action": "create"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Diagnostic bundle created", response.data)
        self.assertIn(b"report.zip", response.data)

    def test_setup_failure_is_recorded_and_returns_diagnostic_link(self):
        client = web.app.test_client()
        with client.session_transaction() as session:
            session["csrf_token"] = "test-token"
        with patch.object(web, "start_setup_run", return_value="run-1"), \
             patch.object(web, "record_setup_event") as record, \
             patch.object(web, "provision_managed_postgres", side_effect=web.LocalPostgresError("Tools missing")):
            response = client.post(
                "/setup", data={"csrf_token": "test-token", "mode": "automatic"},
                headers={"X-Setup-Request": "1"},
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["diagnostics"], "/diagnostics")
        self.assertTrue(any(call.args[1] == "failed" for call in record.call_args_list))

    def test_support_draft_does_not_expose_local_report_path(self):
        bundle = Path.home() / "Documents" / "Statement Importer Reports" / "safe-report.zip"
        with patch.object(diagnostics, "open_report_folder"), patch.object(diagnostics.webbrowser, "open") as opener:
            diagnostics.open_support_draft(bundle)
            self.assertIn("mailto:harshnair02@hotmail.com", opener.call_args.args[0])
        draft_url = opener.call_args.args[0]
        self.assertIn("safe-report.zip", draft_url)
        self.assertNotIn("Documents", draft_url)
        self.assertNotIn(Path.home().name, draft_url)


if __name__ == "__main__":
    unittest.main()
