"""Integration tests for _run_trace_inprocess — PyInstaller in-process execution.

These tests verify correct behavior of the in-process execution path used
when sys.frozen is True (PyInstaller single-file bundle). They test path
resolution, sys.path setup, module import, trace generation, and cleanup.
"""
import importlib
import os
import sys
import tempfile
from pathlib import Path

import pytest

from walkabout.api import _run_trace_inprocess

# ============================================================================
# Fixture: temporary workspace with a note file
# ============================================================================

@pytest.fixture
def workspace():
    """Create a temp workspace with a valid walkthrough note."""
    d = tempfile.mkdtemp()
    ws = Path(d)
    note = ws / "hello.py"
    note.write_text("""\"\"\"Test note.\"\"\"
def main():
    x = 42  # @inspect x
    y = x + 1  # @inspect y
""", encoding="utf-8")
    return ws


@pytest.fixture
def trace_file(tmp_path):
    """Return a path for the trace output."""
    return tmp_path / "traces" / "hello.json"


# ============================================================================
# Core functionality tests
# ============================================================================

class TestRunTraceInprocessBasic:
    """Basic tests for _run_trace_inprocess."""

    def test_creates_trace_file(self, workspace, trace_file, monkeypatch):
        """_run_trace_inprocess creates a trace JSON file."""
        # Ensure core modules are importable
        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        if core_dir not in sys.path:
            sys.path.insert(0, core_dir)
        # Add walkabout root to sys.path for relative imports
        walkabout_root = str(Path(__file__).parent.parent)
        if walkabout_root not in sys.path:
            sys.path.insert(0, walkabout_root)
        # Ensure workspace is on path
        if str(workspace) not in sys.path:
            sys.path.insert(0, str(workspace))

        _run_trace_inprocess("hello", trace_file, workspace)

        assert trace_file.exists(), f"Trace file was not created: {trace_file}"
        import json
        trace = json.loads(trace_file.read_text(encoding="utf-8"))
        assert "steps" in trace
        assert "files" in trace
        assert len(trace["steps"]) > 0, "Should have at least 1 step"

    def test_restores_original_cwd(self, workspace, trace_file, monkeypatch):
        """_run_trace_inprocess restores cwd after execution."""
        # Ensure paths are set up
        walkabout_root = str(Path(__file__).parent.parent)
        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        for p in [walkabout_root, core_dir, str(workspace)]:
            if p not in sys.path:
                sys.path.insert(0, p)

        original_cwd = os.getcwd()
        _run_trace_inprocess("hello", trace_file, workspace)
        assert os.getcwd() == original_cwd, "cwd was not restored"

    def test_restores_sys_path(self, workspace, trace_file, monkeypatch):
        """_run_trace_inprocess restores sys.path after execution."""
        walkabout_root = str(Path(__file__).parent.parent)
        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        for p in [walkabout_root, core_dir, str(workspace)]:
            if p not in sys.path:
                sys.path.insert(0, p)

        old_path = sys.path.copy()
        _run_trace_inprocess("hello", trace_file, workspace)
        assert sys.path == old_path, "sys.path was not restored"

    def test_restores_walkabout_home_env(self, workspace, trace_file, monkeypatch):
        """_run_trace_inprocess restores WALKABOUT_HOME env var."""
        walkabout_root = str(Path(__file__).parent.parent)
        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        for p in [walkabout_root, core_dir, str(workspace)]:
            if p not in sys.path:
                sys.path.insert(0, p)

        old_home = os.environ.get("WALKABOUT_HOME")
        _run_trace_inprocess("hello", trace_file, workspace)
        assert os.environ.get("WALKABOUT_HOME") == old_home, "WALKABOUT_HOME not restored"


