"""Check Wine version guidance without depending on the host's packages."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "resources/preinstall-check.sh"


class PreinstallCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="steelseries-preinstall-")
        self.addCleanup(self.temp.cleanup)
        self.bin = Path(self.temp.name)
        for name in ("python3", "wineboot", "make", "bash", "fc-list", "curl",
                     "udevadm", "timeout", "winetricks", "ntlm_auth"):
            (self.bin / name).symlink_to("/bin/true")
        wine = self.bin / "wine"
        wine.write_text('#!/bin/sh\nprintf "%s\\n" "$TEST_WINE_VERSION"\n')
        wine.chmod(0o755)

    def check_version(self, version):
        result = subprocess.run(
            ["/bin/bash", str(SCRIPT)],
            env=dict(os.environ, PATH=str(self.bin), TEST_WINE_VERSION=version),
            capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def test_versions_before_certificate_fix_warn(self):
        for version in ("wine-9.0 (Ubuntu 9.0~repack-4build3)", "wine-10.0",
                        "wine-11.0", "wine-11.8 (Staging)"):
            with self.subTest(version=version):
                result = self.check_version(version)
                self.assertIn("Wine 11.9 or newer", result.stderr)
                self.assertIn("0x80092023", result.stderr)

    def test_versions_with_certificate_fix_do_not_warn(self):
        for version in ("wine-11.9", "wine-11.18 (Staging)", "wine-12.0"):
            with self.subTest(version=version):
                self.assertEqual(self.check_version(version).stderr, "")

    def test_unknown_version_reports_uncertainty(self):
        self.assertIn("Could not determine Wine version", self.check_version("custom build").stderr)

    def test_missing_ntlm_helper_is_separate_optional_dependency(self):
        (self.bin / "ntlm_auth").unlink()
        result = self.check_version("wine-11.18")
        self.assertEqual(result.stderr, "")
        self.assertIn("winbind", result.stdout)
        self.assertIn("separate from GG's certificate startup crash", result.stdout)


if __name__ == "__main__":
    unittest.main()
