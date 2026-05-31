"""Dev harness: 4 game windows in screen quarters, auto-joined into one room.

Why: the game runs fullscreen, so eyeballing online play across clients is awkward.
This launches a local server plus four client windows tiled across the screen and
scripts them through the lobby — window 0 hosts a room, the other three join and
ready up, then the host starts the game — so all four end up in the same match and
you can watch them side by side. Click a window to give it focus, then move with
WASD/arrows; the other windows show that player moving over the network.

    uv run python tools/online_test.py        # start server + 4 windows
    uv run python tools/online_test.py --clients 2   # fewer windows

pygame allows one window per process, so each client is its own subprocess; this
file is both the orchestrator (no args) and the client (--client, used internally).
Windows-only for the window placement (uses user32); the rest is cross-platform.
All of this lives outside src/ and changes no game code.
"""

import sys
import time
import ctypes
import argparse
import faulthandler
import subprocess
import threading
import traceback
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "pygame_core"))

MAP_NAME = "level2"
ROOM_ID = 1  # the server numbers the first created room 1

# Autopilot schedule, in seconds after the shared start time t0. Generous gaps so
# each step's network round-trip lands before the next across all processes.
T_SET_PLAYER = 0.0
T_CREATE_ROOM = 1.5
T_JOIN_ROOM = 3.5
T_READY = 5.0
T_START = 7.0


def _dpi_aware() -> None:
    if sys.platform == "win32":
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


# ── client subprocess ──────────────────────────────────────────────────────────


def run_client(idx: int, role: str, rect: tuple[int, int, int, int], t0: float) -> None:
    # Dump a C-level trace on a hard crash (e.g. SDL) — a plain traceback won't.
    faulthandler.enable()
    _dpi_aware()
    import pygame
    from pygame_core.application import Application
    from app.game import Game
    from util.constants import WINDOW_TITLE, CHARACTER_LIST, Mode
    from net.commands import Command

    # The engine opens fullscreen in Application.__init__; we need windowed so four
    # clients tile on screen. Replace that one method (this process only) with a
    # single windowed SCALED set_mode — calling set_mode a *second* time to leave
    # fullscreen segfaults SDL, so we never go fullscreen at all. SCALED keeps the
    # logical 1920x1080 render and fits it to the smaller window.
    def _windowed(self) -> None:
        self.set_size(self.minimized_size)
        self.window = pygame.display.set_mode(
            self.size, pygame.SCALED | pygame.RESIZABLE
        )

    Application.full_screen = _windowed

    class DevClient(Game):
        """A Game that opens windowed in a screen quarter and scripts itself
        through the lobby into a shared room."""

        def __init__(self) -> None:
            super().__init__()  # now opens windowed via the patch above
            self._dev = SimpleNamespace(phase=0)
            self._place_window()

        def _place_window(self) -> None:
            x, y, w, h = rect
            try:
                pygame.display.set_caption(f"{WINDOW_TITLE} [{role} {idx}]")
                if sys.platform == "win32":
                    # Resize/move the OS window to our quarter; SCALED rescales the
                    # render to fit.
                    hwnd = pygame.display.get_wm_info()["window"]
                    ctypes.windll.user32.MoveWindow(hwnd, x, y, w, h, True)
            except Exception:
                print(f"[client {idx}] window placement failed:", flush=True)
                traceback.print_exc()

        def update(self) -> None:
            super().update()
            self._autopilot()

        def _autopilot(self) -> None:
            d = self._dev
            if not self.client.is_connected:
                return
            elapsed = time.time() - t0

            if d.phase == 0 and elapsed >= T_SET_PLAYER:
                self.mode = Mode.ONLINE
                character = CHARACTER_LIST[idx % len(CHARACTER_LIST)]
                self.lobby.set_player(f"P{idx}", character)
                d.phase = 1
            elif d.phase == 1 and elapsed >= T_CREATE_ROOM:
                if role == "host":
                    self.lobby.create_room(MAP_NAME)
                d.phase = 2
            elif d.phase == 2 and elapsed >= T_JOIN_ROOM:
                if role == "joiner":
                    self.lobby.join_room(ROOM_ID)
                d.phase = 3
            elif d.phase == 3 and elapsed >= T_READY:
                if role == "joiner":
                    self.client.send(Command.GET_READY)
                d.phase = 4
            elif d.phase == 4 and elapsed >= T_START:
                if role == "host":
                    self.client.send(Command.START_GAME)
                d.phase = 5  # done

    try:
        DevClient().run()
    except SystemExit:
        raise  # normal Game.exit()
    except BaseException:
        print(f"[client {idx}] crashed:", flush=True)
        traceback.print_exc()
        raise


# ── orchestrator ─────────────────────────────────────────────────────────────


def _screen_size() -> tuple[int, int]:
    if sys.platform == "win32":
        u = ctypes.windll.user32
        return u.GetSystemMetrics(0), u.GetSystemMetrics(1)
    return 1920, 1080


def _quarters(n: int) -> list[tuple[int, int, int, int]]:
    w, h = _screen_size()
    hw, hh = w // 2, h // 2
    grid = [
        (0, 0, hw, hh),
        (hw, 0, w - hw, hh),
        (0, hh, hw, h - hh),
        (hw, hh, w - hw, h - hh),
    ]
    return grid[:n]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clients", type=int, default=4, choices=range(1, 5))
    parser.add_argument("--client", nargs=7, default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.client:  # spawned subprocess: idx role x y w h t0
        idx, role, x, y, w, h, t0 = args.client
        run_client(int(idx), role, (int(x), int(y), int(w), int(h)), float(t0))
        return

    _dpi_aware()
    from net.game_server import GameServer
    from util.constants import SERVER_ADDR

    server = GameServer(on_status=lambda msg: print(f"[server] {msg}"))
    threading.Thread(target=server.serve, args=(SERVER_ADDR,), daemon=True).start()
    print(f"[server] listening on {SERVER_ADDR}")

    logdir = ROOT / "tools" / "_logs"
    logdir.mkdir(exist_ok=True)
    rects = _quarters(args.clients)
    t0 = time.time() + 5.0  # shared start; leaves time for spawn + connect
    procs, logs = [], []
    for idx, (x, y, w, h) in enumerate(rects):
        role = "host" if idx == 0 else "joiner"
        log = open(logdir / f"client_{idx}.log", "w+", encoding="utf-8")
        logs.append(log)
        procs.append(
            subprocess.Popen(
                [
                    sys.executable,
                    __file__,
                    "--client",
                    str(idx),
                    role,
                    str(x),
                    str(y),
                    str(w),
                    str(h),
                    str(t0),
                ],
                cwd=str(ROOT),
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        )
    print(f"[orchestrator] launched {len(procs)} client(s); close any window to stop.")

    try:
        while any(p.poll() is None for p in procs):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
        # Surface each client's captured output (banner, tracebacks, faulthandler).
        for idx, log in enumerate(logs):
            log.flush()
            log.seek(0)
            print(f"\n===== client {idx} (exit {procs[idx].poll()}) =====")
            print(log.read().rstrip() or "(no output)")
            log.close()


if __name__ == "__main__":
    main()
