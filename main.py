"""Packaged / Android entry point — launches the game client.

buildozer and python-for-android run *main.py* from the app root. This mirrors
__main__.py (path setup, then Game().run()) and deliberately imports only the
client (app.game.Game) — never app.server_app — so tkinter is never pulled into
the APK. Touch controls switch on automatically: make_controls() detects Android
via the ANDROID_ARGUMENT env var that python-for-android sets.

Desktop launch still uses __main__.py (`python __main__.py`); this file exists
for the packager.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "src" / "pygamine"))

from app.game import Game

if __name__ == "__main__":
    Game().run()
