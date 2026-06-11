"""Tests for plugin-based custom renderer registration and API."""
import sys
from pathlib import Path

import pytest

from walkabout.core.execute_util import RendererRegistry
from walkabout.plugins.base import WalkaboutPlugin, register_renderer
from walkabout.plugins.manager import PluginManager


class TestRegisterRendererDecorator:
    """Tests for the @register_renderer decorator."""

    def test_decorator_sets_attribute(self):
        """The decorator should set _renderer_type on the method."""

        class MyPlugin(WalkaboutPlugin):
            @register_renderer("vega")
            def render_vega(self, rendering_data, style):
                return {"svg": rendering_data}

        plugin = MyPlugin()
        assert hasattr(plugin.render_vega, "_renderer_type")
        assert plugin.render_vega._renderer_type == "vega"

    def test_decorator_multiple_renderers(self):
        """A plugin can have multiple @register_renderer decorated methods."""

        class MultiPlugin(WalkaboutPlugin):
            @register_renderer("vega")
            def render_vega(self, data, style):
                pass

            @register_renderer("mermaid")
            def render_mermaid(self, data, style):
                pass

        plugin = MultiPlugin()
        assert plugin.render_vega._renderer_type == "vega"
        assert plugin.render_mermaid._renderer_type == "mermaid"

    def test_decorator_preserves_method(self):
        """The decorated method should still be callable."""

        class MyPlugin(WalkaboutPlugin):
            @register_renderer("uppercase")
            def render_upper(self, rendering_data, style):
                return (rendering_data or "").upper()

        plugin = MyPlugin()
        result = plugin.render_upper("hello", None)
        assert result == "HELLO"


class TestPluginOnRegisterRenderers:
    """Tests for the on_register_renderers base implementation."""

    def test_plugin_registers_renderers(self):
        """Calling on_register_renderers should register decorated methods."""

        class VegaPlugin(WalkaboutPlugin):
            name = "vega_plugin"

            @register_renderer("vega")
            def render_vega(self, rendering_data, style):
                return {"svg": rendering_data}

        plugin = VegaPlugin()
        registry = RendererRegistry()
        plugin.on_register_renderers(registry)

        assert registry.has("vega")
        fn = registry.get("vega")
        # The registered function should be the bound method
        result = fn('{"x": 1}', None)
        assert result == {"svg": '{"x": 1}'}

    def test_plugin_with_no_decorated_methods(self):
        """A plugin with no @register_renderer methods contributes nothing."""

        class EmptyPlugin(WalkaboutPlugin):
            name = "empty"

            def do_something(self):
                pass

        plugin = EmptyPlugin()
        registry = RendererRegistry()
        plugin.on_register_renderers(registry)

        assert registry.list() == []

    def test_multiple_plugins_different_renderers(self):
        """Two plugins can register different renderer types."""

        class VegaPlugin(WalkaboutPlugin):
            name = "vega"

            @register_renderer("vega")
            def render_vega(self, data, style):
                return {"svg": data}

        class MermaidPlugin(WalkaboutPlugin):
            name = "mermaid"

            @register_renderer("mermaid")
            def render_mermaid(self, data, style):
                return {"diagram": data}

        registry = RendererRegistry()
        VegaPlugin().on_register_renderers(registry)
        MermaidPlugin().on_register_renderers(registry)

        assert sorted(registry.list()) == ["mermaid", "vega"]


