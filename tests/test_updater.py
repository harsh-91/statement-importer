# Created by Harsh (@harsh-91) | Made in India
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from statement_importer import updater


def response(payload: bytes):
    return io.BytesIO(payload)


class UpdateMetadataTests(unittest.TestCase):
    def test_versions_are_strict_and_ordered(self):
        self.assertEqual(updater._version_tuple("v1.3.0"), (1, 3, 0))
        self.assertGreater(updater._version_tuple("1.10.0"), updater._version_tuple("1.9.9"))
        for invalid in ("1.2", "1.2.3-beta", "latest", "1.2.3.4"):
            with self.subTest(invalid=invalid), self.assertRaises(updater.UpdateError):
                updater._version_tuple(invalid)

    def test_only_trusted_https_hosts_are_allowed(self):
        updater._validate_url("https://github.com/harsh-91/statement-importer")
        for untrusted in (
            "http://github.com/file.exe", "https://example.com/file.exe",
            "https://user:password@github.com/file.exe",
        ):
            with self.subTest(untrusted=untrusted), self.assertRaises(updater.UpdateError):
                updater._validate_url(untrusted)

    def test_checksum_manifest_requires_one_exact_match(self):
        digest = "A" * 64
        self.assertEqual(updater._expected_checksum(f"{digest}  release.exe\n", "release.exe"), digest)
        with self.assertRaises(updater.UpdateError):
            updater._expected_checksum(f"{digest}  other.exe\n", "release.exe")
        with self.assertRaises(updater.UpdateError):
            updater._expected_checksum(f"{digest}  release.exe\n{digest}  release.exe\n", "release.exe")

    def test_latest_release_requires_exact_assets(self):
        release = {
            "tag_name": "v1.4.0", "html_url": "https://github.com/harsh-91/statement-importer/releases/tag/v1.4.0",
            "name": "1.4.0", "published_at": "2026-09-21T00:00:00Z", "body": "Safe update",
            "assets": [
                {"name": "StatementImporter-1.4.0-Setup-x64.exe", "state": "uploaded", "size": 4,
                 "digest": "sha256:abcd", "browser_download_url": "https://github.com/harsh-91/statement-importer/releases/download/v1.4.0/StatementImporter-1.4.0-Setup-x64.exe"},
                {"name": "SHA256SUMS.txt", "state": "uploaded", "size": 80, "digest": "",
                 "browser_download_url": "https://github.com/harsh-91/statement-importer/releases/download/v1.4.0/SHA256SUMS.txt"},
            ],
        }
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(updater, "UPDATE_DIR", Path(folder)), \
             patch.object(updater, "CACHE_PATH", Path(folder) / "latest.json"), \
             patch.object(updater, "_open", return_value=response(json.dumps(release).encode())):
            result = updater.check_latest_release()
            self.assertTrue(result["update_available"])
            self.assertEqual(result["latest_version"], "1.4.0")


class VerifiedDownloadTests(unittest.TestCase):
    def test_download_requires_hash_and_signature_before_becoming_ready(self):
        payload = b"signed installer test bytes"
        digest = hashlib.sha256(payload).hexdigest().upper()
        release = {
            "update_available": True, "latest_version": "1.4.0",
            "checksums_url": "https://github.com/checksums",
            "installer": {
                "name": "StatementImporter-1.4.0-Setup-x64.exe", "url": "https://github.com/installer",
                "size": len(payload), "digest": f"sha256:{digest.lower()}",
            },
        }
        manifest = f"{digest}  {release['installer']['name']}\n".encode()
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(updater, "UPDATE_DIR", Path(folder)), \
             patch.object(updater, "READY_PATH", Path(folder) / "ready.json"), \
             patch.object(updater, "check_latest_release", return_value=release), \
             patch.object(updater, "_open", side_effect=[response(manifest), response(payload)]), \
             patch.object(updater, "authenticode_status", return_value={"status": "Valid", "subject": "SignPath Foundation", "thumbprint": "ABC"}):
            ready = updater.download_verified_update()
            self.assertEqual(ready["sha256"], digest)
            self.assertTrue(Path(ready["path"]).is_file())
            self.assertTrue((Path(folder) / "ready.json").is_file())

    def test_signature_failure_never_promotes_partial_download(self):
        payload = b"unsigned installer"
        digest = hashlib.sha256(payload).hexdigest().upper()
        name = "StatementImporter-1.4.0-Setup-x64.exe"
        release = {
            "update_available": True, "latest_version": "1.4.0", "checksums_url": "https://github.com/checksums",
            "installer": {"name": name, "url": "https://github.com/installer", "size": len(payload),
                          "digest": f"sha256:{digest.lower()}"},
        }
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(updater, "UPDATE_DIR", Path(folder)), \
             patch.object(updater, "READY_PATH", Path(folder) / "ready.json"), \
             patch.object(updater, "check_latest_release", return_value=release), \
             patch.object(updater, "_open", side_effect=[response(f"{digest}  {name}\n".encode()), response(payload)]), \
             patch.object(updater, "authenticode_status", side_effect=updater.UpdateError("unsigned")):
            with self.assertRaisesRegex(updater.UpdateError, "unsigned"):
                updater.download_verified_update()
            self.assertFalse((Path(folder) / name).exists())
            self.assertFalse((Path(folder) / f"{name}.partial").exists())
            self.assertFalse((Path(folder) / "ready.json").exists())


if __name__ == "__main__":
    unittest.main()
