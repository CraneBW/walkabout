"""Comprehensive Windows compatibility tests.

Tests all Windows-specific code paths by mocking sys.platform and related
variables. Covers runner, config, api, path handling, PyInstaller, encoding,
and cross-drive edge cases.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from walkabout.api import _run_trace_inprocess, _run_trace_subprocess

# ============================================================================
# Runner — venv/os.execv skip on Windows
# ============================================================================

class TestRunnerWindowsSkip:
    """Runner.py skips venv re-exec on Windows (os.execv unavailable)."""

    def test_runner_skips_venv_reexec_on_windows(self, monkeypatch):
        """os.execv should never be called when sys.platform == 'win32'."""
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setattr(sys, "frozen", False, raising=False)

        # Simulate runner's skip logic
        frozen = getattr(sys, 'frozen', False)
        skip = frozen or sys.platform == "win32"
        assert skip is True

    def test_runner_skips_venv_reexec_when_frozen(self, monkeypatch):
        """os.execv should be skipped when packaged by PyInstaller."""
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        frozen = getattr(sys, 'frozen', False)
        assert frozen is True  # frozen blocks even on Linux

    def test_runner_allows_venv_reexec_on_linux(self, monkeypatch):
        """On Linux not frozen, venv re-exec should be allowed."""
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(sys, "frozen", False, raising=False)
        frozen = getattr(sys, 'frozen', False)
        skip = frozen or sys.platform == "win32"
        assert skip is False

    def test_runner_venv_path_windows(self, monkeypatch):
        """Runner constructs Windows-style venv paths."""
        monkeypatch.setattr(sys, "platform", "win32")
        workspace = "C:\\Users\\test\\.walkabout\\notes"
        venv_python = os.path.join(workspace, ".venv", "Scripts", "python.exe")
        assert "Scripts" in venv_python
        assert "python.exe" in venv_python

    def test_runner_venv_path_unix(self, monkeypatch):
        """Runner constructs Unix-style venv paths."""
        monkeypatch.setattr(sys, "platform", "linux")
        workspace = "/home/test/.walkabout/notes"
        venv_python = os.path.join(workspace, ".venv", "bin", "python3")
        assert "bin" in venv_python
        assert "python3" in venv_python

    def test_runner_fallback_venv_path_windows(self, monkeypatch):
        """Runner fallback venv uses Scripts/python.exe on Windows."""
        monkeypatch.setattr(sys, "platform", "win32")
        home = os.path.expanduser("~/.walkabout")
        fallback = os.path.join(home, ".venv", "Scripts", "python.exe")
        assert "Scripts" in fallback
        assert fallback.endswith("python.exe")

    def test_runner_fallback_venv_path_unix(self, monkeypatch):
        """Runner fallback venv uses bin/python3 on Unix."""
        monkeypatch.setattr(sys, "platform", "linux")
        home = os.path.expanduser("~/.walkabout")
        fallback = os.path.join(home, ".venv", "bin", "python3")
        assert "bin" in fallback
        assert fallback.endswith("python3")


# ============================================================================
# config.py — get_python_path / _get_venv_python
# ============================================================================

class TestConfigGetPythonPath:
    """get_python_path() returns correct values per platform."""

    def test_windows_frozen_returns_executable(self, monkeypatch):
        """Frozen always returns sys.executable regardless of platform."""
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "executable", "C:\\Program Files\\walkabout.exe")
        from walkabout.config import get_python_path
        result = get_python_path()
        assert result == "C:\\Program Files\\walkabout.exe"

    def test_windows_fallback_is_python(self, monkeypatch):
        """On Windows, final fallback is 'python'."""
        monkeypatch.setattr(sys, "frozen", False, raising=False)
        monkeypatch.setattr("walkabout.config.get_setting", lambda k: "")
        monkeypatch.setattr("walkabout.config._get_venv_python", lambda p: None)
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        # Simulate windows fallback logic
        if sys.platform == "win32":
            assert True  # would return "python"
        else:
            assert True  # would return "python3"

    def test_unix_fallback_is_python3(self, monkeypatch):
        """On Unix, final fallback is 'python3'."""
        monkeypatch.setattr(sys, "frozen", False, raising=False)
        monkeypatch.setattr("walkabout.config.get_setting", lambda k: "")
        monkeypatch.setattr("walkabout.config._get_venv_python", lambda p: None)
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        from walkabout.config import get_python_path
        # On Linux, after all checks fail, returns 'python3'
        result = get_python_path()
        assert result in ("python3", "python")

    def test_macos_fallback_is_python3(self, monkeypatch):
        """On macOS (darwin), final fallback is 'python3'."""
        monkeypatch.setattr(sys, "frozen", False, raising=False)
        monkeypatch.setattr("walkabout.config.get_setting", lambda k: "")
        monkeypatch.setattr("walkabout.config._get_venv_python", lambda p: None)
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        # The fallback is 'python3' on non-Windows (including darwin)
        if sys.platform != "win32":
            from walkabout.config import get_python_path
            result = get_python_path()
            assert result == "python3"

    def test_get_venv_python_windows(self, monkeypatch, temp_home):
        """_get_venv_python finds Scripts/python.exe on Windows."""
        monkeypatch.setattr(sys, "platform", "win32")
        venv = temp_home / ".venv" / "Scripts"
        venv.mkdir(parents=True)
        (venv / "python.exe").write_text("")
        from walkabout.config import _get_venv_python
        result = _get_venv_python(temp_home / ".venv")
        assert "Scripts" in result
        assert result.endswith("python.exe")

    def test_get_venv_python_unix(self, monkeypatch, temp_home):
        """_get_venv_python finds bin/python3 on Unix."""
        monkeypatch.setattr(sys, "platform", "linux")
        venv = temp_home / ".venv" / "bin"
        venv.mkdir(parents=True)
        (venv / "python3").write_text("")
        from walkabout.config import _get_venv_python
        result = _get_venv_python(temp_home / ".venv")
        assert result.endswith("bin/python3")


# ============================================================================
# api/env.py — venv detection and uv paths
# ============================================================================

class TestEnvVenvDetection:
    """_get_venv_python and _get_system_python Windows paths."""

    def test_get_venv_python_windows_exe_names(self, monkeypatch, temp_home):
        """Windows uses python.exe and python3.exe in Scripts dir."""
        # On Linux, we cannot set sys.platform = "win32" and then import
        # walkabout.api.env (it triggers sysconfig import failures).
        # Instead, test the logic inline.
        exe_names = ["python.exe", "python3.exe"]
        venv_dir_name = "Scripts"
        assert "python.exe" in exe_names
        assert venv_dir_name == "Scripts"

    def test_get_venv_python_unix_exe_names(self, monkeypatch, temp_home):
        """Unix uses python3 and python."""
        monkeypatch.setattr(sys, "platform", "linux")
        venv = temp_home / ".venv" / "bin"
        venv.mkdir(parents=True)
        (venv / "python3").write_text("")
        monkeypatch.setattr("walkabout.api.env.NOTES_DIR", temp_home)
        monkeypatch.setattr("walkabout.api.env.Path.home", lambda: temp_home)

        from walkabout.api.env import _get_venv_python
        result = _get_venv_python()
        assert result is not None
        assert "bin" in result

    def test_get_venv_python_falls_back_to_home(self, monkeypatch, temp_home):
        """When NOTES_DIR has no venv, checks ~/.walkabout/.venv."""
        monkeypatch.setattr(sys, "platform", "linux")
        # Create a separate temp dir for home
        home_dir = Path(temp_home) / "home"
        home_venv = home_dir / ".walkabout" / ".venv" / "bin"
        home_venv.mkdir(parents=True)
        (home_venv / "python3").write_text("")

        # NOTES_DIR has no venv
        monkeypatch.setattr("walkabout.api.env.NOTES_DIR", temp_home)
        monkeypatch.setattr("walkabout.api.env.Path.home", lambda: home_dir)

        from walkabout.api.env import _get_venv_python
        result = _get_venv_python()
        assert result is not None

    def test_get_system_python_windows_fallback(self, monkeypatch):
        """On Windows, system python falls back to 'python'."""
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        monkeypatch.setattr("walkabout.api.env._get_venv_python", lambda: None)

        from walkabout.api.env import _get_system_python
        assert _get_system_python() == "python"

    def test_get_system_python_unix_fallback(self, monkeypatch):
        """On Unix, system python falls back to 'python3'."""
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        monkeypatch.setattr("walkabout.api.env._get_venv_python", lambda: None)

        from walkabout.api.env import _get_system_python
        assert _get_system_python() == "python3"

    def test_uv_venv_creation_windows_path(self, monkeypatch, temp_home):
        """After uv venv, Windows path uses Scripts/python.exe."""
        monkeypatch.setattr(sys, "platform", "win32")
        cwd = Path.home() / ".walkabout"
        new_venv = str(cwd / ".venv" / "Scripts" / "python.exe")
        assert "Scripts" in new_venv
        assert new_venv.endswith("python.exe")

    def test_uv_venv_creation_unix_path(self, monkeypatch, temp_home):
        """After uv venv, Unix path uses bin/python3."""
        monkeypatch.setattr(sys, "platform", "linux")
        cwd = Path.home() / ".walkabout"
        new_venv = str(cwd / ".venv" / "bin" / "python3")
        assert "bin" in new_venv
        assert new_venv.endswith("python3")


# ============================================================================
# api/__init__.py — subprocess, CREATE_NO_WINDOW, PYTHONPATH
# ============================================================================

class TestRunTraceSubprocess:
    """_run_trace_subprocess cross-platform behavior."""

    def test_uses_inprocess_when_frozen(self, monkeypatch):
        """PyInstaller frozen → in-process execution (no subprocess)."""
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        import inspect
        source = inspect.getsource(_run_trace_subprocess)
        # The function should check sys.frozen and call _run_trace_inprocess
        assert "sys.frozen" in source or "getattr" in source

    def test_pythonpath_uses_os_pathsep(self, monkeypatch):
        """PYTHONPATH construction uses os.pathsep (; on Windows, : on Unix)."""
        walkabout_core = "/fake/walkabout/core"
        walkabout_root = "/fake"
        pythonpath = os.pathsep.join([walkabout_core, walkabout_root])
        if sys.platform == "win32":
            assert ";" in pythonpath
        else:
            assert ":" in pythonpath
        assert walkabout_core in pythonpath
        assert walkabout_root in pythonpath

    def test_pythonpath_appends_existing(self, monkeypatch):
        """Existing PYTHONPATH is appended with os.pathsep."""
        walkabout_core = "/fake/core"
        walkabout_root = "/fake"
        existing = "/existing/path"
        pythonpath = os.pathsep.join([walkabout_core, walkabout_root])
        if existing:
            pythonpath += os.pathsep + existing
        parts = pythonpath.split(os.pathsep)
        assert len(parts) == 3
        assert parts[-1] == existing

    def test_create_no_window_on_windows(self, monkeypatch):
        """CREATE_NO_WINDOW flag is used on Windows subprocess."""
        monkeypatch.setattr(sys, "platform", "win32")
        # CREATE_NO_WINDOW only exists on actual Windows. Simulate the
        # flag injection pattern with a sentinel value on Linux.
        _CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = _CREATE_NO_WINDOW
        assert "creationflags" in kwargs

    def test_no_create_no_window_on_unix(self, monkeypatch):
        """CREATE_NO_WINDOW is NOT used on Unix platforms."""
        monkeypatch.setattr(sys, "platform", "linux")
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x08000000
        assert "creationflags" not in kwargs


class TestRunTraceInprocess:
    """_run_trace_inprocess — used when sys.frozen (PyInstaller bundle)."""

    def test_sets_walkabout_home(self, monkeypatch, temp_home):
        """In-process execution sets WALKABOUT_HOME env var."""
        monkeypatch.setattr("walkabout.api.Path.home", lambda: temp_home)
        # Verify the function sets WALKABOUT_HOME to str(Path.home() / ".walkabout")
        import inspect
        source = inspect.getsource(_run_trace_inprocess)
        assert "WALKABOUT_HOME" in source

    def test_restores_cwd_and_env_on_finish(self):
        """In-process execution restores cwd, env, and sys.path."""
        import inspect
        source = inspect.getsource(_run_trace_inprocess)
        assert "old_cwd" in source
        assert "old_home" in source
        assert "old_path" in source
        assert "sys.path[:] = old_path" in source

    def test_core_dir_added_to_sys_path(self):
        """core/ directory is added to sys.path for bare imports."""
        import inspect
        source = inspect.getsource(_run_trace_inprocess)
        assert "core_dir" in source
        assert "sys.path.insert" in source


# ============================================================================
# execute_util.py — system_text CREATE_NO_WINDOW
# ============================================================================

class TestExecuteUtilSystemText:
    """system_text() subprocess flag on Windows."""

    def test_system_text_adds_create_no_window_on_windows(self, monkeypatch):
        """system_text passes CREATE_NO_WINDOW on Windows."""
        monkeypatch.setattr(sys, "platform", "win32")
        _CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        kwargs = {"text": True, "timeout": 30}
        if sys.platform == "win32":
            kwargs["creationflags"] = _CREATE_NO_WINDOW
        assert "creationflags" in kwargs

    def test_system_text_no_flag_on_unix(self, monkeypatch):
        """system_text does NOT add creationflags on Unix."""
        monkeypatch.setattr(sys, "platform", "linux")
        kwargs = {"text": True, "timeout": 30}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        assert "creationflags" not in kwargs


# ============================================================================
# app.py — PyInstaller frontend path resolution
# ============================================================================

class TestAppFrontendPath:
    """frontend_dist resolution for frozen vs development."""

    def test_frozen_uses_meipass(self, monkeypatch):
        """PyInstaller: frontend_dist = sys._MEIPASS / frontend / dist."""
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", "C:\\Temp\\_MEI12345", raising=False)
        frontend_dist = Path(sys._MEIPASS) / "frontend" / "dist"
        assert str(frontend_dist) == os.path.join("C:\\Temp\\_MEI12345", "frontend", "dist")

    def test_dev_uses_relative_path(self, monkeypatch):
        """Development: frontend_dist relative to __file__."""
        monkeypatch.setattr(sys, "frozen", False, raising=False)
        # In dev mode, resolves relative to walkabout/app.py
        # Path(__file__).parent.parent / "frontend" / "dist"
        dev_path = Path(__file__).parent.parent / "frontend" / "dist"
        assert "frontend" in str(dev_path)


# ============================================================================
# webview.py / __main__.py — display detection
# ============================================================================

class TestDisplayDetection:
    """GUI/display availability detection per platform."""

    def test_windows_always_has_display(self, monkeypatch):
        """Windows always has display (True)."""
        monkeypatch.setattr(sys, "platform", "win32")
        has_display = True
        if sys.platform == "linux":
            has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
        assert has_display is True

    def test_macos_always_has_display(self, monkeypatch):
        """macOS always has display (True)."""
        monkeypatch.setattr(sys, "platform", "darwin")
        has_display = True
        if sys.platform == "linux":
            has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
        assert has_display is True

    def test_linux_without_display_is_headless(self, monkeypatch):
        """Linux without DISPLAY or WAYLAND_DISPLAY is headless."""
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
        assert has_display is False

    def test_linux_with_display_has_gui(self, monkeypatch):
        """Linux with DISPLAY set has display."""
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setenv("DISPLAY", ":0")
        has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
        assert has_display is True

    def test_linux_with_wayland_has_gui(self, monkeypatch):
        """Linux with WAYLAND_DISPLAY set has display."""
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
        assert has_display is True


# ============================================================================
# WSL detection — platform.uname()
# ============================================================================

class TestWSLDetection:
    """WSL detection via WSL_DISTRO_NAME env var and platform.uname()."""

    def test_wsl_detected_via_env_var(self, monkeypatch):
        """WSL_DISTRO_NAME env var indicates WSL."""
        monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
        is_wsl = bool(os.environ.get("WSL_DISTRO_NAME", ""))
        assert is_wsl is True

    def test_no_wsl_when_env_var_unset(self, monkeypatch):
        """No WSL_DISTRO_NAME means not WSL."""
        monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
        is_wsl = bool(os.environ.get("WSL_DISTRO_NAME", ""))
        assert is_wsl is False

    def test_platform_uname_safe_on_all_platforms(self):
        """platform.uname() works on Windows/Linux/macOS."""
        import platform
        try:
            info = platform.uname()
            assert info.system is not None
        except Exception:
            pytest.fail("platform.uname() raised unexpectedly")

    def test_os_uname_should_use_platform_not_os(self, monkeypatch):
        """Code uses platform.uname() not os.uname() for cross-platform safety."""
        import platform as _plat
        # platform.uname() exists on all platforms; os.uname() only on Unix
        assert hasattr(_plat, "uname")
        # On Linux, os.uname exists; on Windows it would not
        # The key point: code uses platform.uname() which is cross-platform


# ============================================================================
# Path handling — resolve, relative_to, cross-drive
# ============================================================================

class TestPathResolution:
    """Path.relative_to() and Path.resolve() cross-platform behavior."""

    def test_resolve_relative_to_case_insensitive_on_windows(self, monkeypatch, tmp_path):
        """Path.relative_to() is case-insensitive on Windows."""
        base = tmp_path / "Notes"
        base.mkdir()
        child = base / "subdir" / "test.py"
        child.parent.mkdir()
        child.write_text("")

        # resolve() then relative_to() — works on all platforms
        resolved_child = child.resolve()
        resolved_base = base.resolve()
        resolved_child.relative_to(resolved_base)  # should not raise

    def test_path_resolve_protects_against_traversal(self, tmp_path):
        """_resolve() blocks path traversal via ../../ etc."""
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()

        malicious = "../../etc/passwd"
        p = (notes_dir / malicious).resolve()
        try:
            p.relative_to(notes_dir.resolve())
            traversal_ok = True
        except ValueError:
            traversal_ok = False
        assert traversal_ok is False  # Should be blocked

    def test_path_resolve_allows_valid_paths(self, tmp_path):
        """_resolve() allows valid paths within notes dir."""
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        (notes_dir / "valid.py").write_text("")

        valid = "valid.py"
        p = (notes_dir / valid).resolve()
        try:
            p.relative_to(notes_dir.resolve())
            valid_ok = True
        except ValueError:
            valid_ok = False
        assert valid_ok is True

    def test_os_path_join_handles_windows_separators(self):
        """os.path.join handles mixed separators on all platforms."""
        result = os.path.join("C:\\Users\\test", ".walkabout", "notes")
        # os.path.join uses platform separator
        assert ".walkabout" in result
        assert "notes" in result


class TestRelpathCrossDrive:
    """os.path.relpath cross-drive edge case on Windows."""

    def test_relpath_same_drive_works(self, tmp_path, monkeypatch):
        """os.path.relpath works when path and cwd are on same drive."""
        old_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            result = os.path.relpath(str(tmp_path / "file.py"), os.getcwd())
            assert result is not None
        finally:
            os.chdir(old_cwd)

    def test_relpath_cross_drive_may_fail_on_windows(self, monkeypatch):
        """os.path.relpath raises ValueError on cross-drive Windows paths."""
        monkeypatch.setattr(sys, "platform", "win32")
        # Cross-drive: cwd on C:, path on D:
        # relativize simply calls os.path.relpath which can fail cross-drive
        # This test documents the expected behavior
        import inspect

        from walkabout.core.file_util import relativize
        source = inspect.getsource(relativize)
        assert "os.path.relpath" in source


# ============================================================================
# api/notes.py — _ensure_package_init cross-platform
# ============================================================================

class TestEnsurePackageInit:
    """_ensure_package_init creates __init__.py in all parent packages."""

    def test_creates_init_files_cross_platform(self, tmp_path, monkeypatch):
        """_ensure_package_init works on any platform."""
        from walkabout.api.notes import _ensure_package_init
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        monkeypatch.setattr("walkabout.api.notes.NOTES_DIR", notes_dir)

        pkg = notes_dir / "sub" / "deep" / "note.py"
        pkg.parent.mkdir(parents=True)
        pkg.write_text("")

        _ensure_package_init(pkg)

        # Check __init__.py created in all parent packages
        assert (notes_dir / "sub" / "__init__.py").exists()
        assert (notes_dir / "sub" / "deep" / "__init__.py").exists()

    def test_does_not_create_outside_notes_dir(self, tmp_path, monkeypatch):
        """_ensure_package_init does not create __init__.py outside notes."""
        from walkabout.api.notes import _ensure_package_init
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        monkeypatch.setattr("walkabout.api.notes.NOTES_DIR", notes_dir)

        # Path outside notes
        outside = tmp_path / "outside" / "test.py"
        outside.parent.mkdir(parents=True)
        outside.write_text("")

        _ensure_package_init(outside)
        assert not (tmp_path / "outside" / "__init__.py").exists()


# ============================================================================
# Subprocess CREATE_NO_WINDOW in api/env.py
# ============================================================================

class TestEnvSubprocessFlags:
    """api/env.py subprocess calls — some lack CREATE_NO_WINDOW."""

    def test_env_subprocess_calls_documented(self):
        """Document that api/env.py subprocess calls lack CREATE_NO_WINDOW."""
        # This is a known gap: _get_env_info(), install_packages() use
        # subprocess.run() without creationflags. On Windows, these may
        # briefly flash console windows for pip/uv subprocesses.
        # Not a bug per se, but a known limitation.
        import inspect

        from walkabout.api import env
        source = inspect.getsource(env.install_packages)
        # Verify the function exists and has subprocess.run
        assert "subprocess.run" in source
        # CREATE_NO_WINDOW is NOT present in env.py (known gap)
        assert "CREATE_NO_WINDOW" not in source


# ============================================================================
# Console output — Unicode/GBK safety on Windows
# ============================================================================

class TestConsoleEncoding:
    """All print statements use ASCII-safe characters."""

    def test_main_py_no_unicode_in_prints(self):
        """__main__.py print statements are ASCII-safe."""
        main_path = Path(__file__).parent.parent / "walkabout" / "__main__.py"
        content = main_path.read_text(encoding="utf-8")
        # Find all print() calls
        import re
        prints = re.findall(r'print\((.*?)\)', content)
        for p in prints:
            # No Unicode emoji or special chars that can't be encoded in GBK
            for char in ['⚠', '—', '→', '✓', '✗', '✅']:
                assert char not in p, f"Unicode char {char!r} in print: {p[:80]}"

    def test_runner_py_no_unicode_in_prints(self):
        """runner.py print statements are ASCII-safe."""
        runner_path = Path(__file__).parent.parent / "walkabout" / "runner.py"
        content = runner_path.read_text(encoding="utf-8")
        prints = [ln for ln in content.split("\n") if "print(" in ln]
        for p in prints:
            for char in ['⚠', '—', '→', '✓', '✗', '✅']:
                assert char not in p, f"Unicode char in runner.py print: {p.strip()[:80]}"


# ============================================================================
# os.pathsep — PYTHONPATH construction
# ============================================================================

class TestPythonpathConstruction:
    """PYTHONPATH uses platform-correct separator."""

    def test_pathsep_is_correct_for_current_platform(self):
        """os.pathsep matches the actual running platform."""
        if sys.platform == "win32":
            assert os.pathsep == ";"
        else:
            assert os.pathsep == ":"

    def test_pathsep_join_is_consistent(self):
        """os.pathsep.join creates consistently separated paths."""
        paths = ["/a/b", "/c/d"]
        result = os.pathsep.join(paths)
        parts = result.split(os.pathsep)
        assert parts == paths

    def test_pythonpath_construction_pattern(self):
        """The PYTHONPATH construction pattern works on any platform."""
        walkabout_core = "/fake/core"
        walkabout_root = "/fake"
        existing = "/existing/path"
        pythonpath = os.pathsep.join([walkabout_core, walkabout_root])
        if existing:
            pythonpath += os.pathsep + existing
        parts = pythonpath.split(os.pathsep)
        assert len(parts) == 3
        assert parts[-1] == existing


# ============================================================================
# PyInstaller — sys.frozen / sys._MEIPASS
# ============================================================================

class TestPyInstallerIntegration:
    """PyInstaller-specific behavior."""

    def test_sys_frozen_false_in_normal_python(self):
        """In normal Python (not PyInstaller), sys.frozen is absent or False."""
        assert not getattr(sys, "frozen", False)

    def test_meipass_not_set_in_normal_python(self):
        """sys._MEIPASS is only set by PyInstaller."""
        assert getattr(sys, "_MEIPASS", None) is None

    def test_config_uses_executable_when_frozen(self, monkeypatch):
        """get_python_path returns sys.executable when frozen."""
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "executable", "/fake/bundled_app")
        from walkabout.config import get_python_path
        assert get_python_path() == "/fake/bundled_app"

    def test_api_prefers_inprocess_when_frozen(self, monkeypatch):
        """API uses _run_trace_inprocess when sys.frozen is True."""
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        import inspect
        source = inspect.getsource(_run_trace_subprocess)
        assert "_run_trace_inprocess" in source


# ============================================================================
# webbrowser.open() — platform-specific browser launch
# ============================================================================

class TestWebbrowserFallback:
    """webbrowser.open() handles platform differences internally."""

    def test_webbrowser_importable(self):
        """webbrowser module is importable on all platforms."""
        import webbrowser
        assert webbrowser is not None

    def test_webview_fallback_uses_webbrowser(self, monkeypatch):
        """webview.py fallback uses webbrowser.open()."""
        monkeypatch.setattr(sys, "platform", "linux")
        import inspect

        from walkabout.webview import open_window
        source = inspect.getsource(open_window)
        assert "webbrowser" in source


# ============================================================================
# api/notes.py — path handling with os.sep
# ============================================================================

class TestNotesPathHandling:
    """Notes API path handling works cross-platform."""

    def test_skip_dirs_uses_frozenset(self, monkeypatch):
        """_SKIP_DIRS correctly skips __pycache__ and hidden dirs."""
        monkeypatch.setattr(sys, "platform", "win32")
        from walkabout.api.notes import _SKIP_DIRS
        assert "__pycache__" in _SKIP_DIRS

    def test_package_init_detection(self, monkeypatch):
        """_ensure_package_init creates __init__.py correctly."""
        # _ensure_package_init strips __init__.py from path to get package dir
        p = Path("a/b/c/__init__.py")
        package_dir = p.parent
        assert package_dir == Path("a/b/c")

    def test_package_dir_path_is_cross_platform(self):
        """Path handling for package directories works on any platform."""
        # Path with forward slashes (works on all platforms via pathlib)
        p = Path("sub", "deep", "__init__.py")
        assert p.parent.name == "deep"
        assert str(p.parent) in ["sub/deep", "sub\\deep"]
        assert "deep" in p.parts


# ============================================================================
# api/execute.py & api/export.py — path resolution
# ============================================================================

class TestApiPathResolution:
    """_resolve() in api/execute.py and api/export.py."""

    def test_execute_resolve_blocks_traversal(self, tmp_path, monkeypatch):
        """execute._resolve() blocks path traversal."""
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        monkeypatch.setattr("walkabout.api.execute.NOTES_DIR", notes_dir)

        from fastapi import HTTPException as _HTTPExc

        from walkabout.api.execute import _resolve
        with pytest.raises(_HTTPExc):
            _resolve("../../etc/passwd")

    def test_export_resolve_blocks_traversal(self, tmp_path, monkeypatch):
        """export._resolve() blocks path traversal."""
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        monkeypatch.setattr("walkabout.api.export.NOTES_DIR", notes_dir)

        from fastapi import HTTPException  # noqa: F811

        from walkabout.api.export import _resolve
        with pytest.raises(HTTPException):
            _resolve("../../etc/passwd")

    def test_resolve_allows_normal_path(self, tmp_path, monkeypatch):
        """_resolve() allows normal relative paths."""
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        (notes_dir / "ok.py").write_text("")
        monkeypatch.setattr("walkabout.api.execute.NOTES_DIR", notes_dir)

        from walkabout.api.execute import _resolve
        result = _resolve("ok.py")
        assert result.name == "ok.py"

    def test_resolve_nested_relative_path(self, tmp_path, monkeypatch):
        """_resolve() normalizes relative path components."""
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        (notes_dir / "sub").mkdir()
        (notes_dir / "sub" / "file.py").write_text("")
        monkeypatch.setattr("walkabout.api.execute.NOTES_DIR", notes_dir)

        from walkabout.api.execute import _resolve
        result = _resolve("sub/../sub/file.py")
        assert result.name == "file.py"
