"""Tests for walkabout.config — settings engine, schema, defaults, merge."""
import json
import sys

from walkabout.config import (
    SETTINGS_SCHEMA,
    _deep_merge,
    _diff_settings,
    _get_venv_python,
    get_defaults,
    get_python_path,
    get_setting,
    load_settings,
    save_settings,
    set_setting,
)


class TestSchemaIntegrity:
    """Verify the settings schema is well-formed."""

    def test_all_keys_have_required_fields(self):
        required = {"key", "type", "default", "description", "category"}
        for item in SETTINGS_SCHEMA:
            missing = required - set(item.keys())
            assert not missing, f"Schema item {item.get('key', '?')} missing: {missing}"

    def test_all_keys_are_unique(self):
        keys = [item["key"] for item in SETTINGS_SCHEMA]
        assert len(keys) == len(set(keys)), "Duplicate keys in schema"

    def test_all_keys_are_dotted(self):
        for item in SETTINGS_SCHEMA:
            assert "." in item["key"], f"Key {item['key']} is not dotted"

    def test_enum_items_have_valid_default(self):
        for item in SETTINGS_SCHEMA:
            if "enum" in item:
                assert item["default"] in item["enum"], (
                    f"Default '{item['default']}' not in enum {item['enum']} for {item['key']}"
                )

    def test_boolean_defaults_are_bool(self):
        for item in SETTINGS_SCHEMA:
            if item["type"] == "boolean":
                assert isinstance(item["default"], bool), f"{item['key']} default not bool"


class TestDefaults:
    """Test default settings generation."""

    def test_get_defaults_returns_dict(self):
        defaults = get_defaults()
        assert isinstance(defaults, dict)

    def test_all_schema_keys_in_defaults(self):
        defaults = get_defaults()
        for item in SETTINGS_SCHEMA:
            parts = item["key"].split(".")
            d = defaults
            for p in parts:
                assert p in d, f"Key {item['key']} missing in defaults at {p}"
                d = d[p]

    def test_port_default(self):
        defaults = get_defaults()
        assert defaults["window"]["port"] == 8000

    def test_editor_font_size_default(self):
        defaults = get_defaults()
        assert defaults["editor"]["fontSize"] == 14

    def test_appearance_theme_default(self):
        defaults = get_defaults()
        assert defaults["appearance"]["theme"] == "dark"


class TestDeepMerge:
    """Test the deep merge utility."""

    def test_nested_merge(self):
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"x": 99}}
        result = _deep_merge(base, override)
        assert result["a"]["x"] == 99
        assert result["a"]["y"] == 2  # preserved from base
        assert result["b"] == 3

    def test_new_key_added(self):
        base = {"a": 1}
        override = {"b": 2}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 2}

    def test_override_replaces_non_dict(self):
        base = {"a": 1}
        override = {"a": {"nested": True}}
        result = _deep_merge(base, override)
        assert result["a"] == {"nested": True}

    def test_empty_override(self):
        base = {"a": 1}
        assert _deep_merge(base, {}) == {"a": 1}


class TestDiffSettings:
    """Test settings diff — only returns changed keys."""

    def test_no_changes(self):
        d = {"a": 1, "b": {"x": 2}}
        assert _diff_settings(d, d) == {}

    def test_simple_change(self):
        defaults = {"a": 1}
        current = {"a": 2}
        assert _diff_settings(defaults, current) == {"a": 2}

    def test_nested_change(self):
        defaults = {"editor": {"fontSize": 14}}
        current = {"editor": {"fontSize": 18}}
        assert _diff_settings(defaults, current) == {"editor": {"fontSize": 18}}

    def test_new_key_not_in_defaults(self):
        defaults = {"a": 1}
        current = {"a": 1, "b": 2}
        assert _diff_settings(defaults, current) == {"b": 2}

    def test_partial_nested_diff(self):
        defaults = {"editor": {"fontSize": 14, "theme": "vs-dark"}}
        current = {"editor": {"fontSize": 18, "theme": "vs-dark"}}
        result = _diff_settings(defaults, current)
        assert result == {"editor": {"fontSize": 18}}


class TestLoadSaveSettings:
    """Test settings persistence."""

    def test_load_defaults_when_no_file(self, temp_home):
        settings_file = temp_home / "settings.json"
        if settings_file.exists():
            settings_file.unlink()
        settings = load_settings()
        assert settings["window"]["port"] == 8000

    def test_load_corrupt_json_falls_back(self, temp_home):
        settings_file = temp_home / "settings.json"
        settings_file.write_text("{invalid json!!!", encoding="utf-8")
        settings = load_settings()
        assert settings["window"]["port"] == 8000  # fallback

    def test_save_and_reload(self, temp_home):
        settings_file = temp_home / "settings.json"
        save_settings({"window": {"port": 9999}})
        assert settings_file.exists()
        loaded = load_settings()
        assert loaded["window"]["port"] == 9999

    def test_save_strips_defaults(self, temp_home):
        """Only non-default values are saved to disk."""
        settings_file = temp_home / "settings.json"
        settings = load_settings()  # all defaults
        settings["window"]["port"] = 9000  # change one value
        save_settings(settings)
        saved = json.loads(settings_file.read_text(encoding="utf-8"))
        # Only the changed key and its category should appear
        assert "window" in saved
        assert saved["window"].get("port") == 9000
        # Default values should NOT be saved
        assert saved["window"].get("height") is None

    def test_get_setting(self, temp_home):
        settings_file = temp_home / "settings.json"
        settings_file.write_text('{"window": {"port": 1234}}', encoding="utf-8")
        assert get_setting("window.port") == 1234

    def test_set_setting(self, temp_home):
        set_setting("window.port", 4321)
        assert get_setting("window.port") == 4321


class TestVenvPython:
    """Test venv Python detection on different platforms."""

    def test_windows_venv_path(self, temp_home, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")
        scripts = temp_home / ".venv" / "Scripts"
        scripts.mkdir(parents=True)
        (scripts / "python.exe").write_text("")
        result = _get_venv_python(temp_home / ".venv")
        assert "Scripts" in result and result.endswith("python.exe")

    def test_unix_venv_path(self, temp_home, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        bin_dir = temp_home / ".venv" / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "python3").write_text("")
        result = _get_venv_python(temp_home / ".venv")
        assert result.endswith("bin/python3")


class TestGetPythonPath:
    """Test Python interpreter resolution."""

    def test_frozen_returns_executable(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "executable", "/fake/python")
        assert get_python_path() == "/fake/python"

    def test_windows_fallback(self, temp_home, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setattr(sys, "frozen", False, raising=False)
        monkeypatch.setattr("walkabout.config.get_setting", lambda k: "")
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        result = get_python_path()
        assert result == "python"

    def test_unix_fallback(self, temp_home, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(sys, "frozen", False, raising=False)
        monkeypatch.setattr("walkabout.config.get_setting", lambda k: "")
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        result = get_python_path()
        assert result == "python3"
