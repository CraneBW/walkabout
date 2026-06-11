"""Integration tests for plugin system end-to-end.

Tests verify in-process execution with plugins, hook chaining,
None passthrough, and error resilience.
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

from walkabout.api import _run_trace_inprocess
from walkabout.plugins.base import WalkaboutPlugin
from walkabout.plugins.manager import PluginManager


# ============================================================================
# In-process execution with plugins
# ============================================================================


class TestInprocessExecuteWithPlugins:
    """Tests for _run_trace_inprocess plugin discovery and hook firing."""

    def test_inprocess_execute_with_plugins(self, temp_home, monkeypatch):
        """_run_trace_inprocess discovers plugins and on_pre/post_execute hooks fire."""
        # Create a plugin in the temp plugins dir
        plugins_dir = temp_home / "plugins"
        plugin_pkg = plugins_dir / "inprocess_plugin"
        plugin_pkg.mkdir(parents=True, exist_ok=True)
        (plugin_pkg / "__init__.py").write_text(
            """
import os
from walkabout.plugins.base import WalkaboutPlugin

class InprocessPlugin(WalkaboutPlugin):
    name = "inprocess_test"

    def on_pre_execute(self, module_name, code):
        os.environ["_TEST_PRE_EXECUTED"] = module_name
        return code  # No code modification — verification via env var

    def on_post_execute(self, module_name, trace):
        os.environ["_TEST_POST_EXECUTED"] = module_name
        # Modify the trace in a way that persists through _dict_to_trace:
        # the 'files' dict is passed through (extra keys in trace dict are
        # dropped by _dict_to_trace, but 'files' and 'steps' are preserved).
        trace["files"]["plugin_marker.txt"] = "post_executed"
        return trace
