# Created by Harsh Nair | Made in India | SPDX-License-Identifier: Apache-2.0
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import hashlib

ROOT = Path(__file__).resolve().parents[1]
CSC = Path(os.environ.get("WINDIR", "C:/Windows")) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
PS = Path(os.environ.get("WINDIR", "C:/Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"


@unittest.skipUnless(os.name == "nt" and CSC.exists(), "Requires Windows and the .NET compiler")
class UpgradeIntegrationTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('RUN_INSTALLER_TEST') == '1', 'Opt-in compiled installer integration')
    def test_real_installer_blocks_busy_file_then_completes_after_close(self):
        installer = ROOT / 'dist/StatementImporter-UpgradeTest.exe'
        self.assertTrue(installer.exists())
        with tempfile.TemporaryDirectory(prefix='installer-e2e-') as folder:
            root = Path(folder)
            target = root / 'StatementImporter.exe'
            subprocess.run([str(CSC), '/nologo', '/out:' + str(target),
                            str(ROOT / 'tests/fixtures/UpgradeWorker.cs')], check=True, capture_output=True)
            old_hash = hashlib.sha256(target.read_bytes()).hexdigest()
            process = subprocess.Popen([str(target)], creationflags=0x08000000)
            command = [str(installer), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/SP-', '/NORESTART',
                       '/TASKS=', '/DIR=' + str(root), '/LOG=' + str(root / 'setup.log')]
            try:
                failed = subprocess.run(command, timeout=45, creationflags=0x08000000)
                self.assertNotEqual(failed.returncode, 0)
                self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), old_hash)
                self.assertIsNone(process.poll())
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
            succeeded = subprocess.run(command, timeout=60, creationflags=0x08000000)
            self.assertEqual(succeeded.returncode, 0, (root / 'setup.log').read_text(errors='replace'))
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(),
                             hashlib.sha256((ROOT / 'dist/StatementImporter.exe').read_bytes()).hexdigest())

    def test_running_upgrade_is_scoped_verified_and_requires_force(self):
        with tempfile.TemporaryDirectory(prefix="statement-upgrade-") as folder:
            root = Path(folder)
            installed = root / "installed"
            unrelated = root / "unrelated"
            installed.mkdir()
            unrelated.mkdir()
            executable = installed / "StatementImporter.exe"
            subprocess.run([str(CSC), "/nologo", "/out:" + str(executable),
                            str(ROOT / "tests/fixtures/UpgradeWorker.cs")], check=True, capture_output=True)
            shutil.copy2(executable, unrelated / executable.name)
            target = subprocess.Popen([str(executable)], creationflags=0x08000000)
            other = subprocess.Popen([str(unrelated / executable.name)], creationflags=0x08000000)
            try:
                result = root / "status.txt"
                command = [str(PS), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                           "-File", str(ROOT / "installer/close-installed-app.ps1"),
                           "-Executable", str(executable), "-ResultPath", str(result)]
                subprocess.run(command, check=True, timeout=25, capture_output=True)
                self.assertEqual(result.read_text(), "busy")
                self.assertIsNone(target.poll(), "Graceful attempt must not force a background process")
                subprocess.run(command + ["-Force"], check=True, timeout=25, capture_output=True)
                self.assertEqual(result.read_text(), "ready")
                target.wait(timeout=3)
                self.assertIsNone(other.poll(), "A same-named executable elsewhere must survive")
                # File replacement proves that the helper did not simply assume closure.
                executable.rename(installed / "old.exe")
                shutil.copy2(unrelated / executable.name, executable)
                subprocess.run(command, check=True, timeout=25, capture_output=True)
                self.assertEqual(result.read_text(), "ready")
            finally:
                for process in (target, other):
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=5)
