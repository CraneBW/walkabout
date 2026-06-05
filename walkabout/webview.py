"""Embedded webview window — no external browser needed."""
import os
import sys


def open_window(url: str = "http://localhost:8000"):
    """Open the Walkabout UI in an embedded window. Falls back to browser.

    The caller is responsible for starting the HTTP server *before* calling
    this function. This function only opens a GUI window pointing at the
    running server.
    """
    # Try pywebview first (native window, no external browser)
    # Note: catch Exception (not just ImportError) because pywebview's qtpy
    # dependency raises QtBindingsNotFoundError when qtpy is installed but
    # no Qt backend (PyQt5/PySide6) is available.
    # Also suppress stderr during the attempt to hide pywebview's internal
    # "[pywebview] QT cannot be loaded" noise.
    old_stderr = sys.stderr
    try:
        # Redirect stderr to /dev/null to suppress pywebview/qtpy noise
        with open(os.devnull, 'w') as devnull:
            sys.stderr = devnull

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
    except Exception:
        pass
    finally:
        sys.stderr = old_stderr

    # Try PyQt5/PySide6 as fallback
    try:
        from PyQt5 import QtCore, QtWebEngineWidgets, QtWidgets
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
    if sys.platform == "linux" and not (
        os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    ):
        return False
    return True