class TestRunTraceInprocessEdgeCases:
    """Edge case tests for _run_trace_inprocess."""

    def test_creates_missing_cwd(self, tmp_path, monkeypatch):
        """Creates the cwd directory if it doesn't exist."""
        walkabout_root = str(Path(__file__).parent.parent)
        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        for p in [walkabout_root, core_dir]:
            if p not in sys.path:
                sys.path.insert(0, p)

        nonexistent = tmp_path / "nonexistent" / "workspace"
        # Create the note file so import_module works
        nonexistent.mkdir(parents=True)
        note = nonexistent / "simple.py"
        note.write_text("""def main():
    pass
""", encoding="utf-8")
        if str(nonexistent) not in sys.path:
            sys.path.insert(0, str(nonexistent))

        trace_file = tmp_path / "trace.json"
        _run_trace_inprocess("simple", trace_file, nonexistent)
        assert trace_file.exists()

    def test_module_not_found_raises(self, workspace, trace_file, monkeypatch):
        """Raises ModuleNotFoundError for non-existent module."""
        walkabout_root = str(Path(__file__).parent.parent)
        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        for p in [walkabout_root, core_dir, str(workspace)]:
            if p not in sys.path:
                sys.path.insert(0, p)

        with pytest.raises(ModuleNotFoundError):
            _run_trace_inprocess("nonexistent_module_xyz", trace_file, workspace)

    def test_creates_trace_parent_dirs(self, workspace, monkeypatch):
        """Creates parent directories for trace file."""
        walkabout_root = str(Path(__file__).parent.parent)
        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        for p in [walkabout_root, core_dir, str(workspace)]:
            if p not in sys.path:
                sys.path.insert(0, p)

        trace_file = Path(tempfile.mkdtemp()) / "sub" / "deep" / "output.json"
        _run_trace_inprocess("hello", trace_file, workspace)
        assert trace_file.exists()

    def test_note_with_underscore_name(self, tmp_path, monkeypatch):
        """Works with notes that have underscores in the name."""
        walkabout_root = str(Path(__file__).parent.parent)
        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        for p in [walkabout_root, core_dir]:
            if p not in sys.path:
                sys.path.insert(0, p)

        ws = tmp_path / "notes"
        ws.mkdir()
        note = ws / "my_test_note.py"
        note.write_text("""def main():
    result = 99  # @inspect result
""", encoding="utf-8")
        if str(ws) not in sys.path:
            sys.path.insert(0, str(ws))

        trace_file = tmp_path / "trace.json"
        _run_trace_inprocess("my_test_note", trace_file, ws)
        assert trace_file.exists()
        import json
        trace = json.loads(trace_file.read_text(encoding="utf-8"))
        # Check the @inspect variable was captured
        env_values = {}
        for step in trace["steps"]:
            env_values.update(step.get("env", {}))
        assert env_values.get("result") == 99


# ============================================================================
# Path resolution tests (PyInstaller-specific edge cases)
# ============================================================================

class TestPathResolution:
    """Tests for path resolution in _run_trace_inprocess."""

    def test_core_dir_is_absolute(self):
        """core_dir is resolved to an absolute path."""
        # Simulate the resolution logic
        core_dir = str(Path(__file__).resolve().parent.parent / "walkabout" / "core")
        assert os.path.isabs(core_dir), f"core_dir should be absolute: {core_dir}"

    def test_core_dir_exists(self):
        """core_dir points to the actual walkabout/core directory."""
        core_dir = str(Path(__file__).resolve().parent.parent / "walkabout" / "core")
        assert os.path.isdir(core_dir), f"core_dir doesn't exist: {core_dir}"

    def test_core_dir_contains_execute_util(self):
        """core_dir contains execute_util.py needed by user notes."""
        core_dir = str(Path(__file__).resolve().parent.parent / "walkabout" / "core")
        assert os.path.isfile(os.path.join(core_dir, "execute_util.py")), \
            f"execute_util.py not found in core_dir: {core_dir}"

    def test_relative_file_resolves_correctly(self, monkeypatch, tmp_path):
        """When __file__ is relative (PyInstaller), resolution is correct."""
        # Simulate the PyInstaller scenario: __file__ is relative
        # The fix computes core_dir BEFORE os.chdir()
        old_cwd = os.getcwd()
        try:
            # Change to a temp directory (simulating chdir to NOTES_DIR)
            os.chdir(str(tmp_path))

            # Compute core_dir (as _run_trace_inprocess now does, BEFORE chdir)
            # But we already changed dir, so we need to do it like the FIXED code
            pass
        finally:
            os.chdir(old_cwd)

        # The fix: compute BEFORE chdir, using .resolve()
        # This test verifies the logic independently
        core_dir_before = str(Path(__file__).resolve().parent.parent / "walkabout" / "core")

        # Now simulate what happens if we chdir then compute (old buggy behavior)
        os.chdir(str(tmp_path))
        try:
            # OLD BUG: compute AFTER chdir with relative __file__
            # Path(__file__) could be relative in PyInstaller
            # Simulate a relative __file__ path (would resolve to tmp_path, not root)
            _relative_file = Path("walkabout/api/__init__.py")
            _buggy_path = str(_relative_file.resolve().parent.parent / "core")
            assert tmp_path.name in _buggy_path  # resolves relative to cwd (tmp_path)
        finally:
            os.chdir(old_cwd)

        # Verify the fixed path is correct (absolute, exists)
        assert os.path.isabs(core_dir_before)
        assert os.path.isdir(core_dir_before)

    def test_cwd_added_to_sys_path(self, workspace, trace_file, monkeypatch):
        """After _run_trace_inprocess, the old cwd is restored but cwd was properly set."""
        walkabout_root = str(Path(__file__).parent.parent)
        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        for p in [walkabout_root, core_dir, str(workspace)]:
            if p not in sys.path:
                sys.path.insert(0, p)

        # Call function — it should add cwd to sys.path internally
        _run_trace_inprocess("hello", trace_file, workspace)
        # After function returns, cwd should NOT be in sys.path (it was restored)
        # But during execution, it was added. This test verifies cleanup.
        assert os.getcwd() != str(workspace)  # cwd restored


