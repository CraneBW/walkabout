"""Base class for Walkabout plugins."""
from __future__ import annotations

from abc import ABC


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
