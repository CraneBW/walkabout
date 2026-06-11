"""Plugin discovery and lifecycle management."""
import importlib
import logging
import sys

from .. import config as _config
from ..core.execute_util import RendererRegistry, set_renderer_registry
from .base import WalkaboutPlugin

_log = logging.getLogger(__name__)

class PluginManager:
    def __init__(self):
        self.plugins: list[WalkaboutPlugin] = []
        self.registry: RendererRegistry = RendererRegistry()

    def discover(self):
        """Load plugins from ~/.walkabout/plugins/ and collect renderers."""
        _config.ensure_dirs()
        self.plugins = []
        # Reset registry so that repeated discover() calls do not
        # raise duplicate-registration errors.
        self.registry = RendererRegistry()
        for item in _config.PLUGINS_DIR.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                try:
                    sys.path.insert(0, str(_config.PLUGINS_DIR.parent))
                    mod = importlib.import_module(f"plugins.{item.name}")
                    for attr in dir(mod):
                        obj = getattr(mod, attr)
                        if (isinstance(obj, type) and issubclass(obj, WalkaboutPlugin)
                                and obj is not WalkaboutPlugin):
                            plugin = obj()
                            self.plugins.append(plugin)
                except Exception as e:
                    print(f"[plugin] Failed to load {item.name}: {e}")
        self._collect_renderers()

    def _collect_renderers(self):
        """Call on_register_renderers on each plugin and share globally."""
        for p in self.plugins:
            try:
                p.on_register_renderers(self.registry)
            except Exception:
                _log.warning("Plugin %s on_register_renderers failed", p.name,
                             exc_info=True)
        set_renderer_registry(self.registry)

    def on_startup(self, app):
        for p in self.plugins:
            try:
                p.on_startup(app)
            except Exception:
                _log.warning("Plugin %s on_startup failed", p.name, exc_info=True)

    def on_pre_execute(self, module_name: str, code: str) -> str:
        for p in self.plugins:
            try:
                result = p.on_pre_execute(module_name, code)
                if result is not None:
                    code = result
            except Exception:
                _log.warning("Plugin %s on_pre_execute failed", p.name, exc_info=True)
        return code

    def on_post_execute(self, module_name: str, trace: dict) -> dict:
        for p in self.plugins:
            try:
                result = p.on_post_execute(module_name, trace)
                if result is not None:
                    trace = result
            except Exception:
                _log.warning("Plugin %s on_post_execute failed", p.name, exc_info=True)
        return trace
