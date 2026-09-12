# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

APP_NAME = "深大场馆预约"
datas = collect_data_files("streamlit") + copy_metadata("streamlit") + copy_metadata("altair")
datas += [
    ("app.py", "."),
    ("apis.py", "."),
    ("settings.py", "."),
]
hiddenimports = collect_submodules("streamlit") + [
    "streamlit.web.cli",
    "streamlit.runtime.scriptrunner",
    "streamlit.runtime.scriptrunner.magic_funcs",
    "altair",
    "pyarrow",
    "pandas",
    "numpy",
    "requests",
]

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "openai", "openpyxl", "tqdm"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name=f"{APP_NAME}.app",
        icon=None,
        bundle_identifier="com.szu.venuehelper",
        info_plist={
            "CFBundleName": APP_NAME,
            "CFBundleDisplayName": APP_NAME,
            "NSHighResolutionCapable": True,
        },
    )
