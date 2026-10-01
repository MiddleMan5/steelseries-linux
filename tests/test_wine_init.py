"""Exercise setup without changing the user's prefix or installing software."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "resources/wine-init.sh"

# External commands record their arguments and emulate success/failure. A
# wineserver wait fails immediately to model a prefix with a long-running app.
COMMAND = r'''
import json
import os
from pathlib import Path
import sys

name = Path(sys.argv[0]).name
args = sys.argv[1:]
prefix = Path(os.environ.get("WINEPREFIX", Path.home() / ".wine"))
with open(os.environ["CALL_LOG"], "a") as log:
    log.write(json.dumps([name, args, str(prefix)]) + "\n")
step = name
if name == "wine":
    step = args[0]
if step == os.environ.get("FAIL_STEP"):
    sys.exit(23)
if name == "wineboot":
    (prefix / "drive_c/windows/Fonts").mkdir(parents=True, exist_ok=True)
elif name == "fc-list":
    print(os.environ.get("SYSTEM_FONTS", ""))
elif name == "timeout":
    mode = os.environ.get("FONT_RESULT", "success")
    fonts = prefix / "drive_c/windows/Fonts"
    if mode in ("success", "partial_timeout"):
        (fonts / "arialbd.ttf").write_text("bold")
    if mode == "success":
        (fonts / "ariblk.ttf").write_text("black")
    sys.exit({"success": 0, "failed": 1, "partial_timeout": 124}[mode])
elif name == "wineserver":
    sys.exit("Wine applications are still running")
'''


class WineInitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="steelseries-test-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        for name in ("wine", "wineboot", "wineserver", "fc-list", "timeout", "winetricks"):
            command = self.bin / name
            command.write_text(f"#!{sys.executable}\n{COMMAND}")
            command.chmod(0o755)
        self.log = self.home / "calls.jsonl"
        self.prefix = self.home / "custom prefix"
        self.env = dict(os.environ, HOME=str(self.home), WINEPREFIX=str(self.prefix),
                        PATH=f"{self.bin}:/usr/bin:/bin", CALL_LOG=str(self.log))
        self.env.pop("FAIL_STEP", None)
        self.env.pop("FONT_RESULT", None)
        fonts = self.home / "system fonts"
        fonts.mkdir()
        paths = [fonts / "ArialBD.TTF", fonts / "ariblk.ttf"]
        for path in paths:
            path.write_text(path.name)
        # A suffix match must not accidentally copy this nonexistent file.
        self.env["SYSTEM_FONTS"] = "\n".join([str(fonts / "notarialbd.ttf"), *map(str, paths)])

    def run_setup(self):
        return subprocess.run(["/bin/bash", str(SCRIPT)], env=self.env,
                              capture_output=True, text=True, timeout=10)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def registered_fonts(self):
        return [args[args.index("/v") + 1] for name, args, _ in self.calls()
                if name == "wine" and args[:2] == ["reg", "add"] and "Fonts" in args[2]]

    def test_configures_prefix_with_spaces_without_waiting_for_other_apps(self):
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Wine configuration complete", result.stdout)
        self.assertTrue(all(prefix == str(self.prefix) for _, _, prefix in self.calls()))
        self.assertNotIn("wineserver", [name for name, _, _ in self.calls()])
        self.assertEqual(self.registered_fonts(), ["Arial Bold (TrueType)", "Arial Black (TrueType)"])
        self.assertEqual((self.prefix / "drive_c/windows/Fonts/arialbd.ttf").read_text(), "ArialBD.TTF")
        self.assertNotIn("timeout", [name for name, _, _ in self.calls()])
        # Reruns must also register fonts already present in the prefix.
        self.env["SYSTEM_FONTS"] = ""
        self.assertEqual(self.run_setup().returncode, 0)
        self.assertEqual(len(self.registered_fonts()), 4)
        self.assertNotIn("timeout", [name for name, _, _ in self.calls()])

    def test_unset_or_empty_prefix_uses_home_for_all_commands(self):
        for value in (None, ""):
            with self.subTest(value=value):
                if value is None:
                    self.env.pop("WINEPREFIX")
                else:
                    self.env["WINEPREFIX"] = value
                result = self.run_setup()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(all(prefix == str(self.home / ".wine") for _, _, prefix in self.calls()))

    def test_storage_workaround_is_scoped_to_gg_launcher(self):
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        overrides = [args for name, args, _ in self.calls()
                     if name == "wine" and args[:2] == ["reg", "add"]
                     and "DllOverrides" in args[2]]
        self.assertEqual(len(overrides), 1)
        args = overrides[0]
        self.assertEqual(args[2], r"HKEY_CURRENT_USER\Software\Wine\AppDefaults\SteelSeriesGGEZ.exe\DllOverrides")
        self.assertEqual(args[args.index("/v") + 1], "windows.storage.applicationdata")
        self.assertEqual(args[args.index("/d") + 1], "")

    def test_required_failures_stop_setup(self):
        for step in ("wineboot", "winecfg", "reg", "fc-list"):
            with self.subTest(step=step):
                self.env["FAIL_STEP"] = step
                self.log.write_text("")
                result = self.run_setup()
                self.assertEqual(result.returncode, 23, result.stderr)
                self.assertNotIn("Wine configuration complete", result.stdout)
                self.assertNotIn("timeout", [name for name, _, _ in self.calls()])

    def test_optional_font_install_success(self):
        self.env["SYSTEM_FONTS"] = ""
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.registered_fonts()), 2)
        self.assertNotIn("could not install", result.stderr)

    def test_optional_font_install_failure_warns_and_continues(self):
        self.env.update(SYSTEM_FONTS="", FONT_RESULT="failed")
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("winetricks corefonts failed", result.stderr)
        self.assertIn("could not install the following fonts: arialbd.ttf ariblk.ttf", result.stderr)
        self.assertIn("Wine configuration complete", result.stdout)

    def test_missing_fonts_without_winetricks_warn_and_continue(self):
        self.env["SYSTEM_FONTS"] = ""
        self.env["PATH"] = str(self.bin)
        (self.bin / "winetricks").unlink()
        for name in ("realpath", "awk", "cat"):
            (self.bin / name).symlink_to(shutil.which(name))
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("could not install the following fonts: arialbd.ttf ariblk.ttf", result.stderr)
        self.assertIn("Wine configuration complete", result.stdout)

    def test_font_timeout_registers_partial_download_and_warns(self):
        self.env.update(SYSTEM_FONTS="", FONT_RESULT="partial_timeout")
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("winetricks timed out", result.stderr)
        self.assertIn("could not install the following fonts: ariblk.ttf", result.stderr)
        self.assertEqual(self.registered_fonts(), ["Arial Bold (TrueType)"])

    def test_make_does_not_launch_installer_after_setup_failure(self):
        self.env["FAIL_STEP"] = "wineboot"
        result = subprocess.run(
            ["make", "install", "-o", "check", "-o", "udev-reload", "UDEV_RULES=",
             "ENGINE_EXE=/bin/true"], cwd=ROOT, env=self.env,
            capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("wine", [name for name, _, _ in self.calls()])

    def test_preinstall_detects_missing_timeout(self):
        self.env["PATH"] = str(self.bin)
        (self.bin / "timeout").unlink()
        for name in ("python3", "make", "bash", "curl", "udevadm"):
            (self.bin / name).symlink_to("/bin/true")
        result = subprocess.run(["/bin/bash", str(ROOT / "resources/preinstall-check.sh")],
                                env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Missing required prerequisites: timeout", result.stderr)


if __name__ == "__main__":
    unittest.main()
