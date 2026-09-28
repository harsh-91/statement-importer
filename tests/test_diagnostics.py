# Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0
import json
import io
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
             patch.object(web, "create_diagnostic_bundle", return_value=fake_bundle), \
             patch.object(web, "submission_diagnostics", return_value={"report_id": "SI-test"}):
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

    def test_send_requires_review_and_uses_private_receiver(self):
        client = web.app.test_client()
        with client.session_transaction() as session:
            session["csrf_token"] = "test-token"
            session["diagnostic_bundle"] = str(diagnostics.REPORT_DIR / "report.zip")
        report = {"report_id": "SI-20260928-120000-ABC123", "application_version": "1.6.2", "system": {}, "checks": []}
        with patch.object(web.Path, "exists", return_value=True), \
             patch.object(web, "run_diagnostics", return_value=[]), \
             patch.object(web, "submission_diagnostics", return_value=report), \
             patch.object(web, "send_bug_report", return_value="https://github.com/harsh-91/statement-importer-bug-reports/issues/1") as sender:
            denied = client.post("/diagnostics", data={"csrf_token": "test-token", "action": "send", "description": "Setup fails every time"})
            self.assertIn(b"confirm before sending", denied.data)
            self.assertFalse(sender.called)
            accepted = client.post("/diagnostics", data={"csrf_token": "test-token", "action": "send", "description": "Setup fails every time", "consent": "yes"})
            self.assertIn(b"Bug report sent", accepted.data)
            sender.assert_called_once()

    def test_submission_excludes_bundle_events_and_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / "report.zip"
            with zipfile.ZipFile(bundle, "w") as archive:
                archive.writestr("diagnostic-report.json", json.dumps({
                    "report_id": "SI-20260928-120000-ABC123", "application_version": "1.6.2",
                    "system": {"os": "Windows", "release": "11", "architecture": "AMD64"},
                    "checks": [{"name": "Connection", "status": "fail", "detail": "password=hunter2"}],
                    "evidence": {"secret": "private"},
                }))
                archive.writestr("setup-events.jsonl", '{"message":"sensitive event"}')
            payload = diagnostics.submission_diagnostics(bundle)
            serialized = json.dumps(payload)
            self.assertNotIn("hunter2", serialized)
            self.assertNotIn("sensitive event", serialized)
            self.assertNotIn("private", serialized)

    def test_submission_posts_only_reviewed_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / "report.zip"
            with zipfile.ZipFile(bundle, "w") as archive:
                archive.writestr("diagnostic-report.json", json.dumps({
                    "report_id": "SI-20260928-120000-ABC123", "application_version": "1.6.2",
                    "system": {"os": "Windows"}, "checks": [], "evidence": {"private": "do not send"},
                }))
            reply = io.BytesIO(b'{"issue_url":"https://github.com/harsh-91/statement-importer-bug-reports/issues/7"}')
            with patch.object(diagnostics, "_report_endpoint", return_value="https://example.workers.dev/report"), \
                 patch.object(diagnostics.REPORT_OPENER, "open", return_value=reply) as opener:
                issue_url = diagnostics.send_bug_report(bundle, "Setup fails on launch")
            self.assertTrue(issue_url.endswith("/issues/7"))
            posted = json.loads(opener.call_args.args[0].data)
            self.assertEqual(posted["description"], "Setup fails on launch")
            self.assertNotIn("evidence", posted["diagnostics"])


if __name__ == "__main__":
    unittest.main()