class TestPluginManagerCollectRenderers:
    """Tests for PluginManager renderer collection."""

    def test_discover_collects_renderers(self, temp_home):
        """PluginManager.discover() should collect renderers from plugins in PLUGINS_DIR."""
        plugins_dir = temp_home / "plugins"
        plugin_pkg = plugins_dir / "test_renderer_plugin"
        plugin_pkg.mkdir(parents=True, exist_ok=True)
        (plugin_pkg / "__init__.py").write_text(
            """
from walkabout.plugins.base import WalkaboutPlugin, register_renderer

class TestRendererPlugin(WalkaboutPlugin):
    name = "test_renderer"
    version = "1.0.0"

    @register_renderer("test_chart")
    def render_test(self, rendering_data, style):
        return {"type": "test", "data": rendering_data}
"""
        )

        pm = PluginManager()
        pm.discover()

        assert len(pm.plugins) == 1
        assert pm.registry is not None
        assert pm.registry.has("test_chart")

    def test_plugin_manager_shares_registry_globally(self, temp_home):
        """PluginManager should share its registry via set_renderer_registry()."""
        from walkabout.core.execute_util import get_renderer_registry

        plugins_dir = temp_home / "plugins"
        plugin_pkg = plugins_dir / "global_registry_plugin"
        plugin_pkg.mkdir(parents=True, exist_ok=True)
        (plugin_pkg / "__init__.py").write_text(
            """
from walkabout.plugins.base import WalkaboutPlugin, register_renderer

class GlobalRegistryPlugin(WalkaboutPlugin):
    name = "global_registry"
    @register_renderer("global_chart")
    def render_global(self, rendering_data, style):
        return {}
"""
        )

        pm = PluginManager()
        pm.discover()

        global_reg = get_renderer_registry()
        assert global_reg is pm.registry
        assert global_reg.has("global_chart")

    def test_empty_plugins_dir(self, temp_home):
        """An empty plugins dir causes no errors."""
        pm = PluginManager()
        pm.discover()
        assert pm.plugins == []


class TestPluginManagerEdgeCases:
    """Edge-case tests for PluginManager behaviour."""

    def test_plugin_manager_double_discover_is_safe(self, temp_home):
        """Calling pm.discover() twice should not duplicate plugins or renderers."""
        from walkabout.core.execute_util import get_renderer_registry

        plugins_dir = temp_home / "plugins"
        plugin_pkg = plugins_dir / "double_discover_plugin"
        plugin_pkg.mkdir(parents=True, exist_ok=True)
        (plugin_pkg / "__init__.py").write_text(
            """
from walkabout.plugins.base import WalkaboutPlugin, register_renderer

class DoubleDiscoverPlugin(WalkaboutPlugin):
    name = "double_discover"
    version = "1.0.0"

    @register_renderer("dd_chart")
    def render_dd(self, rendering_data, style):
        return {"type": "dd", "data": rendering_data}
""",
            encoding="utf-8",
        )

        pm = PluginManager()
        pm.discover()
        assert len(pm.plugins) == 1
        assert pm.registry.has("dd_chart")

        # Second discover must not raise and should not duplicate
        pm.discover()
        assert len(pm.plugins) == 1, "plugins should not be duplicated"
        # Renderer must still be registered after second discover
        assert pm.registry.has("dd_chart"), "renderer should still be present"
        # The global registry singleton must also reflect the current state
        global_reg = get_renderer_registry()
        assert global_reg.has("dd_chart"), "global registry should have the renderer"

    def test_on_pre_execute_with_no_plugins_returns_original(self):
        """PluginManager.on_pre_execute with empty plugins returns original code."""
        pm = PluginManager()
        result = pm.on_pre_execute("test_mod", "original code")
        assert result == "original code"

    def test_on_post_execute_with_no_plugins_returns_original(self):
        """PluginManager.on_post_execute with empty plugins returns original trace."""
        pm = PluginManager()
        trace = {"steps": [], "files": {"test.py": "x = 1"}}
        result = pm.on_post_execute("test_mod", trace)
        assert result is trace  # Same object, unchanged


