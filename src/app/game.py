import threading
from typing import override

import pygame

from util.constants import (
    WINDOW_TITLE,
    WINDOW_SIZE,
    BACKGROUND_COLORS,
    FPS,
    TILE_WIDTH,
    TILE_HEIGHT,
    AVOID_RADIUS,
    CLIENT_ADDR,
    Green,
    Yellow,
)
from pygame_core.application import Application
from pygame_core.asset_manager import AssetManager
from pygame_core.asset_path import AssetPath
from pygame_core.debug import Debug

from pygame_core.net.transport import BaseClient
from pygame_core.net.protocol import Protocol, PickleCodec
from app.lobby_scene import LobbyScene
from gameplay.map import Map
from gameplay.camera import Camera
from pygame_core.spatial_grid import SpatialGrid
from gameplay.player import Players
from gameplay.mob import Mobs
from net.commands import Command


class Game(Application):
    def __init__(self) -> None:
        super().__init__(WINDOW_SIZE, WINDOW_TITLE, FPS)

        self.assets = AssetManager()
        self.assets.load_manifest("config/assets.yaml")
        missing = self.assets.validate()
        if missing:
            raise FileNotFoundError("Missing assets:\n  " + "\n  ".join(missing))

        self._debug_text = ""
        self.debug_font = pygame.font.Font(None, 25)

        self.window.fill(BACKGROUND_COLORS["menu"])
        pygame.display.update()

        self.gun_flashes = [self.assets.image_path(f"muzzle_{i + 1}") for i in range(5)]

        # Session state shared across scenes.
        self.is_game_started = False
        self.mode = None
        self.player_info = None

        self.walls = []

        # The lobby owns all menu/panel state; Game forwards the loop to it while
        # not in-world. Gameplay still lives on Game (extracted in a later step).
        self.lobby = LobbyScene(self)

        # Incoming server message -> handler. Mirrors the server's _handlers dict;
        # both dispatch on the shared net.commands.Command names. Lobby-phase
        # messages are routed to self.lobby; gameplay-phase ones stay on Game.
        self._message_handlers = {
            Command.SET_PLAYER_COUNT: self.lobby.update_player_count,
            Command.UPDATE_ROOM: self._on_update_room,
            Command.LEAVE_ROOM: self._on_leave_room,
            Command.START_GAME: self._on_start_game,
            Command.UPDATE_PLAYER: self._on_update_player,
            Command.SHOOT: self._on_shoot,
            Command.SPAWN: self.spawn_mob,
            Command.DISCONNECT: self._on_disconnect_message,
        }

        self.start_client()
        self.lobby.open_panel("main_menu")

    # Networking / game flow (called by the lobby + client callbacks)

    def debug_log(self, text):
        # Kept for the network client, which logs connection status here.
        self._debug_text = str(text)

    def start_client(self) -> None:
        # The transport client is game-unaware: it just pumps decoded messages
        # to get_data and connection status to debug_log. Connect off-thread so a
        # slow/refused connect never blocks the game loop.
        # Must use the same codec as the server (GameServer uses pickle, since it
        # sends whole PlayerInfo/Room/MobInfo objects). Keep these two in lockstep.
        self.client = BaseClient(
            on_message=self.get_data,
            on_disconnect=lambda: self.debug_log("[CLIENT] connection lost"),
            on_status=self.debug_log,
            protocol=Protocol(PickleCodec()),
        )
        threading.Thread(
            target=self.client.connect, args=(CLIENT_ADDR,), daemon=True
        ).start()

    def start(self):
        self.walls = []
        self.map = Map(
            self, AssetPath(self.player_info.room.map_name, "maps", "tmx"), 2
        )
        self.map.render()
        # Walls are static, so grid them once. Mobs query this for collision.
        # of_static buckets each wall into every cell it overlaps (walls can be
        # bigger than a cell) so queries on those cells don't miss it.
        self.wall_grid = SpatialGrid.of_static(self.walls, max(TILE_WIDTH, TILE_HEIGHT))
        self.players = Players(self)
        self.mobs = Mobs(self)
        self.mob_grid = SpatialGrid(AVOID_RADIUS)
        self.camera = Camera(self.size, self.map)
        self.bullets = []
        self.effects = []

        self.player = self.players.add_player(self.player_info, Green)

        if self.mode == "online":
            for player in self.player_info.room:
                if not player.id == self.player.id:
                    self.players.add_player(player, Yellow)

        elif self.mode == "offline":
            thread = threading.Thread(
                target=self.player_info.room.handle_spawner, args=(self.spawn_mob,)
            )
            thread.start()

        self.is_game_started = True

    def update_player_rect(self, player_id, delta: tuple):
        player = self.players.get_player_with_id(player_id)
        if player:  # may have just left; server can still relay stale updates
            player.delta = delta

    def update_player_angle(self, player_id, angle):
        player = self.players.get_player_with_id(player_id)
        if player:
            player.angle = angle

    def shoot(self):
        if self.player.is_shooting:
            if self.mode == "online":
                self.client.send(Command.SHOOT, self.player.id)
            elif self.mode == "offline":
                self.player.shoot()

    def remove_player(self, player_id):
        if self.is_game_started:
            player = self.players.get_player_with_id(player_id)
            if player:
                self.players.remove(player)

    def spawn_mob(self, mob_info):
        self.mobs.add_mob(mob_info)

    def get_data(self, data) -> None:
        if not data:
            return
        command = data["command"]
        value = data.get("value")
        handler = self._message_handlers.get(command)
        if handler:
            handler(value)

    def _on_update_room(self, value) -> None:
        if value:
            self.player_info = value
            self.lobby.update_room()

    def _on_start_game(self, _value) -> None:
        self.start()

    def _on_leave_room(self, _value) -> None:
        self.lobby.open_panel("game_type_menu")

    def _on_update_player(self, value) -> None:
        self.update_player_rect(value[0], value[1])
        self.update_player_angle(value[0], value[2])

    def _on_shoot(self, value) -> None:
        player = self.players.get_player_with_id(value)
        if player:
            player.shoot()

    def _on_disconnect_message(self, value) -> None:
        if getattr(self, "player_info", None) and self.player_info.id == value:
            # Server told us we're gone: drop the socket first so exit() doesn't
            # try to send a redundant !DISCONNECT back.
            self.client.disconnect()
            self.exit()
        else:
            self.remove_player(value)

    # Application overrides

    @override
    def _handle_core_event(self, event: pygame.event.Event) -> None:
        # Esc/QUIT drive menu/in-game back-navigation (not a hard exit), matching the
        # original game; keep F1 (debug) and F11 (fullscreen) from the base.
        if event.type == pygame.QUIT or (
            event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
        ):
            self._handle_back()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F1:
                self._is_in_debug_mode = not self._is_in_debug_mode
            elif event.key == pygame.K_F11:
                self.minimize() if self.size != self.minimized_size else self.full_screen()

    def _handle_back(self) -> None:
        if self.is_game_started:
            self.is_game_started = False
            self.lobby.open_panel("main_menu")
        else:
            self.lobby.handle_back()

    @override
    def handle_event(self, event: pygame.event.Event) -> None:
        if self.is_game_started:
            self.player.handle_events(event)
        else:
            self.lobby.handle_event(event)

    @override
    def update(self) -> None:
        # Compat attributes the gameplay/networking code reads via self.game.*
        self.delta_time = self.clock.get_time() * 0.001 * FPS
        self.mouse_position = self.mouse.position

        if self.is_game_started:
            self._update_gameplay()
        else:
            self.lobby.update()

    def _update_gameplay(self) -> None:
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

        if hasattr(self, "player"):
            self.player.rotate_to_mouse()
            self.player.update_movement()

        if self.mode == "online":
            self.client.send(
                Command.UPDATE_PLAYER,
                [self.player_info.id, self.player.delta, self.player.angle],
            )
        elif self.mode == "offline":
            self.player_info.room.update(self.spawn_mob)

    @override
    def draw(self) -> None:
        if self.is_game_started:
            self._draw_gameplay()
        else:
            self.lobby.draw()

    def _draw_gameplay(self) -> None:
        self.camera.draw(self.window, [self.map])
        self.camera.draw(self.window, self.mobs)
        self.camera.draw(self.window, self.players)
        self.camera.draw(self.window, self.bullets)
        self.camera.draw(self.window, self.effects)

        for mob in self.mobs:
            mob.draw_name(self.window, self.camera)
            mob.draw_health_bar(self.window, self.camera)
            if self._is_in_debug_mode:
                mob.draw_rects(self.window, self.camera)

        for player in self.players:
            player.draw_name(self.window, self.camera)
            player.draw_health_bar(self.window, self.camera)
            if self._is_in_debug_mode:
                player.draw_rects(self.window, self.camera)

        if self._is_in_debug_mode:
            for wall in self.walls:
                wall.draw_rect(self.window)

    @override
    def draw_debug(self) -> None:
        Debug.draw(
            self.window,
            self.debug_font,
            [
                (
                    "Application",
                    {
                        "FPS": round(self.clock.get_fps()),
                        "Mouse": self.mouse.position,
                        "Game started": self.is_game_started,
                    },
                ),
                ("Client", {"Log": self._debug_text}),
            ],
        )

    @override
    def exit(self) -> None:
        # Best-effort notify the server, then always tear down the socket and exit -
        # don't depend on the server echoing !DISCONNECT back to close the window.
        if self.client.is_connected:
            self.client.send(Command.DISCONNECT)
        self.client.disconnect()
        super().exit()
