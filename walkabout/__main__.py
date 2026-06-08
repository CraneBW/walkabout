"""Entry point: walkabout or python -m walkabout

Launches as a standalone desktop app with embedded webview.
No external browser required.
"""
import argparse
import contextlib
import os
import platform
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any


def _create_bind_socket(host: str, port: int) -> socket.socket:
    """Create a TCP socket with SO_REUSEADDR, bound and listening."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(2048)
    return sock


def _run_server(app, host: str, port: int, log_level: str = "info",
                ready: threading.Event = None) -> None:
    """Run uvicorn with a pre-created socket.  Signals *ready* when the
    socket is bound so the main thread can open the GUI window safely."""
    import uvicorn

    try:
        sock = _create_bind_socket(host, port)
    except OSError:
        print(f"\n   Error: Port {port} is already in use.")
        print("   Or change port in ~/.walkabout/settings.json (window.port)\n")
        return

    if ready:
        ready.set()

    config = uvicorn.Config(app, host=host, port=port, log_level=log_level)
    server = uvicorn.Server(config=config)
    server.run(sockets=[sock])


def _wait_for_server(port: int, timeout: float = 5.0) -> bool:
    """Poll until the HTTP server accepts connections or *timeout* expires."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            s = socket.socket()
            s.settimeout(0.5)
            s.connect(("127.0.0.1", port))
            s.close()
            return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.1)
    return False


# ── Display and WSL detection utilities ──────────────────────────────────


def _has_display() -> bool:
    """Return True when a GUI display is available.

    Windows and macOS always have a display.  On Linux we check
    ``$DISPLAY`` or ``$WAYLAND_DISPLAY``.
    """
    if sys.platform in ("win32", "darwin"):
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _is_wsl() -> bool:
    """Return True when running inside WSL (Windows Subsystem for Linux).

    Detection uses the ``WSL_DISTRO_NAME`` environment variable first,
    then falls back to checking ``platform.uname().release`` for
    ``"microsoft"`` (kernel string).
    """
    is_wsl = bool(os.environ.get("WSL_DISTRO_NAME", ""))
    if not is_wsl:
        with contextlib.suppress(Exception):
            is_wsl = "microsoft" in platform.uname().release.lower()
    return is_wsl


# ── CLI argument parser ─────────────────────────────────────────────────


def create_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="walkabout",
        description="Walkabout — Interactive Code Walkthrough Editor",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Force server-only mode; do not attempt to open a GUI window",
    )
    subparsers = parser.add_subparsers(dest="subcommand")
    # No subcommand → defaults to serve (handled in main())
    subparsers.required = False

    # serve
    _ = subparsers.add_parser(
        "serve", help="Start the server and GUI (default behaviour)",
    )

    # run
    run_p = subparsers.add_parser(
        "run",
        help="Execute a walkthrough script headlessly and save trace JSON",
    )
    run_p.add_argument("script", help="Path to the walkthrough .py script")
    run_p.add_argument(
        "-o", "--output", default=None,
        help="Output trace JSON path (default: SCRIPT.json)",
    )
    run_p.add_argument(
        "--inspect-all", action="store_true",
        help="Capture all local variables (not just @inspect)",
    )

    # export
    export_p = subparsers.add_parser(
        "export",
        help="Export a walkthrough to standalone HTML",
    )
    export_p.add_argument(
        "script", nargs="?", default=None,
        help="Path to the walkthrough .py script",
    )
    export_p.add_argument(
        "--from-trace", default=None,
        help="Path to existing trace JSON (export without re-executing)",
    )
    export_p.add_argument(
        "-o", "--output", default=None,
        help="Output HTML path (default: SCRIPT.html or TRACE.html)",
    )
    export_p.add_argument(
        "--strip-source", action="store_true",
        help="Strip unreferenced source lines from trace",
    )
    export_p.add_argument(
        "--content-only", action="store_true",
        help="Export rendered content only, no source code",
    )

    return parser


# ── Subcommand handlers ──────────────────────────────────────────────────


def run_command(script: str, output: str | None,
                inspect_all: bool) -> dict[str, Any]:
    """Execute a walkthrough script and save trace JSON.

    Returns the trace dict.
    """
    from walkabout.runner import execute_note

    script = os.path.abspath(script)
    if not output:
        output = os.path.splitext(os.path.basename(script))[0] + ".json"
    else:
        output = os.path.abspath(output)

    trace_dict = execute_note(script, output, inspect_all)
    steps = len(trace_dict.get("steps", []))
    print(f"Trace saved: {output} ({steps} steps)", file=sys.stderr)
    return trace_dict


