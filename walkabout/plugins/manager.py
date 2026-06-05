"""Plugin discovery and lifecycle management."""
import importlib
import logging
import sys

from ..config import PLUGINS_DIR, ensure_dirs
from .base import WalkaboutPlugin

_log = logging.getLogger(__name__)

class PluginManager:
    def __init__(self):
        self.plugins: list[WalkaboutPlugin] = []

    def discover(self):
        """Load plugins from ~/.walkabout/plugins/."""
        ensure_dirs()
        self.plugins = []
        for item in PLUGINS_DIR.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                try:
                    sys.path.insert(0, str(item.parent))
                    mod = importlib.import_module(f"plugins.{item.name}")
                    for attr in dir(mod):
                        obj = getattr(mod, attr)
                        if (isinstance(obj, type) and issubclass(obj, WalkaboutPlugin)
                                and obj is not WalkaboutPlugin):
                            plugin = obj()
                            self.plugins.append(plugin)
                except Exception as e:
                    print(f"[plugin] Failed to load {item.name}: {e}")

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
