"""
Functions such as (e.g., note, image, link) populate the list of renderings,
which will be shown in place of the line of code in the interface.
"""
from __future__ import annotations

import inspect
import os
import re
import subprocess
import sys
from dataclasses import dataclass

from walkabout.core.file_util import cached, relativize

# arxiv_util imported lazily inside link()
from walkabout.core.reference import Reference


@dataclass(frozen=True)
class CodeLocation:
    """Refers to a specific line of code."""
    path: str
    line_number: int


@dataclass(frozen=True)
class Rendering:
    """
    Specifies what to display instead of a line of code.  Types:
    - text: plain text (verbatim)
    - markdown: to be rendered as markdown
    - image: an image (data = url)
    - link: an link to internal code or external URL
    """
    type: str
    data: str | None = None
    style: dict | None = None
    external_link: Reference | None = None
    internal_link: CodeLocation | None = None

############################################################

def text(message: str, style: dict | None = None, verbatim: bool = False):
    """Make a note (bullet point) with `message`."""
    style = style or {}
    if verbatim:
        messages = message.split("\n")
        style = {
            "fontFamily": "monospace",
            "whiteSpace": "pre",
            **style
        }
    else:
        messages = [message]

    for message in messages:
        _current_renderings.append(Rendering(type="markdown", data=message, style=style))


def image(url: str, style: dict | None = None, width: int | str | None = None):
    """Show the image at `url`."""
    style = style or {}
    if width is not None:
        style["width"] = width

    if is_url(url):
        path = cached(url, "image")
    else:
        path = url
        if not os.path.exists(path):
            raise ValueError(f"Image not found: {path}")

    _current_renderings.append(Rendering(type="image", data=path, style=style))


def is_url(url: str) -> bool:
    """Check if `url` looks like a URL."""
    return url.startswith("http")


def link(arg: type | Reference | str | None = None, style: dict | None = None, **kwargs):
    """
    Shows a link.  There are four possible usages:
    1. link(title="...", url="...") [Creates a new reference]
    2. link(arg: Reference) [Shows an existing reference]
    3. link(arg: type) [Shows a link to the code]
    4. link(arg: str) [Creates a new reference with the given URL]
    """
    style = style or {}

    if arg is None:
        reference = Reference(**kwargs)
        _current_renderings.append(Rendering(type="link", style=style, external_link=reference))
    elif isinstance(arg, Reference):
        _current_renderings.append(Rendering(type="link", style=style, external_link=arg))
    elif isinstance(arg, type) or callable(arg):
        path = inspect.getfile(arg)
        _, line_number = inspect.getsourcelines(arg)
        anchor = CodeLocation(relativize(path), line_number)
        _current_renderings.append(Rendering(type="link", data=arg.__name__, style=style, internal_link=anchor))
    elif isinstance(arg, str):
        from walkabout.core.arxiv_util import arxiv_reference, is_arxiv_link
        if is_arxiv_link(arg):
            try:
                reference = arxiv_reference(arg)
                _current_renderings.append(Rendering(type="link", style=style, external_link=reference))
            except Exception:
                reference = Reference(url=arg)
                _current_renderings.append(Rendering(type="link", style=style, external_link=reference))
        else:
            reference = Reference(url=arg)
            _current_renderings.append(Rendering(type="link", style=style, external_link=reference))
    else:
        raise ValueError(f"Invalid argument: {arg}")


############################################################

# ── RendererRegistry ──────────────────────────────────────


class RendererRegistry:
    """Registry for custom renderer types provided by plugins."""

    def __init__(self):
        self._registry: dict[str, callable] = {}

    def register(self, type_name: str, render_fn: callable):
        """Register a renderer function for *type_name*.

        Raises ValueError if *type_name* is already registered.
        """
        if type_name in self._registry:
            raise ValueError(f"Renderer '{type_name}' already registered")
        self._registry[type_name] = render_fn

    def get(self, type_name: str) -> callable | None:
        """Return the renderer function for *type_name*, or None."""
        return self._registry.get(type_name)

    def has(self, type_name: str) -> bool:
        """Return True if *type_name* is registered."""
        return type_name in self._registry

    def list(self) -> list[str]:
        """Return a list of all registered type names."""
        return list(self._registry.keys())

    def all(self) -> dict[str, callable]:
        """Return the full {type_name: function} dict."""
        return dict(self._registry)


# ── Module-level registry singleton ───────────────────────

_renderer_registry: RendererRegistry | None = None


def get_renderer_registry() -> RendererRegistry:
    """Return the module-level RendererRegistry singleton."""
    global _renderer_registry
    if _renderer_registry is None:
        _renderer_registry = RendererRegistry()
    return _renderer_registry


def set_renderer_registry(registry: RendererRegistry | None):
    """Set the module-level RendererRegistry (used by PluginManager)."""
    global _renderer_registry
    _renderer_registry = registry


# ── custom_render() ───────────────────────────────────────


def custom_render(type_name: str, data: str | None = None,
                  style: dict | None = None,
                  strict: bool = False):
    """Create a custom rendering of *type_name*.

    In strict mode, validates that *type_name* is registered in the
    global registry.  Non-strict mode (default) always creates the
    rendering, which allows subprocess execution without the registry.
    """
    if strict:
        reg = get_renderer_registry()
        if not reg.has(type_name):
            raise ValueError(f"Custom renderer '{type_name}' not registered")
    _current_renderings.append(
        Rendering(type=type_name, data=data, style=style)
    )


############################################################

# Accumulate the renderings during execution (gets flushed).
_current_renderings: list[Rendering] = []

def pop_renderings() -> list[Rendering]:
    """Return the renderings and clear the list."""
    renderings = _current_renderings.copy()
    _current_renderings.clear()
    return renderings


def system_text(command: list[str]):
    kwargs = {"text": True, "timeout": 30}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    output = subprocess.check_output(command, **kwargs)
    output = remove_ansi_escape_sequences(output)
    text(output, verbatim=True)


def remove_ansi_escape_sequences(input_text: str) -> str:
    ansi_escape_pattern = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape_pattern.sub('', input_text)
