"""Launch the Streamlit venue helper without requiring ``uv run``.

When frozen by PyInstaller, this starts Streamlit against the bundled
``app.py`` and opens the browser. Logs and the local profile stay next
to the executable.
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def disable_quick_edit() -> None:
    """Keep a console click from pausing the packaged Windows process."""
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-10)
        mode = ctypes.c_uint()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value & ~0x0040)
    except Exception:
        pass


def wait_for_port(port: int, timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.4):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def open_browser(port: int) -> None:
    if wait_for_port(port):
        webbrowser.open(f"http://localhost:{port}")


def main() -> None:
    disable_quick_edit()
    os.chdir(app_dir())
    port = os.environ.get("STREAMLIT_SERVER_PORT", "8501")
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    threading.Thread(target=open_browser, args=(int(port),), daemon=True).start()
    sys.argv = [
        "streamlit",
        "run",
        str(app_dir() / "app.py"),
        f"--server.port={port}",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--global.developmentMode=false",
    ]
    from streamlit.web.cli import main as streamlit_main

    streamlit_main()


if __name__ == "__main__":
    main()