def export_command(
    script: str | None,
    from_trace: str | None,
    output: str | None,
    strip_source: bool,
    content_only: bool,
) -> Path | None:
    """Export a walkthrough to standalone HTML.

    Either *script* (execute first) or *from_trace* (use existing trace
    JSON) must be provided.  *output* defaults to the script/trace stem
    with an ``.html`` extension.

    Returns the path to the generated HTML file, or ``None`` on error.
    """
    from walkabout.export import export_note

    if from_trace:
        trace_path = os.path.abspath(from_trace)
        if not os.path.exists(trace_path):
            print(f"Error: Trace file not found: {from_trace}", file=sys.stderr)
            sys.exit(1)
        out = output if output else os.path.splitext(from_trace)[0] + ".html"
        return export_note(Path(trace_path), Path(out),
                          title=None,
                          strip_source=strip_source,
                          content_only=content_only)

    if script:
        script_path = os.path.abspath(script)
        if not os.path.exists(script_path):
            print(f"Error: Script not found: {script}", file=sys.stderr)
            sys.exit(1)
        if not output:
            out = os.path.splitext(os.path.basename(script))[0] + ".html"
        else:
            out = os.path.abspath(output)

        import tempfile

        from walkabout.runner import execute_note

        # Execute first, then export via a temporary trace file.
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            temp_trace = tf.name
        try:
            execute_note(script_path, temp_trace, inspect_all=False)
            result = export_note(Path(temp_trace), Path(out),
                                 title=None,
                                 strip_source=strip_source,
                                 content_only=content_only)
        finally:
            if os.path.exists(temp_trace):
                os.unlink(temp_trace)
        return result

    print("Error: Either a script path or --from-trace is required for export.",
          file=sys.stderr)
    print("Usage: walkabout export SCRIPT.py [-o OUTPUT.html] [--strip-source] [--content-only]",
          file=sys.stderr)
    print("   or: walkabout export --from-trace TRACE.json -o OUTPUT.html",
          file=sys.stderr)
    sys.exit(1)


def serve_command(no_gui: bool = False) -> None:
    """Start the server and optionally open a GUI window (original behaviour)."""
    from walkabout.config import NOTES_DIR, load_settings
    from walkabout.plugins.manager import PluginManager

    settings = load_settings()
    port = settings.get("window", {}).get("port", 8000)
    host = "127.0.0.1"

    print(" Walkabout -- Interactive Code Walkthrough Editor")

    # Load plugins
    pm = PluginManager()
    pm.discover()
    if pm.plugins:
        print(f"   Plugins: {', '.join(p.name for p in pm.plugins)}")

    print(f"   Workspace: {NOTES_DIR}")
    print("   Settings:  ~/.walkabout/settings.json")
    print()

    # Check frontend
    dist = Path(__file__).parent.parent / "frontend" / "dist" / "index.html"
    if not dist.exists():
        print("   [WARN] Frontend not built. First-time setup:")
        print("      cd frontend && npm install && npm run build")
        print()

    from walkabout.app import create_app
    app = create_app()
    url = f"http://localhost:{port}"

    # Resolve launch mode ------------------------------------------------
    has_display = _has_display()
    is_wsl = _is_wsl()

    # --no-gui always overrides: force server-only mode
    if no_gui:
        print(f"   Server mode (--no-gui) --server starting at {url}\n")
        _run_server(app, host, port, log_level="info")
        return

    # WSL detection: check display availability first
    if is_wsl:
        if has_display:
            # WSL with X Server / WSLg -- fall through to GUI code below
            pass
        else:
            # WSL without display -- server mode with WSL forwarding message
            print("   WSL2 detected --server starting at:")
            print(f"   ->  {url}")
            print("   Open this URL in your Windows browser."
                  " (WSL2 auto-forwards localhost)\n")
            _run_server(app, host, port, log_level="info")
            return

    if not has_display:
        print(f"   Headless mode --server starting at {url}\n")
        _run_server(app, host, port, log_level="info")
        return

    # Has display -- try native window
    try:
        from walkabout.webview import open_window
    except ImportError:
        open_window = None  # pywebview not installed, skip native window

    if open_window:
        # Start server in background thread; wait until it is actually
        # accepting connections before opening the GUI window.
        server_ready = threading.Event()
        server_thread = threading.Thread(
            target=_run_server,
            args=(app, host, port),
            kwargs=dict(log_level="warning", ready=server_ready),
            daemon=True,
        )
        server_thread.start()

        if not _wait_for_server(port, timeout=5.0):
            print("   Error: Server did not start in time."
                  " Check the output above.")
            return

        print("   Launching native window...")
        try:
            open_window(url)
            server_thread.join()
            return
        except Exception as e:
            print(f"   pywebview failed ({e}), falling back to browser...")
            print(f"   Opening {url} ...")
            import webbrowser
            webbrowser.open(url)
            server_thread.join()
            return

    # Fallback: browser mode (server runs in main thread)
    print(f"   Opening {url} ...")
    import webbrowser
    webbrowser.open(url)
    _run_server(app, host, port, log_level="info")


# ── Entry point ──────────────────────────────────────────────────────────


def main() -> None:
    """Main entry point — parse CLI args and dispatch to the right handler."""
    parser = create_parser()
    args = parser.parse_args()

    if args.subcommand == "run":
        run_command(args.script, args.output, args.inspect_all)
    elif args.subcommand == "export":
        export_command(args.script, args.from_trace, args.output,
                       args.strip_source, args.content_only)
    else:
        # No subcommand, or "serve" explicitly — original GUI behaviour
        serve_command(no_gui=args.no_gui)


if __name__ == "__main__":
    main()
