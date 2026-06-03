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
    print(f"   Settings:  {settings.get('_file', '~/.walkabout/settings.json')}")
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

    # 1st choice: pywebview (native window, no external browser)
    try:
        from walkabout.webview import open_window

        def serve():
            uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

        server_thread = threading.Thread(target=serve, daemon=True)
        server_thread.start()
        time.sleep(1.5)
        print(f"   Launching native window...")
        open_window(url)
        return
    except ImportError:
        pass
    except Exception as e:
        print(f"   pywebview failed ({e}), trying alternatives...")

    # 2nd choice: system browser with localhost
    print(f"   Opening {url} in browser...")
    import webbrowser
    webbrowser.open(url)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
