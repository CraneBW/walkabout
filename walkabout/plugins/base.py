"""Base class for Walkabout plugins."""
from __future__ import annotations

from abc import ABC

from walkabout.core.execute_util import RendererRegistry


def register_renderer(type_name: str):
    """Decorator that marks a plugin method as a custom renderer.

    Usage::

        class MyPlugin(WalkaboutPlugin):
            @register_renderer("vega")
            def render_vega(self, rendering_data, style):
                return {"svg": rendering_data}
    """
    def decorator(method):
        method._renderer_type = type_name
        return method
    return decorator


class WalkaboutPlugin(ABC):  # noqa: B024
    """Plugins can hook into the execution pipeline and add UI features."""
    name: str = "unnamed"
    version: str = "0.1.0"

    def on_startup(self, app):  # noqa: B027
        """Called when the FastAPI app starts."""
        pass

    def on_pre_execute(self, module_name: str, code: str) -> str | None:
        """Called before execution. Return modified code or None."""
        return None

    def on_post_execute(self, module_name: str, trace: dict) -> dict | None:
        """Called after execution. Return modified trace or None."""
        return None

    def get_frontend_components(self) -> list[dict]:
        """Return frontend component descriptors for UI extension."""
        return []

    def on_register_renderers(self, registry: RendererRegistry):  # noqa: B027
        """Register custom renderers with *registry*.

        The default implementation scans for methods decorated with
        ``@register_renderer`` and registers them automatically.
        Override for custom registration logic.
        """
        import inspect
        for _name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            renderer_type = getattr(method, "_renderer_type", None)
            if renderer_type is not None:
                registry.register(renderer_type, method)
