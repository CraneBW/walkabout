"""Entry point: walkabout or python -m walkabout

Launches as a standalone desktop app with embedded webview.
No external browser required.
"""
import sys, os, threading, time, signal
import uvicorn


def main():
    from walkabout.config import NOTES_DIR, TRACES_DIR, FILES_DIR, load_settings
    from walkabout.plugins.manager import PluginManager

    settings = load_settings()
    port = settings.get("window", {}).get("port", 8000)

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
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
        return

    if not has_display:
        print(f"   Headless mode — server starting at {url}\n")
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
        return

    # Has display — try native window
    try:
        from walkabout.webview import open_window

        def serve():
            uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

        server_thread = threading.Thread(target=serve, daemon=True)
        server_thread.start()
        time.sleep(1.5)
        print("   Launching native window...")
        open_window(url)
        return
    except ImportError:
        pass
    except Exception as e:
        print(f"   pywebview failed ({e}), falling back to browser...")

    # Fallback: system browser
    print(f"   Opening {url} ...")
    import webbrowser
    webbrowser.open(url)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
