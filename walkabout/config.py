"""Walkabout configuration — VS Code-style settings with schema, defaults, validation."""
import os, json, shutil, copy
from pathlib import Path
from typing import Any

WALKABOUT_HOME = Path(os.environ.get("WALKABOUT_HOME", Path.home() / ".walkabout"))
NOTES_DIR = WALKABOUT_HOME / "notes"
TRACES_DIR = WALKABOUT_HOME / "traces"
FILES_DIR = WALKABOUT_HOME / "files"
SETTINGS_FILE = WALKABOUT_HOME / "settings.json"
DEFAULTS_FILE = WALKABOUT_HOME / "settings.default.json"
PLUGINS_DIR = WALKABOUT_HOME / "plugins"

# ── Settings Schema ─────────────────────────────────────────────
# Each setting: {key, type, default, description, category, enum?}
SETTINGS_SCHEMA = [
    # ── Python ──
    {"key": "python.path", "type": "string", "default": "",
     "description": "Path to Python interpreter for running walkthroughs",
     "category": "Python"},
    {"key": "python.timeout", "type": "integer", "default": 60,
     "description": "Execution timeout in seconds", "category": "Python"},
    {"key": "python.args", "type": "array", "default": [],
     "description": "Extra arguments passed to Python interpreter", "category": "Python"},

    # ── Editor ──
    {"key": "editor.fontSize", "type": "integer", "default": 14,
     "description": "Editor font size (px)", "category": "Editor"},
    {"key": "editor.fontFamily", "type": "string", "default": "Fira Code, monospace",
     "description": "Editor font family", "category": "Editor"},
    {"key": "editor.tabSize", "type": "integer", "default": 4,
     "description": "Number of spaces per tab", "category": "Editor"},
    {"key": "editor.wordWrap", "type": "boolean", "default": True,
     "description": "Enable word wrapping", "category": "Editor"},
    {"key": "editor.minimap", "type": "boolean", "default": False,
     "description": "Show minimap", "category": "Editor"},
    {"key": "editor.theme", "type": "string", "default": "vs-dark",
     "enum": ["vs", "vs-dark", "hc-black", "hc-light"],
     "description": "Monaco editor color theme", "category": "Editor"},

    # ── Appearance ──
    {"key": "appearance.theme", "type": "string", "default": "dark",
     "enum": ["dark", "light", "system"],
     "description": "Application color theme", "category": "Appearance"},
    {"key": "appearance.locale", "type": "string", "default": "en",
     "enum": ["en", "zh-CN"],
     "description": "Interface language", "category": "Appearance"},

    # ── Execution ──
    {"key": "execution.autoSave", "type": "boolean", "default": True,
     "description": "Auto-save before running", "category": "Execution"},
    {"key": "execution.clearOutput", "type": "boolean", "default": False,
     "description": "Clear previous output before each run", "category": "Execution"},
    {"key": "execution.animate", "type": "boolean", "default": True,
     "description": "Animate step transitions in viewer", "category": "Execution"},

    # ── Window ──
    {"key": "window.width", "type": "integer", "default": 1400,
     "description": "Window width (px)", "category": "Window"},
    {"key": "window.height", "type": "integer", "default": 900,
     "description": "Window height (px)", "category": "Window"},
    {"key": "window.port", "type": "integer", "default": 8000,
     "description": "Server port", "category": "Window"},

    # ── Export ──
    {"key": "export.directory", "type": "string", "default": "",
     "description": "Directory for exported HTML files (leave empty for ~/.walkabout/exports)",
     "category": "Export"},
]


# ── Settings Engine ─────────────────────────────────────────────

def ensure_dirs():
    for d in [NOTES_DIR, TRACES_DIR, FILES_DIR, PLUGINS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def get_defaults() -> dict:
    """Build default settings dict from schema."""
    defaults = {}
    for item in SETTINGS_SCHEMA:
        keys = item["key"].split(".")
        d = defaults
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = item["default"]
    return defaults


def load_settings() -> dict:
    """Load user settings, deep-merged over defaults."""
    ensure_dirs()
    defaults = get_defaults()
    user = {}
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE) as f:
            user = json.load(f)
    return _deep_merge(defaults, user)


def save_settings(s: dict):
    """Save only user overrides (strip defaults)."""
    ensure_dirs()
    defaults = get_defaults()
    overrides = _diff_settings(defaults, s)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(overrides, f, indent=2, ensure_ascii=False)


def get_setting(key: str) -> Any:
    """Get a single setting value."""
    settings = load_settings()
    for k in key.split("."):
        settings = settings.get(k, {}) if isinstance(settings, dict) else settings
    return settings


def set_setting(key: str, value: Any):
    """Set a single setting and persist."""
    settings = load_settings()
    # Also write to user overrides
    user = {}
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE) as f:
            user = json.load(f)
    keys = key.split(".")
    d = user
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value
    save_settings(_deep_merge(get_defaults(), user))


def get_python_path() -> str:
    path = get_setting("python.path")
    if path and Path(path).exists():
        return path
    for candidate in [
        WALKABOUT_HOME / ".venv" / "bin" / "python3",
        WALKABOUT_HOME / ".venv" / "bin" / "python",
    ]:
        if candidate.exists():
            return str(candidate)
    for cmd in ["python3", "python"]:
        p = shutil.which(cmd)
        if p:
            return p
    return "python3"


def set_python_path(path: str):
    set_setting("python.path", path)


def get_plugin_dir(name: str) -> Path:
    return PLUGINS_DIR / name


# ── Helpers ─────────────────────────────────────────────────────

def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base, returning a new dict."""
    result = copy.deepcopy(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _diff_settings(defaults: dict, current: dict) -> dict:
    """Return only the keys that differ from defaults."""
    diff = {}
    for k, v in current.items():
        if k in defaults:
            if isinstance(v, dict) and isinstance(defaults[k], dict):
                sub = _diff_settings(defaults[k], v)
                if sub:
                    diff[k] = sub
            elif v != defaults[k]:
                diff[k] = v
        else:
            diff[k] = v
    return diff
