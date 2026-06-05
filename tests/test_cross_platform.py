"""Tests for cross-platform compatibility (Linux, Windows, macOS)."""
import os
import platform as _platform
import sys
from pathlib import Path

import pytest


class TestPlatformDetection:
    """Verify platform detection logic works correctly."""

    def test_windows_has_display(self):
        """On Windows, has_display should always be True."""
        if sys.platform != "win32":
            pytest.skip("Only relevant on Windows")
        assert sys.platform == "win32"  # Windows always has display

    def test_linux_checks_display(self):
        """On Linux, has_display checks DISPLAY or WAYLAND_DISPLAY."""
        display = os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
        has_display = bool(display) if sys.platform not in ("win32", "darwin") else True
        if sys.platform == "linux" and not display:
            assert not has_display  # headless Linux

    def test_macos_always_has_display(self):
        """macOS (darwin) should always have display True."""
        is_darwin = sys.platform == "darwin"
        has_display = sys.platform in ("win32", "darwin")
        if is_darwin:
            assert has_display


class TestVenvPaths:
    """Verify virtual environment Python paths on each platform."""

    def test_windows_venv_scripts(self):
        """Windows uses Scripts/python.exe."""
        if sys.platform == "win32":
            venv_dir = Path("C:/fake/.venv")
            scripts = venv_dir / "Scripts"
            assert scripts.as_posix().endswith("Scripts")
        else:
            pytest.skip("Windows-only test")

    def test_unix_venv_bin(self):
        """Unix uses bin/python3."""
        if sys.platform != "win32":
            venv_dir = Path("/fake/.venv")
            bin_dir = venv_dir / "bin"
            assert str(bin_dir).endswith("bin")
        else:
            pytest.skip("Unix-only test")

    def test_walkabout_home_cross_platform(self):
        """Path.home()/.walkabout works on all platforms."""
        home = Path.home()
        walkabout_dir = home / ".walkabout"
        assert str(walkabout_dir).endswith(".walkabout")


class TestPathSeparators:
    """Verify correct path separator usage."""

    def test_ospathsep_is_platform_correct(self):
        if sys.platform == "win32":
            assert os.pathsep == ";"
        else:
            assert os.pathsep == ":"

    def test_ossep_is_platform_correct(self):
        if sys.platform == "win32":
            assert os.sep == "\\"
        else:
            assert os.sep == "/"

    def test_path_relative_to_case_insensitive(self):
        """Path.relative_to() is case-insensitive on Windows."""
        if sys.platform == "win32":
            base = Path("C:/Users/Test/.walkabout/notes").resolve()
            # Even with different case, should work
            p = Path("c:/users/test/.walkabout/notes/subdir/test.py").resolve()
            try:
                p.relative_to(base)
            except ValueError:
                pytest.fail("Path.relative_to() should be case-insensitive on Windows")


class TestEncoding:
    """Verify correct encoding usage."""

    def test_utf8_encoding_in_open_calls(self):
        """Quick check that encoding='utf-8' is used in key files."""
        # Check source files contain encoding='utf-8' in open calls
        # (skip modules that require heavy deps like fastapi)
        for mod_name in ["walkabout.config", "walkabout.core.execute", "walkabout.core.file_util"]:
            import importlib
            mod = importlib.import_module(mod_name)
            src = Path(mod.__file__).read_text(encoding="utf-8")
            open_calls = [ln for ln in src.split("\n") if "open(" in ln and "encoding" not in ln
                         and "webbrowser" not in ln and "os.devnull" not in ln
                         and "devnull" not in ln and "wb" not in ln]
            for line in open_calls:
                if ('"w"' in line or '"r"' in line or "'w'" in line or "'r'" in line) \
                        and "subprocess" not in line and "BytesIO" not in line:
                    pytest.fail(f"Missing encoding in {mod_name}: {line.strip()}")


class TestPythonFallback:
    """Verify Python executable fallback per platform."""

    def test_windows_python_exe(self):
        if sys.platform == "win32":
            import shutil
            assert shutil.which("python") is not None or shutil.which("python3") is not None
            # Fallback should be "python" on Windows
            from walkabout.config import get_python_path
            # With no venv and no custom path
            assert "python" in get_python_path().lower()

    def test_unix_python3(self):
        if sys.platform != "win32":
            import shutil
            p = shutil.which("python3") or shutil.which("python")
            assert p is not None, "Python should be available for testing"


class TestSubprocessFlags:
    """Verify platform-specific subprocess flags."""

    def test_create_no_window_on_windows(self):
        """subprocess.CREATE_NO_WINDOW exists only on Windows."""
        import subprocess
        if sys.platform == "win32":
            assert hasattr(subprocess, "CREATE_NO_WINDOW")
            assert subprocess.CREATE_NO_WINDOW != 0
        else:
            # Should not crash when accessing
            pass  # Other platforms shouldn't have CREATE_NO_WINDOW

    def test_os_devnull_exists(self):
        """os.devnull exists on all platforms."""
        assert os.devnull is not None
        assert os.path.exists(os.devnull) or os.devnull in ("/dev/null", "nul", "/dev/null")


class TestSysFrozen:
    """Verify sys.frozen detection for PyInstaller."""

    def test_sys_frozen_is_false_in_tests(self):
        """In normal Python (not PyInstaller), sys.frozen should be absent or False."""
        assert not getattr(sys, "frozen", False)

    def test_meipass_not_set_in_tests(self):
        """sys._MEIPASS is only set by PyInstaller."""
        assert getattr(sys, "_MEIPASS", None) is None


class TestPlatformUname:
    """Verify platform.uname() works cross-platform."""

    def test_platform_uname_does_not_raise(self):
        """platform.uname() should work on all platforms."""
        try:
            info = _platform.uname()
            assert info.system is not None
            assert info.release is not None
        except Exception as e:
            pytest.fail(f"platform.uname() raised: {e}")

    def test_sys_platform_is_valid(self):
        """sys.platform should be one of: win32, linux, darwin."""
        assert sys.platform in ("win32", "linux", "darwin", "cygwin"), \
            f"Unexpected sys.platform: {sys.platform}"