""",
            encoding="utf-8",
        )

        # Create workspace with a walkthrough note
        workspace = Path(tempfile.mkdtemp())
        note = workspace / "ip_note.py"
        note.write_text(
            '''"""Test inprocess plugins."""
def main():
    x = 42  # @inspect x
''',
            encoding="utf-8",
        )

        # Ensure the project root is on sys.path so walkabout package is importable
        project_root = Path(__file__).parent.parent
        walkabout_root = str(project_root)
        core_dir = str(project_root / "walkabout" / "core")
        for p in [walkabout_root, core_dir]:
            if p not in sys.path:
                sys.path.insert(0, p)

        trace_file = Path(tempfile.mkdtemp()) / "trace.json"

        # Clean up env vars before test
        os.environ.pop("_TEST_PRE_EXECUTED", None)
        os.environ.pop("_TEST_POST_EXECUTED", None)

        try:
            _run_trace_inprocess("ip_note", trace_file, workspace)

            # --- Assert trace file exists and is valid ---
            assert trace_file.exists()
            import json

            trace = json.loads(trace_file.read_text(encoding="utf-8"))
            assert "steps" in trace
            assert "files" in trace
            assert len(trace["steps"]) > 0

            # --- Verify on_pre_execute fired (set env var) ---
            assert os.environ.get("_TEST_PRE_EXECUTED") == "ip_note", (
                "on_pre_execute should have set _TEST_PRE_EXECUTED env var"
            )

            # --- Verify on_post_execute fired ---
            # on_post_execute added a file to the trace dict (which persists)
            assert "plugin_marker.txt" in trace.get("files", {}), (
                "on_post_execute should have added plugin_marker.txt to files. "
                f"Got files: {list(trace.get('files', {}).keys())}"
            )
            assert os.environ.get("_TEST_POST_EXECUTED") == "ip_note", (
                "on_post_execute should have set _TEST_POST_EXECUTED env var"
            )
        finally:
            os.environ.pop("_TEST_PRE_EXECUTED", None)
            os.environ.pop("_TEST_POST_EXECUTED", None)
            # Clean up temp dirs
            import shutil

            shutil.rmtree(str(workspace), ignore_errors=True)


# ============================================================================
# Plugin hook chaining
# ============================================================================


class TestPluginHookChaining:
    """Tests for chaining behaviour of multiple plugin hooks."""

    def test_multiple_plugins_pre_execute_chain(self):
        """Multiple on_pre_execute hooks chain: plugin2 receives plugin1's output."""
        class P1Plugin(WalkaboutPlugin):
            name = "p1"

            def on_pre_execute(self, module_name, code):
                return code.replace("x", "y")

        class P2Plugin(WalkaboutPlugin):
            name = "p2"

            def on_pre_execute(self, module_name, code):
                self.received_code = code
                return code.replace("y", "z")

        p1 = P1Plugin()
        p2 = P2Plugin()
        pm = PluginManager()
        pm.plugins = [p1, p2]

        result = pm.on_pre_execute("test_mod", "x code")

        # Plugin2 should have received Plugin1's modified code
        assert p2.received_code == "y code", (
            f"Plugin2 should receive Plugin1's output 'y code', got {p2.received_code!r}"
        )
        # Final result should have both transformations applied
        assert result == "z code", f"Expected 'z code', got {result!r}"

    def test_multiple_plugins_post_execute_chain(self):
        """Multiple on_post_execute hooks chain: plugin2 sees plugin1's modifications."""
        class P1Plugin(WalkaboutPlugin):
            name = "p1"

            def on_post_execute(self, module_name, trace):
                trace["step1"] = "from_p1"
                return trace

        class P2Plugin(WalkaboutPlugin):
            name = "p2"

            def on_post_execute(self, module_name, trace):
                trace["chained"] = trace.get("step1") == "from_p1"
                trace["step2"] = True
                return trace

        p1 = P1Plugin()
        p2 = P2Plugin()
        pm = PluginManager()
        pm.plugins = [p1, p2]

        result = pm.on_post_execute("test_mod", {"steps": []})

        assert result.get("step1") == "from_p1", "Plugin1 should have set step1"
        assert result.get("step2") is True, "Plugin2 should have set step2"
        assert result.get("chained") is True, (
            "Plugin2 should see Plugin1's modification (chained behaviour)"
        )

    def test_plugin_on_pre_execute_returns_none_passthrough(self):
        """When a plugin returns None from on_pre_execute, original code passes through."""
        class NonePlugin(WalkaboutPlugin):
            name = "none_ret"

            def on_pre_execute(self, module_name, code):
                return None  # Explicit None — should not modify code

        class ModifyPlugin(WalkaboutPlugin):
            name = "modifier"

            def on_pre_execute(self, module_name, code):
                self.received_code = code
                return code.replace("original", "modified")

        none_p = NonePlugin()
        mod_p = ModifyPlugin()
        pm = PluginManager()
        pm.plugins = [none_p, mod_p]

        result = pm.on_pre_execute("test_mod", "original code")

        # ModifyPlugin should have received the ORIGINAL code (unchanged by NonePlugin)
        assert mod_p.received_code == "original code", (
            f"ModifyPlugin should receive original code, got {mod_p.received_code!r}"
        )
        assert "modified" in result
        assert "original" not in result

    def test_plugin_error_in_hook_does_not_crash_pipeline(self):
        """If one plugin raises in on_pre_execute, PluginManager catches it and continues."""
        class CrashingPlugin(WalkaboutPlugin):
            name = "crash"

            def on_pre_execute(self, module_name, code):
                raise RuntimeError("Boom!")

        class GoodPlugin(WalkaboutPlugin):
            name = "good"

            def on_pre_execute(self, module_name, code):
                return code.replace("original", "modified")

        pm = PluginManager()
        pm.plugins = [CrashingPlugin(), GoodPlugin()]

        result = pm.on_pre_execute("test_mod", "original code")

        # GoodPlugin should still have run and modified the code
        assert "modified" in result, (
            f"GoodPlugin should have modified code even though CrashingPlugin raised. "
            f"Got: {result!r}"
        )

    def test_plugin_error_in_post_execute_does_not_crash_pipeline(self):
        """If one plugin raises in on_post_execute, PluginManager catches it and continues."""
        class CrashingPlugin(WalkaboutPlugin):
            name = "crash_post"

            def on_post_execute(self, module_name, trace):
                raise RuntimeError("Post boom!")

        class GoodPlugin(WalkaboutPlugin):
            name = "good_post"

            def on_post_execute(self, module_name, trace):
                trace["good_ran"] = True
                return trace

        pm = PluginManager()
        pm.plugins = [CrashingPlugin(), GoodPlugin()]

        result = pm.on_post_execute("test_mod", {"steps": []})

        assert result.get("good_ran") is True, (
            "GoodPlugin should have run even though CrashingPlugin raised"
        )
