"""Embedded webview window — no external browser needed."""
import sys, threading, time

def open_window(url: str = "http://localhost:8000"):
    """Open the Walkabout UI in an embedded window. Falls back to browser."""
    # Try pywebview first (native window, no external browser)
    try:
        import webview
        # Start server in background thread
        def run_server():
            import uvicorn
            from .app import create_app
            app = create_app()
            uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        time.sleep(1)  # Wait for server to be ready

        webview.create_window(
            "Walkabout — Interactive Code Walkthrough",
            url,
            width=1400, height=900,
            min_size=(900, 600),
            text_select=True,
        )
        webview.start()
        return True
    except ImportError:
        pass

    # Try PyQt5/PySide6 as fallback
    try:
        from PyQt5 import QtWebEngineWidgets, QtWidgets, QtCore
        app = QtWidgets.QApplication(sys.argv)
        web = QtWebEngineWidgets.QWebEngineView()
        web.load(QtCore.QUrl(url))
        web.resize(1400, 900)
        web.setWindowTitle("Walkabout")
        web.show()
        app.exec_()
        return True
    except ImportError:
        pass

    # Fallback: open system browser
    try:
        import webbrowser
        webbrowser.open(url)
    except Exception:
        print(f"  Open {url} in your browser")
    return False


def is_gui_available() -> bool:
    """Check if we can show a GUI window."""
    if sys.platform == "linux" and not os.environ.get("DISPLAY"):
        return False
    return True
