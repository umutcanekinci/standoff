# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build recipe for the Standoff desktop client.

    pyinstaller standoff.spec --noconfirm

Produces a onedir bundle in ``dist/standoff/`` whose launcher is ``standoff``
(``standoff.exe`` on Windows). onedir is preferred over onefile for a game:
startup is instant (no per-launch temp extraction) and the assets stay
browsable next to the executable.

Entry point is ``__main__.py`` (the desktop client) — not ``main.py``, which is
the Android/buildozer entry point. The dedicated server (``server.py``,
tkinter-based) is desktop-only tooling and is not bundled here; run it from
source alongside the packaged client if you want to host a game.

The ``assets/`` and ``config/`` trees are bundled as data and unpacked next to
the executable (``sys._MEIPASS``); the game resolves them cwd-relative, and
the launcher directory doubles as the cwd when double-clicked from Explorer/
Finder, so the same relative paths resolve as they do from source.
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH)  # noqa: F821 — injected by PyInstaller

# Runtime data trees the game loads by relative path.
datas = [
    (str(ROOT / "assets"), "assets"),
    (str(ROOT / "config"), "config"),
]

a = Analysis(
    ["__main__.py"],
    pathex=[str(ROOT / "src"), str(ROOT / "src" / "pygame_core")],
    binaries=[],
    datas=datas,
    # pytmx's pygame loader is imported through a string in the base tilemap;
    # pin both so the module graph can't miss them.
    hiddenimports=["pytmx", "pytmx.util_pygame"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="standoff",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # windowed app — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="standoff",
)

# On macOS, also wrap the onedir bundle as a .app for a native double-click.
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Standoff.app",
        icon=None,
        bundle_identifier="com.umutcanekinci.standoff",
    )
