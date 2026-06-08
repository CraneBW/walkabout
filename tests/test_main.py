"""Tests for walkabout.__main__ -- CLI entry point, display detection, WSL."""
import sys
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# _has_display()
# ---------------------------------------------------------------------------

class TestHasDisplay:
    """Display detection logic (_has_display)."""

    def test_with_display_env(self, monkeypatch):
        """$DISPLAY is set on Linux => True."""
        monkeypatch.setenv("DISPLAY", ":0")
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        monkeypatch.setattr(sys, "platform", "linux")
        from walkabout.__main__ import _has_display
        assert _has_display() is True

    def test_headless(self, monkeypatch):
        """Neither $DISPLAY nor $WAYLAND_DISPLAY => False on Linux."""
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        monkeypatch.setattr(sys, "platform", "linux")
        from walkabout.__main__ import _has_display
        assert _has_display() is False

    def test_windows_always_has_display(self, monkeypatch):
        """Windows always claims a display."""
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        monkeypatch.setattr(sys, "platform", "win32")
        from walkabout.__main__ import _has_display
        assert _has_display() is True

    def test_macos_always_has_display(self, monkeypatch):
        """macOS always claims a display."""
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        monkeypatch.setattr(sys, "platform", "darwin")
        from walkabout.__main__ import _has_display
        assert _has_display() is True

    def test_wayland_display(self, monkeypatch):
        """$WAYLAND_DISPLAY alone is enough on Linux."""
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        monkeypatch.setattr(sys, "platform", "linux")
        from walkabout.__main__ import _has_display
        assert _has_display() is True


# ---------------------------------------------------------------------------
# _is_wsl()
# ---------------------------------------------------------------------------

class TestIsWsl:
    """WSL detection logic (_is_wsl)."""

    def test_wsl_from_env_var(self, monkeypatch):
        """WSL_DISTRO_NAME set => True."""
        monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
        from walkabout.__main__ import _is_wsl
        assert _is_wsl() is True

    def test_wsl_from_uname_release(self, monkeypatch):
        """No env var but uname contains 'microsoft' => True."""
        monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
        monkeypatch.setattr(
            "platform.uname",
            lambda: MagicMock(release="5.10.16.3-microsoft-standard-WSL2"),
        )
        from walkabout.__main__ import _is_wsl
        assert _is_wsl() is True

    def test_not_wsl(self, monkeypatch):
        """Neither env nor uname => False."""
        monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
        monkeypatch.setattr(
            "platform.uname",
            lambda: MagicMock(release="6.2.0-arch1-1"),
        )
        from walkabout.__main__ import _is_wsl
        assert _is_wsl() is False

    def test_uname_exception_returns_false(self, monkeypatch):
        """If platform.uname() raises, fall back to False."""
        monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
        monkeypatch.setattr("platform.uname", MagicMock(side_effect=Exception))
        from walkabout.__main__ import _is_wsl
        assert _is_wsl() is False


# ---------------------------------------------------------------------------
# main() decision paths
# ---------------------------------------------------------------------------

def _mock_main_deps(monkeypatch):
    """Patch heavyweight main() dependencies so tests can probe the
    decision logic without real side-effects.

    We insert a mock ``walkabout.app`` module into ``sys.modules``
    *before* any import of the real module to avoid pulling in
    heavy framework dependencies (fastapi, starlette, etc.).
    """
    import sys as _sys

    mock_app = MagicMock()
    mock_app.create_app = MagicMock(return_value=MagicMock())
    # Prevent real walkabout.app import during tests
    monkeypatch.setitem(_sys.modules, "walkabout.app", mock_app)

    monkeypatch.setattr("walkabout.config.load_settings", lambda: {"window": {"port": 8000}})
    monkeypatch.setattr("walkabout.plugins.manager.PluginManager", MagicMock)
    monkeypatch.setattr("walkabout.__main__._wait_for_server", lambda *a, **kw: True)
    monkeypatch.setattr("walkabout.__main__.threading.Thread", MagicMock)


