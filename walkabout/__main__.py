"""Entry point: walkabout or python -m walkabout"""
import sys, os, threading, time
import uvicorn

def main():
    from walkabout.config import NOTES_DIR, TRACES_DIR, FILES_DIR
    from walkabout.plugins.manager import PluginManager

    print(" Walkabout — Interactive Code Walkthrough Editor")

    # Load plugins
    pm = PluginManager()
    pm.discover()
    if pm.plugins:
        print(f"   Plugins: {', '.join(p.name for p in pm.plugins)}")

    print(f"   Workspace: {NOTES_DIR}")
    print(f"   Traces:    {TRACES_DIR}")
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

    # Try embedded window, fall back to browser
    url = "http://localhost:8000"
    try:
        from walkabout.webview import open_window
        # Run uvicorn in a thread, open webview in main thread
        def serve():
            uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
        t = threading.Thread(target=serve, daemon=True)
        t.start()
        time.sleep(1.5)
        open_window(url)
    except Exception:
        print(f"  Opening {url} ...")
        import webbrowser
        webbrowser.open(url)
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")

if __name__ == "__main__":
    main()
