import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "src" / "pygame_core"))

from net.server import Application

if __name__ == "__main__":
    Application().Start()