class TestMainDecisionPaths:
    """Verify that main() routes to the correct code path based on
    display, WSL, and --no-gui."""

    def test_wsl_with_display_allows_gui(self, monkeypatch, capsys):
        """WSL + $DISPLAY set => falls through to GUI path."""
        monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
        monkeypatch.setenv("DISPLAY", ":0")
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        monkeypatch.setattr(sys, "platform", "linux")
        _mock_main_deps(monkeypatch)

        # Use mutable container to track calls from within closures
        tracker = {"direct_server_call": False}

        def track_run_server(*a, **kw):
            tracker["direct_server_call"] = True
        monkeypatch.setattr("walkabout.__main__._run_server", track_run_server)

        # Make open_window importable (simulate pywebview available)
        monkeypatch.setattr("walkabout.webview.open_window", lambda url: True)

        from walkabout.__main__ import main
        main([])

        captured = capsys.readouterr()
        # The WSL-server banner must NOT appear (we are NOT taking the
        # old "WSL always skips GUI" path).
        assert "WSL2 detected" not in captured.out
        # We should reach the GUI path.
        assert "Launching native window" in captured.out
        # _run_server should NOT be called directly (it runs in a thread).
        assert not tracker["direct_server_call"], (
            "_run_server was called directly (server path) instead of via thread"
        )

    def test_wsl_without_display_goes_headless(self, monkeypatch, capsys):
        """WSL + no $DISPLAY => server mode with WSL banner."""
        monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        monkeypatch.setattr(sys, "platform", "linux")
        _mock_main_deps(monkeypatch)

        tracker = {"direct_server_call": False}

        def track_run_server(*a, **kw):
            tracker["direct_server_call"] = True
        monkeypatch.setattr("walkabout.__main__._run_server", track_run_server)

        from walkabout.__main__ import main
        main([])

        captured = capsys.readouterr()
        assert "WSL2 detected" in captured.out
        assert tracker["direct_server_call"], (
            "expected _run_server to be called directly in WSL headless mode"
        )

    def test_headless_linux_no_wsl(self, monkeypatch, capsys):
        """Linux, no WSL, no display => server mode."""
        monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
        monkeypatch.setattr(
            "platform.uname", lambda: MagicMock(release="6.2.0-arch1-1")
        )
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        monkeypatch.setattr(sys, "platform", "linux")
        _mock_main_deps(monkeypatch)

        tracker = {"direct_server_call": False}

        def track_run_server(*a, **kw):
            tracker["direct_server_call"] = True
        monkeypatch.setattr("walkabout.__main__._run_server", track_run_server)

        from walkabout.__main__ import main
        main([])

        captured = capsys.readouterr()
        assert "Headless mode" in captured.out
        assert tracker["direct_server_call"]

    def test_no_gui_flag_forces_server_mode(self, monkeypatch, capsys):
        """--no-gui forces server mode even with a display available."""
        monkeypatch.setenv("DISPLAY", ":0")
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        monkeypatch.setattr(sys, "platform", "linux")
        _mock_main_deps(monkeypatch)

        tracker = {"direct_server_call": False}

        def track_run_server(*a, **kw):
            tracker["direct_server_call"] = True
        monkeypatch.setattr("walkabout.__main__._run_server", track_run_server)

        from walkabout.__main__ import main
        main(["--no-gui"])

        captured = capsys.readouterr()
        assert "Server mode (--no-gui)" in captured.out
        assert tracker["direct_server_call"]

    def test_wsl_with_no_gui_flag(self, monkeypatch, capsys):
        """WSL + DISPLAY + --no-gui => still server mode (no GUI skip)."""
        monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
        monkeypatch.setenv("DISPLAY", ":0")
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        monkeypatch.setattr(sys, "platform", "linux")
        _mock_main_deps(monkeypatch)

        tracker = {"direct_server_call": False}

        def track_run_server(*a, **kw):
            tracker["direct_server_call"] = True
        monkeypatch.setattr("walkabout.__main__._run_server", track_run_server)

        from walkabout.__main__ import main
        main(["--no-gui"])

        captured = capsys.readouterr()
        assert "Server mode (--no-gui)" in captured.out
        assert tracker["direct_server_call"], (
            "expected _run_server with --no-gui on WSL"
        )


class TestArgparse:
    """CLI argument parsing."""

    def test_no_gui_flag_default_false(self):
        from walkabout.__main__ import create_parser
        parser = create_parser()
        args = parser.parse_args([])
        assert args.no_gui is False

    def test_no_gui_flag_set_true(self):
        from walkabout.__main__ import create_parser
        parser = create_parser()
        args = parser.parse_args(["--no-gui"])
        assert args.no_gui is True

    def test_unknown_args_raise_error(self):
        from walkabout.__main__ import create_parser
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--bogus"])
