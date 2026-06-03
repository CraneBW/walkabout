"""Entry point: walkabout or python -m walkabout

Launches as a standalone desktop app with embedded webview.
No external browser required.
"""
import sys, os, threading, time, socket


def _create_bind_socket(host: str, port: int) -> socket.socket:
    """Create a TCP socket with SO_REUSEADDR, bound and listening."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(2048)
    return sock


def _run_server(app, host: str, port: int, log_level: str = "info") -> None:
    """Run uvicorn with a pre-created socket to avoid TIME-WAIT conflicts."""
    import uvicorn

    sock = _create_bind_socket(host, port)
    config = uvicorn.Config(app, host=host, port=port, log_level=log_level)
    server = uvicorn.Server(config=config)
    server.run(sockets=[sock])


def main():
    from walkabout.config import NOTES_DIR, TRACES_DIR, FILES_DIR, load_settings
    from walkabout.plugins.manager import PluginManager

    settings = load_settings()
    port = settings.get("window", {}).get("port", 8000)
    host = "127.0.0.1"

    print(" Walkabout — Interactive Code Walkthrough Editor")

    # Load plugins
    pm = PluginManager()
    pm.discover()
    if pm.plugins:
        print(f"   Plugins: {', '.join(p.name for p in pm.plugins)}")

    print(f"   Workspace: {NOTES_DIR}")
    print(f"   Settings:  ~/.walkabout/settings.json")
    print()

    # Check frontend
    from pathlib import Path
    dist = Path(__file__).parent.parent / "frontend" / "dist" / "index.html"
    if not dist.exists():
        print("   ⚠  Frontend not built. First-time setup:")
        print("      cd frontend && npm install && npm run build")
        print()

    from walkabout.app import create_app
    app = create_app()
    url = f"http://localhost:{port}"

    # Detect headless / WSL — skip GUI, use server-only mode
    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    is_wsl = "microsoft" in os.uname().release.lower() or bool(os.environ.get("WSL_DISTRO_NAME", ""))

    if is_wsl:
        print(f"   WSL2 detected — server starting at:")
        print(f"   →  {url}")
        print(f"   Open this URL in your Windows browser. (WSL2 auto-forwards localhost)\n")
        _run_server(app, host, port, log_level="info")
        return

    if not has_display:
        print(f"   Headless mode — server starting at {url}\n")
        _run_server(app, host, port, log_level="info")
        return

    # Has display — try native window
    try:
        from walkabout.webview import open_window
    except ImportError:
        open_window = None  # pywebview not installed, skip native window

    if open_window:
        # Start server in background thread for the native window case
        server_thread = threading.Thread(
            target=_run_server,
            args=(app, host, port),
            kwargs=dict(log_level="warning"),
            daemon=True,
        )
        server_thread.start()
        time.sleep(1.5)
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
            # Server thread is already running — keep the process alive by waiting
            server_thread.join()
            return

    # Fallback: browser mode (server runs in main thread)
    print(f"   Opening {url} ...")
    import webbrowser
    webbrowser.open(url)
    _run_server(app, host, port, log_level="info")


if __name__ == "__main__":
    main()
