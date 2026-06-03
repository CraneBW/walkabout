"""Embedded webview window — no external browser needed."""
import sys

def open_window(url: str = "http://localhost:8000"):
    """Open the Walkabout UI in an embedded window. Falls back to browser.

    The caller is responsible for starting the HTTP server *before* calling
    this function. This function only opens a GUI window pointing at the
    running server.
    """
    # Try pywebview first (native window, no external browser)
    try:
        import webview
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
