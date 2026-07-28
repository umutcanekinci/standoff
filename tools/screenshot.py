"""Capture real in-game screenshots for the README / store pages.

Runs the actual game under SDL's headless `dummy` video driver (so it never
hijacks the desktop), drives the real scenes, and saves the window surface as
PNG. Three shots: the main menu, the character carousel, and an offline
gameplay frame with a staged zombie swarm + a live muzzle flash.

    uv run python tools/screenshot.py            # -> docs/screenshots/*.png

Headless and deterministic: no display, audio, or network needed. The shots are
genuine renders of the live scenes, not mockups.
"""

from __future__ import annotations

import os
import random
import sys
from pathlib import Path

# Headless + silent BEFORE pygame is imported anywhere. dummy video still
# software-renders into the window surface, which is all image.save needs.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "src" / "pygamine"))

import pygame  # noqa: E402
from pygame.math import Vector2 as Vec  # noqa: E402

from app.game import Game  # noqa: E402
from net.player_info import PlayerInfo, MobInfo  # noqa: E402
from util.constants import CHARACTER_LIST, FPS, Mode  # noqa: E402

OUT = _ROOT / "docs" / "screenshots"


def pump(game: Game, frames: int) -> None:
    """Advance the live loop `frames` times in real time (so the offline mob
    spawner and AI integrate against a realistic delta_time)."""
    for _ in range(frames):
        game.clock.tick(FPS)
        game._listen_inputs()
        game.update()
        game.draw()


def save(game: Game, name: str) -> None:
    game.draw()  # one clean frame with no mouse cursor / debug overlay
    path = OUT / name
    pygame.image.save(game.window, str(path))
    print(f"  saved {path.relative_to(_ROOT)}  ({path.stat().st_size // 1024} KB)")


def shoot_main_menu(game: Game) -> None:
    game.lobby.open_panel("main_menu")
    pump(game, 2)
    save(game, "01_main_menu.png")


def shoot_character_select(game: Game) -> None:
    game.lobby.open_panel("player_menu")
    # Land on the robot — a recognisable, photogenic character for the carousel.
    game.lobby.selected_character = CHARACTER_LIST.index("robot")
    game.lobby._refresh_character()
    game.lobby.panel_manager["player_menu"]["name_input"].set_text("PLAYER")
    pump(game, 2)
    save(game, "02_character_select.png")


def shoot_gameplay(game: Game) -> None:
    # Drop into an offline match as the soldier.
    game.player_info = PlayerInfo(name="PLAYER", character_name="solider")
    game.mode = Mode.OFFLINE
    game.lobby.create_room("level2")  # builds the Room + calls Game.start()
    scene = game.gameplay
    assert scene is not None

    # Stage a zombie swarm directly around the player so the frame reads as
    # "under attack" without waiting ~20s for the timed spawner to walk mobs in
    # from 10-20 tiles away. They home on the player from here.
    center = Vec(scene.player.rect.center)
    base = tuple(center)  # mobs home toward this point — the player's position
    random.seed(7)
    count = 12
    for i in range(count):
        ang = -35 + i * (250 / (count - 1))  # a fan across the player's front
        radius = random.randint(150, 300)
        pos = center + Vec(radius, 0).rotate(ang)
        scene.mob_id = i + 1
        scene.spawn_mob(MobInfo(i + 1, scene.game.player_info.room, base, tuple(pos)))

    pump(game, 40)  # let them close in and the sprites animate/orient

    # Aim at the densest cluster and fire, for a live muzzle flash + bullet.
    nearest = min(scene.mobs, key=lambda m: (Vec(m.rect.center) - center).length())
    to = Vec(nearest.rect.center) - Vec(scene.player.rect.center)
    scene.player.angle = -Vec(1, 0).angle_to(to)
    scene.player.is_shooting = True
    scene.shoot()
    pump(game, 1)  # advance the flash/bullet a frame so they're clearly in-flight
    save(game, "03_gameplay.png")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    game = Game()
    game.minimize()  # windowed at full 1920x1080 logical res (no fullscreen grab)
    print(f"Rendering at {game.window.get_size()} -> {OUT.relative_to(_ROOT)}")

    shoot_main_menu(game)
    shoot_character_select(game)
    shoot_gameplay(game)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
