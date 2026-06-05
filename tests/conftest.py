"""Shared test fixtures for Walkabout."""
import os, sys, json, tempfile, shutil
from pathlib import Path
import pytest

# Ensure the project root is on sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def temp_home(monkeypatch):
    """Create a temporary WALKABOUT_HOME with clean state."""
    d = tempfile.mkdtemp()
    home = Path(d)
    (home / "notes").mkdir(parents=True)
    (home / "traces").mkdir(parents=True)
    (home / "files").mkdir(parents=True)
    (home / "plugins").mkdir(parents=True)
    monkeypatch.setenv("WALKABOUT_HOME", str(home))
    monkeypatch.setattr("walkabout.config.WALKABOUT_HOME", home)
    monkeypatch.setattr("walkabout.config.NOTES_DIR", home / "notes")
    monkeypatch.setattr("walkabout.config.TRACES_DIR", home / "traces")
    monkeypatch.setattr("walkabout.config.FILES_DIR", home / "files")
    monkeypatch.setattr("walkabout.config.PLUGINS_DIR", home / "plugins")
    monkeypatch.setattr("walkabout.config.SETTINGS_FILE", home / "settings.json")
    monkeypatch.setattr("walkabout.config.DEFAULTS_FILE", home / "settings.default.json")
    yield home
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def demo_walkthrough():
    """Return the content of the demo walkthrough script."""
    demo = PROJECT_ROOT / "walkabout" / "examples" / "demo_walkthrough.py"
    if demo.exists():
        return demo.read_text(encoding="utf-8")
    return ""


@pytest.fixture
def sample_note(temp_home):
    """Create a simple walkthrough note in the temp notes dir."""
    note_content = """\"\"\"Test walkthrough.\"\"\"
from execute_util import text

def main():
    x = 42  # @inspect x
    name = "Test"  # @inspect name
    text("Hello from test")
"""
    note_path = temp_home / "notes" / "test_note.py"
    note_path.write_text(note_content, encoding="utf-8")
    return note_path


@pytest.fixture
def mock_platform(monkeypatch):
    """Utility to mock sys.platform for cross-platform testing."""
    def _set(platform):
        monkeypatch.setattr(sys, "platform", platform)
    return _set
