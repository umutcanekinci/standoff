"""In-world phase: the playable arena, entities, camera, and game loop.

This scene IS the "world" that entities depend on: Player, Mob, Bullet,
MuzzleFlash, Map and Wall read their surroundings (walls, players, mobs,
delta_time, camera, the mob grid, ...) off the scene passed to them, instead
of reaching into the whole Game. That narrow surface is what lets an entity be
exercised against a stand-in (see bench/bench_mobs.py) without a full Game.

Shared session state (client, player_info, mode, window, clock, keys) still
lives on Game and is read through self.game.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from util.constants import (
    FPS,
    TILE_WIDTH,
    TILE_HEIGHT,
    AVOID_RADIUS,
    Mode,
    Green,
    Yellow,
)
from pygame.math import Vector2 as Vec

from pygame_core.asset_path import AssetPath
from pygame_core.spatial_grid import SpatialGrid

from app.scene import Scene
from gameplay.map import Map
from gameplay.camera import Camera
from gameplay.player import Players
from gameplay.mob import Mobs
from net.commands import Command

if TYPE_CHECKING:
    from app.game import Game


class GameplayScene(Scene):
    def __init__(self, game: "Game") -> None:
        super().__init__(game)

        self.gun_flashes = [game.assets.image_path(f"muzzle_{i + 1}") for i in range(5)]

        # Per-frame inputs, refreshed at the top of update(); entities read these.
        self.delta_time = 0.0
        self.mouse_position = (0, 0)

        # walls must exist before Map builds Obstacles into it.
        self.walls = []
        self.map = Map(
            self, AssetPath(game.player_info.room.map_name, "maps", "tmx"), 2
        )
        self.map.render()
        # Walls are static, so grid them once. Mobs query this for collision.
        # of_static buckets each wall into every cell it overlaps (walls can be
        # bigger than a cell) so queries on those cells don't miss it.
        self.wall_grid = SpatialGrid.of_static(self.walls, max(TILE_WIDTH, TILE_HEIGHT))
        self.players = Players(self)
        self.mobs = Mobs(self)
        self.mob_grid = SpatialGrid(AVOID_RADIUS)
        self.camera = Camera(game.size, self.map)
        self.bullets = []
        self.effects = []

        self.player = self.players.add_player(game.player_info, Green)
        self.player.is_local = True  # input-driven; the rest follow the network

        if game.mode == Mode.ONLINE:
            for player in game.player_info.room:
                if player.id != self.player.id:
                    self.players.add_player(player, Yellow)

        elif game.mode == Mode.OFFLINE:
            threading.Thread(
                target=game.player_info.room.handle_spawner, args=(self.spawn_mob,)
            ).start()

    # World surface read by entities (see module docstring).

    @property
    def assets(self):
        return self.game.assets

    @property
    def keys(self):
        return self.game.keys

    # Loop hooks (driven by Game while this scene is active)

    def handle_event(self, event) -> None:
        self.player.handle_events(event)

    def update(self) -> None:
        self.delta_time = self.game.clock.get_time() * 0.001 * FPS
        self.mouse_position = self.game.mouse.position

        # Rebuild the mob grid from this frame's positions before anyone moves;
        # mob avoidance queries it instead of scanning every other mob.
        self.mob_grid = SpatialGrid.of(self.mobs, AVOID_RADIUS)
        for entity in (*self.players, *self.mobs, *self.bullets, *self.effects):
            entity.update()
        self.players[:] = [p for p in self.players if p.alive]
        self.mobs[:] = [m for m in self.mobs if m.alive]
        self.bullets[:] = [b for b in self.bullets if b.alive]
        self.effects[:] = [e for e in self.effects if e.alive]

        self.camera.follow(self.player.rect)
        self.shoot()
        self.player.rotate_to_mouse()
        self.player.update_movement()

        if self.game.mode == Mode.ONLINE:
            # Send our absolute position (not a delta) so a dropped packet can't
            # permanently desync us on the other clients — each update is truth.
            self.game.client.send(
                Command.UPDATE_PLAYER,
                [self.game.player_info.id, self.player.rect.center, self.player.angle],
            )
        elif self.game.mode == Mode.OFFLINE:
            self.game.player_info.room.update(self.spawn_mob)

    def draw(self) -> None:
        window, camera = self.game.window, self.camera
        debug = self.game._is_in_debug_mode

        camera.draw(window, [self.map])
        camera.draw(window, self.mobs)
        camera.draw(window, self.players)
        camera.draw(window, self.bullets)
        camera.draw(window, self.effects)

        for mob in self.mobs:
            mob.draw_name(window, camera)
            mob.draw_health_bar(window, camera)
            if debug:
                mob.draw_rects(window, camera)

        for player in self.players:
            player.draw_name(window, camera)
            player.draw_health_bar(window, camera)
            if debug:
                player.draw_rects(window, camera)

        if debug:
            for wall in self.walls:
                wall.draw_rect(window)

    # Gameplay actions (called by the loop + Game's network message router)

    def shoot(self) -> None:
        if self.player.is_shooting:
            if self.game.mode == Mode.ONLINE:
                self.game.client.send(Command.SHOOT, self.player.id)
            elif self.game.mode == Mode.OFFLINE:
                self.player.shoot()

    def spawn_mob(self, mob_info) -> None:
        mob = self.mobs.add_mob(mob_info)
        # Online, the server drives mob movement and we follow; offline the mob
        # runs its own AI.
        mob.is_network = self.game.mode == Mode.ONLINE

    def update_mobs(self, positions) -> None:
        for mob_id, position in positions:
            mob = self.mobs.get_mob_from_id(mob_id)
            if mob:  # ignore ids we've already killed locally
                mob.target_position = Vec(position)

    def update_player_position(self, player_id, position: tuple) -> None:
        player = self.players.get_player_with_id(player_id)
        if player:  # may have just left; server can still relay stale updates
            player.target_position = Vec(position)

    def update_player_angle(self, player_id, angle) -> None:
        player = self.players.get_player_with_id(player_id)
        if player:
            player.angle = angle

    def remove_player(self, player_id) -> None:
        player = self.players.get_player_with_id(player_id)
        if player:
            self.players.remove(player)
