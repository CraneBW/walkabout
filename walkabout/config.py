"""Walkabout configuration — workspace, Python interpreter, settings, plugins."""
import os, json, shutil
from pathlib import Path

WALKABOUT_HOME = Path(os.environ.get("WALKABOUT_HOME", Path.home() / ".walkabout"))
NOTES_DIR = WALKABOUT_HOME / "notes"
TRACES_DIR = WALKABOUT_HOME / "traces"
FILES_DIR = WALKABOUT_HOME / "files"
SETTINGS_FILE = WALKABOUT_HOME / "settings.json"
PLUGINS_DIR = WALKABOUT_HOME / "plugins"


def ensure_dirs():
    for d in [NOTES_DIR, TRACES_DIR, FILES_DIR, PLUGINS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def load_settings() -> dict:
    ensure_dirs()
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE) as f:
            return json.load(f)
    return {}


def save_settings(s: dict):
    ensure_dirs()
    with open(SETTINGS_FILE, "w") as f:
        json.dump(s, f, indent=2)


def get_python_path() -> str:
    """Return configured Python interpreter path (configurable via settings or env)."""
    # 1. Explicit config in settings.json
    settings = load_settings()
    path = settings.get("python_path", "")
    if path and Path(path).exists():
        return path
    # 2. Workspace venv
    for candidate in [
        WALKABOUT_HOME / ".venv" / "bin" / "python3",
        WALKABOUT_HOME / ".venv" / "bin" / "python",
    ]:
        if candidate.exists():
            return str(candidate)
    # 3. System python
    for cmd in ["python3", "python"]:
        p = shutil.which(cmd)
        if p:
            return p
    return "python3"


def set_python_path(path: str):
    settings = load_settings()
    settings["python_path"] = path
    save_settings(settings)


def get_plugin_dir(name: str) -> Path:
    return PLUGINS_DIR / name