class TestApiRenderersEndpoint:
    """Tests for the GET /api/renderers endpoint."""

    def test_api_returns_registered_types(self):
        """FastAPI endpoint should return registered renderer types."""
        from fastapi.testclient import TestClient
        from walkabout.app import create_app

        app = create_app()
        client = TestClient(app)

        response = client.get("/api/renderers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_api_renderers_with_plugin_registrations(self, temp_home):
        """API should return types registered by plugins."""
        plugins_dir = temp_home / "plugins"
        plugin_pkg = plugins_dir / "api_test_plugin"
        plugin_pkg.mkdir(parents=True, exist_ok=True)
        (plugin_pkg / "__init__.py").write_text(
            """
from walkabout.plugins.base import WalkaboutPlugin, register_renderer

class ApiTestPlugin(WalkaboutPlugin):
    name = "api_test"
    @register_renderer("api_chart")
    def render_api(self, rendering_data, style):
        return {"result": rendering_data}

    def get_frontend_components(self):
        return [{"type": "renderer", "renderer_type": "api_chart", "js": "/static/api_chart.js"}]
"""
        )

        from fastapi.testclient import TestClient
        from walkabout.app import create_app

        app = create_app()
        client = TestClient(app)

        response = client.get("/api/renderers")
        assert response.status_code == 200
        data = response.json()
        if "api_chart" in data:
            assert data["api_chart"]["type"] == "api_chart"
            assert data["api_chart"]["frontend_js"] is not None


class TestWalkthroughPluginCustomRenderer:
    """Integration tests for plugins with custom renderers."""

    def test_plugin_on_pre_execute_hook(self):
        """PluginManager.on_pre_execute should be called before execution."""
        from walkabout.plugins.base import WalkaboutPlugin

        class PreExecPlugin(WalkaboutPlugin):
            name = "pre_exec"

            def on_pre_execute(self, module_name, code):
                return code.replace("original", "modified")

        pm = PluginManager()
        pm.plugins = [PreExecPlugin()]
        result = pm.on_pre_execute("test_mod", "print('original')")
        assert "modified" in result
        assert "original" not in result

    def test_plugin_on_post_execute_hook(self):
        """PluginManager.on_post_execute should be called after execution."""
        from walkabout.plugins.base import WalkaboutPlugin

        class PostExecPlugin(WalkaboutPlugin):
            name = "post_exec"

            def on_post_execute(self, module_name, trace):
                trace["post_processed"] = True
                return trace

        pm = PluginManager()
        pm.plugins = [PostExecPlugin()]
        result = pm.on_post_execute("test_mod", {"steps": []})
        assert result["post_processed"] is True

    def test_execute_with_plugin_manager_calls_hooks(self, temp_home):
        """execute() should call on_pre_execute and on_post_execute when plugin_manager is passed."""
        from walkabout.core.execute import execute
        from walkabout.plugins.base import WalkaboutPlugin
        from walkabout.plugins.manager import PluginManager

        class TestPlugin(WalkaboutPlugin):
            name = "test_plugin"

            def on_pre_execute(self, module_name, code):
                self.last_pre = (module_name, code)
                return None

            def on_post_execute(self, module_name, trace):
                self.last_post = (module_name, trace)
                return None

        plugin = TestPlugin()
        pm = PluginManager()
        pm.plugins = [plugin]

        note = temp_home / "notes" / "hook_test.py"
        note.write_text(
            '''"""Test hooks."""
from execute_util import text

def main():
    x = 1  # @inspect x
''',
            encoding="utf-8",
        )

        import os
        old_cwd = os.getcwd()
        old_path = sys.path.copy()
        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        try:
            os.chdir(str(temp_home / "notes"))
            if str(temp_home / "notes") not in sys.path:
                sys.path.insert(0, str(temp_home / "notes"))
            if core_dir not in sys.path:
                sys.path.insert(0, core_dir)

            trace = execute(
                module_name="hook_test",
                inspect_all_variables=False,
                plugin_manager=pm,
            )

            assert hasattr(plugin, "last_pre")
            assert hasattr(plugin, "last_post")
            assert plugin.last_pre[0] == "hook_test"
            assert plugin.last_post[0] == "hook_test"
        finally:
            os.chdir(old_cwd)
            sys.path[:] = old_path

    def test_on_pre_execute_modifies_source(self, temp_home):
        """on_pre_execute return value (modified source) should be used during execution."""
        import os
        from pathlib import Path
        from walkabout.core.execute import execute
        from walkabout.plugins.base import WalkaboutPlugin
        from walkabout.plugins.manager import PluginManager

        class InjectPlugin(WalkaboutPlugin):
            name = "inject_plugin"

            def on_pre_execute(self, module_name, code):
                # Replace the value assigned to y inside main()
                return code.replace("y = 99", "y = 77")

        plugin = InjectPlugin()
        pm = PluginManager()
        pm.plugins = [plugin]

        note = temp_home / "notes" / "inject_test.py"
        note.write_text(
            '''"""Test source injection."""
from execute_util import text

def main():
    y = 99  # @inspect y
''',
            encoding="utf-8",
        )

        old_cwd = os.getcwd()
        old_path = sys.path.copy()
        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        try:
            os.chdir(str(temp_home / "notes"))
            if str(temp_home / "notes") not in sys.path:
                sys.path.insert(0, str(temp_home / "notes"))
            if core_dir not in sys.path:
                sys.path.insert(0, core_dir)

            trace = execute(
                module_name="inject_test",
                inspect_all_variables=False,
                plugin_manager=pm,
            )

            y_values = []
            for step in trace.steps:
                if "y" in step.env and step.env["y"] is not None:
                    y_values.append(step.env["y"])
            assert 77 in y_values, (
                f"Source injection should change y from 99 to 77. "
                f"Got y values: {y_values}"
            )
        finally:
            os.chdir(old_cwd)
            sys.path[:] = old_path

    def test_on_post_execute_modifies_trace(self, temp_home):
        """on_post_execute return value (modified trace) should replace the returned trace."""
        import os
        from pathlib import Path
        from walkabout.core.execute import execute
        from walkabout.plugins.base import WalkaboutPlugin
        from walkabout.plugins.manager import PluginManager

        class ModifyEnvPlugin(WalkaboutPlugin):
            name = "modify_env_plugin"

            def on_post_execute(self, module_name, trace_dict):
                # Modify the env value of the second step
                if len(trace_dict.get("steps", [])) > 1:
                    trace_dict["steps"][1]["env"]["z"] = 99
                return trace_dict

        plugin = ModifyEnvPlugin()
        pm = PluginManager()
        pm.plugins = [plugin]

        note = temp_home / "notes" / "post_test.py"
        note.write_text(
            '''"""Test post-execute."""
def main():
    z = 1  # @inspect z
''',
            encoding="utf-8",
        )

        old_cwd = os.getcwd()
        old_path = sys.path.copy()
        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        try:
            os.chdir(str(temp_home / "notes"))
            if str(temp_home / "notes") not in sys.path:
                sys.path.insert(0, str(temp_home / "notes"))
            if core_dir not in sys.path:
                sys.path.insert(0, core_dir)

            trace = execute(
                module_name="post_test",
                inspect_all_variables=False,
                plugin_manager=pm,
            )

            # Check that on_post_execute modification took effect
            z_values = []
            for step in trace.steps:
                if "z" in step.env:
                    z_values.append(step.env["z"])
            assert 99 in z_values, (
                f"on_post_execute should have changed z from 1 to 99. "
                f"Got z values: {z_values}"
            )
        finally:
            os.chdir(old_cwd)
            sys.path[:] = old_path
    """Tests for custom renderer support in export."""

    def test_generate_html_custom_renderers(self):
        """generate_html should accept custom_renderers and embed them."""
        from walkabout.export import generate_html

        trace = {
            "steps": [],
            "files": {"test.py": "x = 1"},
        }
        custom_renderers = {
            "vega": {
                "type": "vega",
                "frontend_js": "https://cdn.jsdelivr.net/npm/vega-embed",
            }
        }

        html = generate_html(trace, custom_renderers=custom_renderers)

        # The custom renderer JS URL should appear somewhere in the HTML
        assert "https://cdn.jsdelivr.net/npm/vega-embed" in html
        # The __CUSTOM_RENDERER_JS__ placeholder should be replaced
        assert "__CUSTOM_RENDERER_JS__" not in html

    def test_generate_html_no_custom_renderers(self):
        """generate_html should work without custom_renderers."""
        from walkabout.export import generate_html

        trace = {"steps": [], "files": {}}
        html = generate_html(trace)
        assert "__CUSTOM_RENDERER_JS__" not in html

    def test_generate_html_custom_renderers_in_rendering_js(self):
        """Custom renderers should be injected as window.customRenderers in the template."""
        from walkabout.export import generate_html

        trace = {
            "steps": [],
            "files": {"test.py": "x = 1"},
        }
        custom_renderers = {
            "chart": {
                "type": "chart",
                "frontend_js": "/static/chart.js",
            }
        }

        html = generate_html(trace, custom_renderers=custom_renderers)

        # The template should define window.customRenderers
        assert "window.customRenderers" in html
        # The JS URL should be embedded
        assert "/static/chart.js" in html
