"""Launch the Streamlit venue helper without requiring ``uv run``.

When frozen by PyInstaller, this starts Streamlit against the bundled
``app.py`` and opens the browser. Logs and the local profile stay next
to the executable.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def main() -> None:
    os.chdir(app_dir())
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    os.environ.setdefault("STREAMLIT_SERVER_HEADLESS", "true")
    sys.argv = [
        "streamlit",
        "run",
        str(app_dir() / "app.py"),
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--global.developmentMode=false",
    ]
    from streamlit.web.cli import main as streamlit_main

    streamlit_main()


if __name__ == "__main__":
    main()
