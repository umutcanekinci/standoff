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
    RESPAWN_DELAY,
    Mode,
    Red,
    Green,
    Yellow,
    White,
    Gray,
)
import pygame
from pygame.math import Vector2 as Vec

from pygame_core.asset_path import AssetPath
from pygame_core.spatial_grid import SpatialGrid
from pygame_core.panel_manager import PanelManager
from pygame_core.ecs.components.transform import Transform
from pygame_core.ui_widgets.text_object import TextObject

from app.scene import Scene
from gameplay.map import Map
from gameplay.camera import Camera
from gameplay.player import Players
from gameplay.controls import make_controls
from gameplay.mob import Mobs
from net.commands import Command
from ui.widgets import ShapeButton

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

        # Where the local player's move/aim/fire intent comes from: keyboard+mouse
        # on desktop, on-screen joystick+fire on Android (chosen by make_controls).
        self.controls = make_controls(
            size=self.game.size,
            assets=self.game.assets,
            get_keys=lambda: self.game.keys,
            get_mouse_pos=lambda: self.game.mouse.position,
        )
        self.player.controls = self.controls

        if game.mode == Mode.ONLINE:
            for player in game.player_info.room:
                if player.id != self.player.id:
                    self.players.add_player(player, Yellow)

        elif game.mode == Mode.OFFLINE:
            threading.Thread(
                target=game.player_info.room.handle_spawner, args=(self.spawn_mob,)
            ).start()

        # Death/spectator state. _was_alive tracks the alive->dead transition;
        # _view_target is whose view the camera shows (self while alive, a living
        # team-mate while spectating).
        self._was_alive = True
        self._showing_death_panel = False
        self._spectate_index = 0
        self._view_target = self.player
        self._death_time = 0  # ticks at last death; gates the respawn timer
        self._respawn_secs_shown = -1  # last countdown second drawn on the button
        # Authoritative alive state per player id (local from self.player, remotes
        # from UPDATE_PLAYER) — drives which roster entries are greyed.
        self._alive_by_id = {info.id: True for info in game.player_info.room}
        self._build_death_ui()
        self._build_roster()

    def _build_death_ui(self) -> None:
        # A grey wash + "YOU DIED" + buttons, drawn over the live game while dead.
        # Positioned by fraction of the logical size so it fits any window
        # (fullscreen or the tiled test harness).
        screen = Transform((0, 0), self.game.size)
        w, h = self.game.size
        # Light grey overlay so the dead player's whole view reads as "downed".
        self._tint = pygame.Surface((w, h), pygame.SRCALPHA)
        self._tint.fill((120, 120, 120, 110))
        self._spectate_font = pygame.font.Font(None, max(20, h // 24))

        self._death_panel = PanelManager(starting_tab="death")
        self._death_panel.add_object(
            "death",
            "title",
            TextObject(
                screen,
                ("CENTER", int(h * 0.28)),
                "YOU DIED",
                pygame.font.Font(None, max(36, h // 12)),
                Red,
            ),
        )

        def button(label, y):
            return ShapeButton(
                screen,
                ("CENTER", int(h * y)),
                (min(360, w - 40), 60),
                normal_color=Green,
                hover_color=Red,
                text=label,
                text_size=32,
            )

        self._respawn_button = button("RESPAWN", 0.42)
        self._spectate_button = button("SPECTATE", 0.55)
        self._room_button = button("RETURN TO ROOM", 0.68)
        self._death_panel.add_object("death", "respawn", self._respawn_button)
        self._death_panel.add_object("death", "spectate", self._spectate_button)
        self._death_panel.add_object("death", "return", self._room_button)

    @staticmethod
    def _greyscale(surface):
        try:
            return pygame.transform.grayscale(surface)
        except (AttributeError, ValueError, pygame.error):
            faded = surface.copy()  # fallback: darken if grayscale isn't available
            faded.fill((110, 110, 110, 255), special_flags=pygame.BLEND_RGB_MULT)
            return faded

    def _build_roster(self) -> None:
        # Top-right list of everyone in the room: a small character icon + name.
        # Built once (room membership is fixed for the match). Each entry keeps an
        # alive and a greyed variant; _draw_roster picks per the live alive state.
        h = self.game.size[1]
        icon_size = max(28, h // 18)
        font = pygame.font.Font(None, max(18, h // 28))
        self._roster = []
        for info in self.game.player_info.room:
            image = self.game.assets.get_image(f"char_{info.character_name}_idle")
            icon = pygame.transform.smoothscale(image, (icon_size, icon_size))
            self._roster.append(
                {
                    "id": info.id,
                    "icon": icon,
                    "icon_dead": self._greyscale(icon),
                    "name": font.render(info.name, True, White),
                    "name_dead": font.render(info.name, True, Gray),
                }
            )

    def _draw_roster(self, window) -> None:
        right = self.game.size[0] - 12
        y = 12
        for row in self._roster:
            alive = self._alive_by_id.get(row["id"], True)
            icon = row["icon"] if alive else row["icon_dead"]
            name = row["name"] if alive else row["name_dead"]
            window.blit(icon, (right - icon.get_width(), y))
            window.blit(
                name,
                (
                    right - icon.get_width() - 8 - name.get_width(),
                    y + (icon.get_height() - name.get_height()) // 2,
                ),
            )
            y += icon.get_height() + 6

    # World surface read by entities (see module docstring).

    @property
    def assets(self):
        return self.game.assets

    @property
    def keys(self):
        return self.game.keys

    # Loop hooks (driven by Game while this scene is active)

    def handle_event(self, event) -> None:
        if self.player.alive:
            self.controls.handle_event(event)
        elif self._showing_death_panel:
            self._handle_death_panel(event)
        else:
            self._handle_spectate(event)

    def update(self) -> None:
        self.delta_time = self.game.clock.get_time() * 0.001 * FPS
        self.mouse_position = self.game.mouse.position

        if self._was_alive and not self.player.alive:
            # Just died: surface the death panel and start the respawn cooldown.
            self._showing_death_panel = True
            self._spectate_index = 0
            self._death_time = pygame.time.get_ticks()
            self._respawn_secs_shown = -1
        self._was_alive = self.player.alive
        self._alive_by_id[self.game.player_info.id] = self.player.alive  # for roster

        # Rebuild the mob grid from this frame's positions before anyone moves;
        # mob avoidance queries it instead of scanning every other mob.
        self.mob_grid = SpatialGrid.of(self.mobs, AVOID_RADIUS)
        for entity in (*self.players, *self.mobs, *self.bullets, *self.effects):
            entity.update()
        # Drop only the local player on death (they switch to spectate); keep
        # remote corpses in the list so they respawn in place and so set_player_alive
        # can keep them marked dead (mobs ignore them, can't be spectated).
        self.players[:] = [p for p in self.players if p.alive or not p.is_local]
        self.mobs[:] = [m for m in self.mobs if m.alive]
        self.bullets[:] = [b for b in self.bullets if b.alive]
        self.effects[:] = [e for e in self.effects if e.alive]

        if self.player.alive:
            self.camera.follow(self.player.rect)
            self.player.is_shooting = self.controls.is_firing()
            self.shoot()
            self.player.aim()
            self.player.update_movement()
        else:
            self._update_death_ui()  # respawn-timer button state
            self._update_spectate()  # dead: ride a team-mate's view

        if self.game.mode == Mode.ONLINE:
            # Send our absolute position (not a delta) so a dropped packet can't
            # permanently desync us on the other clients — each update is truth.
            # alive lets the server stop steering mobs toward us once we die.
            self.game.client.send(
                Command.UPDATE_PLAYER,
                [
                    self.game.player_info.id,
                    self.player.rect.center,
                    self.player.angle,
                    self.player.alive,
                ],
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

        if self.player.alive:
            self.controls.draw(window)  # touch HUD (no-op on desktop); hidden when dead
        else:
            self._draw_death_ui(window)

        self._draw_roster(window)  # always on top, readable in any state

    # Death / spectator

    def _respawn_remaining_ms(self) -> int:
        return max(0, RESPAWN_DELAY - (pygame.time.get_ticks() - self._death_time))

    def _update_death_ui(self) -> None:
        # Gate the respawn button behind the cooldown and show the countdown.
        remaining = self._respawn_remaining_ms()
        ready = remaining == 0
        self._respawn_button.set_enabled(ready)
        secs = 0 if ready else remaining // 1000 + 1
        if secs != self._respawn_secs_shown:
            self._respawn_secs_shown = secs
            self._respawn_button.set_label("RESPAWN" if ready else f"RESPAWN ({secs})")

    def _living_players(self) -> list:
        return [p for p in self.players if p.alive]

    def _update_spectate(self) -> None:
        # Follow a living team-mate (cycled by _handle_spectate); if everyone is
        # down, sit on our own corpse.
        living = self._living_players()
        if living:
            self._spectate_index %= len(living)
            self._view_target = living[self._spectate_index]
        else:
            self._view_target = self.player
        self.camera.follow(self._view_target.rect)

    def _handle_death_panel(self, event) -> None:
        mouse = self.game.mouse.position
        self._death_panel.handle_event(event, mouse)
        if self._respawn_button.is_clicked(event, mouse):
            self._respawn()
        elif self._spectate_button.is_clicked(event, mouse):
            self._showing_death_panel = False  # dismiss panel, watch the action
        elif self._room_button.is_clicked(event, mouse):
            self._return_to_room()

    def _handle_spectate(self, event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        living = self._living_players()
        if event.key in (pygame.K_LEFT, pygame.K_a) and living:
            self._spectate_index = (self._spectate_index - 1) % len(living)
        elif event.key in (pygame.K_RIGHT, pygame.K_d) and living:
            self._spectate_index = (self._spectate_index + 1) % len(living)
        elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
            self._respawn()
        elif event.key == pygame.K_r:
            self._return_to_room()

    def _respawn(self) -> None:
        # Revive at our spawn base, full HP, motion cleared, and rejoin the active
        # players list (we were pruned on death). Online, the next UPDATE_PLAYER
        # carries alive=True so the server re-targets mobs and team-mates see us.
        if self._respawn_remaining_ms() > 0:
            return  # still on cooldown
        player = self.player
        player.alive = True
        player.set_hp(player.max_hp)
        player.is_shooting = False
        player.velocity = Vec()
        player.delta = Vec()
        player.knockback = Vec()
        player.update_position(self.map.spawn_points[self.game.player_info.base_number])
        if player not in self.players:
            self.players.append(player)
        self._showing_death_panel = False
        self._was_alive = True

    def _return_to_room(self) -> None:
        # Leave the in-world view for the room screen; the room is still ours.
        self.game.gameplay = None
        self.game.active_scene = self.game.lobby
        self.game.lobby.update_room()

    def _draw_death_ui(self, window) -> None:
        window.blit(self._tint, (0, 0))  # grey wash whenever dead
        if self._showing_death_panel:
            self._death_panel.draw(window)
        else:
            name = getattr(self._view_target, "name", "")
            remaining = self._respawn_remaining_ms()
            respawn = (
                "respawn" if remaining == 0 else f"respawn ({remaining // 1000 + 1})"
            )
            hint = (
                f"Spectating {name}    Left/Right: switch    "
                f"Space: {respawn}    R: room    Esc: menu"
            )
            surface = self._spectate_font.render(hint, True, White)
            window.blit(
                surface, (self.game.size[0] // 2 - surface.get_width() // 2, 18)
            )

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

    def hit_mob(self, mob, damage) -> None:
        # Online the server owns mob HP, so just report the hit; offline we apply
        # it locally (and keep the old hit-stun).
        if self.game.mode == Mode.ONLINE:
            self.game.client.send(Command.HIT_MOB, (mob.id, damage))
        else:
            mob.velocity = Vec(0, 0)
            mob.lose_hp(damage)

    def update_mobs(self, mobs) -> None:
        for mob_id, position, hp in mobs:
            mob = self.mobs.get_mob_from_id(mob_id)
            if mob:  # ignore ids we've already killed locally
                mob.target_position = Vec(position)
                mob.set_hp(hp)  # server only sends living mobs, so hp > 0 (no kill)

    def kill_mob(self, mob_id) -> None:
        mob = self.mobs.get_mob_from_id(mob_id)
        if mob:
            mob.kill()  # alive = False; pruned from the list next frame

    def update_player_position(self, player_id, position: tuple) -> None:
        player = self.players.get_player_with_id(player_id)
        if player:  # may have just left; server can still relay stale updates
            player.target_position = Vec(position)

    def update_player_angle(self, player_id, angle) -> None:
        player = self.players.get_player_with_id(player_id)
        if player:
            player.angle = angle

    def set_player_alive(self, player_id, alive) -> None:
        # Authoritative alive from a player's own client; greys its roster entry
        # and marks the remote Player so mobs stop attacking it and it drops out
        # of the spectate rotation (the local player is driven by its own HP).
        self._alive_by_id[player_id] = alive
        player = self.players.get_player_with_id(player_id)
        if player and not player.is_local:
            player.set_alive(alive)  # also swaps to a grey corpse / back on respawn

    def remove_player(self, player_id) -> None:
        player = self.players.get_player_with_id(player_id)
        if player:
            self.players.remove(player)