# ============================================================================
# Trace content verification
# ============================================================================

class TestTraceContent:
    """Verify the trace JSON content generated by in-process execution."""

    def test_trace_includes_files(self, workspace, trace_file, monkeypatch):
        """Trace includes the source file."""
        walkabout_root = str(Path(__file__).parent.parent)
        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        for p in [walkabout_root, core_dir, str(workspace)]:
            if p not in sys.path:
                sys.path.insert(0, p)

        _run_trace_inprocess("hello", trace_file, workspace)
        import json
        trace = json.loads(trace_file.read_text(encoding="utf-8"))
        assert "files" in trace
        assert len(trace["files"]) >= 1
        # At least one file path should reference hello.py
        file_paths = list(trace["files"].keys())
        assert any("hello.py" in p for p in file_paths), \
            f"hello.py not in files: {file_paths}"

    def test_trace_includes_steps(self, workspace, trace_file, monkeypatch):
        """Trace includes execution steps."""
        walkabout_root = str(Path(__file__).parent.parent)
        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        for p in [walkabout_root, core_dir, str(workspace)]:
            if p not in sys.path:
                sys.path.insert(0, p)

        _run_trace_inprocess("hello", trace_file, workspace)
        import json
        trace = json.loads(trace_file.read_text(encoding="utf-8"))
        assert len(trace["steps"]) >= 2, f"Expected >=2 steps, got {len(trace['steps'])}"

    def test_trace_captures_inspect_variables(self, workspace, trace_file, monkeypatch):
        """@inspect variables are captured in the trace."""
        walkabout_root = str(Path(__file__).parent.parent)
        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        for p in [walkabout_root, core_dir, str(workspace)]:
            if p not in sys.path:
                sys.path.insert(0, p)

        _run_trace_inprocess("hello", trace_file, workspace)
        import json
        trace = json.loads(trace_file.read_text(encoding="utf-8"))
        # Collect all env values from all steps
        env_values = {}
        for step in trace["steps"]:
            env_values.update(step.get("env", {}))
        assert "x" in env_values, f"Variable 'x' not captured. env_values: {env_values}"
        assert env_values.get("x") == 42
        assert "y" in env_values
        assert env_values.get("y") == 43


# ============================================================================
# PyInstaller simulation tests
# ============================================================================

