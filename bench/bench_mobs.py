"""Headless capacity benchmark: how many zombies before we miss 60 FPS?

    uv run python bench/bench_mobs.py

Spawns increasing numbers of mobs and times one frame of UPDATE (the AI/physics
simulation, which includes the per-mob sprite rotation) and DRAW (blits to an
offscreen surface). No window or assets are needed — image loading is stubbed.

The numbers are MACHINE-RELATIVE: use them to compare before/after an
optimization on the same machine, not as an absolute promise of player FPS.
"""

import os
import sys
import time
import random
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "pygame_core"))

import pygame

pygame.init()

# Stub image loading so we need no assets/disk. entity.py and game_sprite.py bind
# `load_image` at import, so patch it on those modules (resolved at call time).
import gameplay.entity as _entity_mod
import gameplay.game_sprite as _gs_mod


def _fake_load_image(path, size=None):
    surf = pygame.Surface((64, 64), pygame.SRCALPHA)
    surf.fill((0, 180, 0))
    return surf


_entity_mod.load_image = _fake_load_image
_gs_mod.load_image = _fake_load_image

from util.constants import WINDOW_SIZE, FPS, MOB_MAX_HP, AVOID_RADIUS  # noqa: E402
from gameplay.camera import Camera  # noqa: E402
from gameplay.mob import Mobs  # noqa: E402
from gameplay.spatial_grid import SpatialGrid  # noqa: E402

FRAME_BUDGET_MS = 1000.0 / FPS  # 16.67 ms for 60 FPS
MAP_SIZE = (4000, 4000)
COUNTS = [50, 100, 200, 400, 800, 1600, 3200]
WARMUP = 5
FRAMES = 30


class _FakePlayer:
    def __init__(self, center):
        self.rect = pygame.Rect(0, 0, 40, 40)
        self.rect.center = center
        self.alive = True

    def lose_hp(self, value):
        pass

    def apply_knockback(self, direction, distance):
        pass


class _FakeMap:
    def __init__(self, size):
        self.rect = pygame.Rect(0, 0, *size)


class _FakeAssets:
    def image_path(self, name):
        return name  # value is ignored — load_image is stubbed


class _FakeMobInfo:
    def __init__(self, id, position, target_base):
        self.id = id
        self.position = position
        self.size = 1
        self.target_base = target_base


class _FakeGame:
    """Provides exactly the attributes Mob/Entity read via self.game.*"""

    def __init__(self):
        self.assets = _FakeAssets()
        self.map = _FakeMap(MAP_SIZE)
        self.camera = Camera(WINDOW_SIZE, self.map)
        center = (MAP_SIZE[0] // 2, MAP_SIZE[1] // 2)
        self.players = [_FakePlayer(center)]
        self.walls = []
        self.mobs = Mobs(self)
        self.delta_time = 1.0  # ~1 frame at 60 FPS


def _build_game(n_mobs: int) -> _FakeGame:
    random.seed(1234)  # deterministic layout across runs
    game = _FakeGame()
    base = (MAP_SIZE[0] // 2, MAP_SIZE[1] // 2)
    for i in range(n_mobs):
        pos = (random.randint(0, MAP_SIZE[0]), random.randint(0, MAP_SIZE[1]))
        game.mobs.add_mob(_FakeMobInfo(i, pos, base))
    for mob in game.mobs:
        mob.set_hp(MOB_MAX_HP - 10)  # so health bars render in the draw pass
    return game


def _step_update(game: _FakeGame) -> None:
    # Mirror Game.update: rebuild the mob grid from this frame's positions first.
    game.mob_grid = SpatialGrid.of(game.mobs, AVOID_RADIUS)
    for mob in game.mobs:
        mob.update()
    game.mobs[:] = [m for m in game.mobs if m.alive]


def _step_draw(game: _FakeGame, window: pygame.Surface) -> None:
    game.camera.follow(game.players[0].rect)
    game.camera.draw(window, game.mobs)
    for mob in game.mobs:
        mob.draw_name(window, game.camera)
        mob.draw_health_bar(window, game.camera)


def _time_phase(fn, *args) -> float:
    """Average wall-clock ms for `fn` over FRAMES, after WARMUP frames."""
    for _ in range(WARMUP):
        fn(*args)
    start = time.perf_counter()
    for _ in range(FRAMES):
        fn(*args)
    return (time.perf_counter() - start) / FRAMES * 1000.0


def main() -> None:
    window = pygame.Surface(WINDOW_SIZE)
    print(f"Frame budget for {FPS} FPS: {FRAME_BUDGET_MS:.2f} ms/frame\n")
    header = f"{'mobs':>6} | {'update ms':>10} | {'draw ms':>9} | {'total ms':>9} | {'~FPS':>6} | 60?"
    print(header)
    print("-" * len(header))

    for n in COUNTS:
        game = _build_game(n)
        update_ms = _time_phase(_step_update, game)
        # Rebuild so draw isn't measured on a board the update loop mutated.
        game = _build_game(n)
        draw_ms = _time_phase(_step_draw, game, window)
        total = update_ms + draw_ms
        fps = 1000.0 / total if total else float("inf")
        ok = "ok" if total <= FRAME_BUDGET_MS else "MISS"
        print(
            f"{n:>6} | {update_ms:>10.2f} | {draw_ms:>9.2f} | "
            f"{total:>9.2f} | {fps:>6.0f} | {ok}"
        )


if __name__ == "__main__":
    main()
