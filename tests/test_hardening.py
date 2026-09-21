# Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0
import csv
import json
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch

from statement_importer import mapping
from statement_importer.parsers import StatementError, _validate_ooxml_archive
from statement_importer.security import safe_csv_row, safe_spreadsheet_cell


class ExportSafetyTests(unittest.TestCase):
    def test_formula_prefixes_are_neutralized(self):
        for value in ("=1+1", "+SUM(A1)", "-2+3", "@cmd", "\tformula"):
            with self.subTest(value=value):
                self.assertEqual(safe_spreadsheet_cell(value), "'" + value)
        self.assertEqual(safe_spreadsheet_cell("ordinary text"), "ordinary text")

    def test_csv_writer_receives_neutralized_values(self):
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=["description", "amount"])
        writer.writeheader()
        writer.writerow(safe_csv_row({"description": "=HYPERLINK(\"bad\")", "amount": "100.00"}))
        self.assertIn("'=HYPERLINK", output.getvalue())


class PendingFileTests(unittest.TestCase):
    def test_pending_payload_is_encrypted_and_round_trips(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(mapping, "PENDING_DIR", Path(folder)):
            token = mapping.save_pending(b"private statement bytes", "safe.csv")
            stored = (Path(folder) / f"{token}.bin").read_bytes()
            self.assertNotIn(b"private statement bytes", stored)
            payload, filename = mapping.load_pending(token)
            self.assertEqual(payload, b"private statement bytes")
            self.assertEqual(filename, "safe.csv")

    def test_expired_pending_payload_is_removed(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(mapping, "PENDING_DIR", Path(folder)):
            token = mapping.save_pending(b"private", "safe.csv")
            metadata_path = Path(folder) / f"{token}.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["created_at"] = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            with self.assertRaises(StatementError):
                mapping.load_pending(token)
            self.assertFalse((Path(folder) / f"{token}.bin").exists())


class WorkbookSafetyTests(unittest.TestCase):
    def test_extreme_compression_ratio_is_rejected(self):
        output = BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("xl/worksheets/sheet1.xml", b"0" * 2_000_000)
        with self.assertRaisesRegex(StatementError, "compression ratio"):
            _validate_ooxml_archive(output.getvalue())

    def test_invalid_zip_is_rejected(self):
        with self.assertRaisesRegex(StatementError, "valid Excel"):
            _validate_ooxml_archive(b"PK\x03\x04not-a-real-archive")


if __name__ == "__main__":
    unittest.main()