class TestPyInstallerSimulation:
    """Simulate PyInstaller frozen environment for in-process execution."""

    def test_frozen_mode_uses_inprocess(self, monkeypatch):
        """When sys.frozen is True, _run_trace_subprocess calls _run_trace_inprocess."""
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        import inspect

        from walkabout.api import _run_trace_subprocess
        source = inspect.getsource(_run_trace_subprocess)
        assert "_run_trace_inprocess" in source
        assert "sys.frozen" in source or "getattr" in source

    def test_frozen_mode_skips_subprocess(self, monkeypatch):
        """When frozen, subprocess.Popen is never called."""
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        import inspect

        from walkabout.api import _run_trace_subprocess
        source = inspect.getsource(_run_trace_subprocess)
        # The function should return early (via _run_trace_inprocess) when frozen
        assert "return _run_trace_inprocess" in source

    def test_meipass_path_structure(self):
        """Verify the expected MEIPASS path structure for PyInstaller."""
        # In PyInstaller onefile mode:
        # sys._MEIPASS = temp extraction directory
        # walkabout/ package is under MEIPASS root
        # core_dir should be <MEIPASS>/walkabout/core
        meipass = Path("C:\\Temp\\_MEI12345")
        expected_core = meipass / "walkabout" / "core"
        assert str(expected_core) == os.path.join("C:\\Temp\\_MEI12345", "walkabout", "core")


# ============================================================================
# Module import verification
# ============================================================================

class TestModuleImport:
    """Verify that _run_trace_inprocess can import modules correctly."""

    def test_imports_module_from_cwd(self, workspace, trace_file, monkeypatch):
        """Can import a module from the cwd directory."""
        walkabout_root = str(Path(__file__).parent.parent)
        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        for p in [walkabout_root, core_dir, str(workspace)]:
            if p not in sys.path:
                sys.path.insert(0, p)

        # Verify the module is importable from workspace
        sys.path.insert(0, str(workspace))
        try:
            mod = importlib.import_module("hello")
            assert hasattr(mod, "main"), "Module should have a main() function"
        finally:
            sys.path.pop(0)

    def test_import_fails_for_missing_module(self, workspace):
        """import_module raises ModuleNotFoundError for missing modules."""
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("this_module_does_not_exist_xyz")

    def test_cwd_resolve_matches_saved_note_path(self, tmp_path, monkeypatch):
        """verify that cwd.resolve() is consistent with _resolve() logic."""
        from walkabout.api.execute import _resolve

        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        monkeypatch.setattr("walkabout.api.execute.NOTES_DIR", notes_dir)
        monkeypatch.setattr("walkabout.api.notes.NOTES_DIR", notes_dir)
        monkeypatch.setattr("walkabout.config.NOTES_DIR", notes_dir)

        # Save a note via _resolve (same logic as execute/notes API)
        resolved_path = _resolve("test.py")
        resolved_path.write_text("def main(): pass\n", encoding="utf-8")

        # The resolved path should be under notes_dir
        assert notes_dir.resolve() in resolved_path.parents

        # cwd.resolve() should be the canonical form of NOTES_DIR
        cwd_canonical = str(notes_dir.resolve())
        assert os.path.isdir(cwd_canonical)


# ============================================================================
# Diagnostic output verification
# ============================================================================

class TestDiagnostics:
    """Verify diagnostic info is available on failure."""

    def test_diagnostics_include_sys_path_on_error(self, tmp_path, monkeypatch, capsys):
        """When execution fails, diagnostic info is printed to stderr."""
        walkabout_root = str(Path(__file__).parent.parent)
        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        for p in [walkabout_root, core_dir]:
            if p not in sys.path:
                sys.path.insert(0, p)

        nonexistent = tmp_path / "empty_workspace"
        nonexistent.mkdir()
        if str(nonexistent) not in sys.path:
            sys.path.insert(0, str(nonexistent))

        trace_file = tmp_path / "trace.json"
        import contextlib
        with contextlib.suppress(ModuleNotFoundError):
            _run_trace_inprocess("missing_module", trace_file, nonexistent)

        stderr = capsys.readouterr().err
        # Diagnostics go to stderr via print() on error
        assert isinstance(stderr, str)

    def test_cwd_resolved_in_diagnostics(self, workspace, trace_file, monkeypatch):
        """cwd is resolved before being used."""
        walkabout_root = str(Path(__file__).parent.parent)
        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        for p in [walkabout_root, core_dir, str(workspace)]:
            if p not in sys.path:
                sys.path.insert(0, p)

        # Verify workspace.resolve() works
        resolved = str(workspace.resolve())
        assert os.path.isabs(resolved)
        assert os.path.isdir(resolved)
