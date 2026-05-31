import threading
from typing import override

import pygame

from util.constants import (
    WINDOW_TITLE,
    WINDOW_SIZE,
    BACKGROUND_COLORS,
    FPS,
    CLIENT_ADDR,
    Mode,
)
from pygame_core.application import Application
from pygame_core.asset_manager import AssetManager
from pygame_core.debug import Debug

from pygame_core.net.transport import BaseClient
from pygame_core.net.protocol import Protocol, PickleCodec
from app.lobby_scene import LobbyScene
from app.gameplay_scene import GameplayScene
from net.commands import Command
from ui.widgets import ShapeButton


class Game(Application):
    client: BaseClient  # created in start_client(), which __init__ calls

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

        # UI sound effects, loaded once (the mixer is up via Application). Each
        # load is guarded so a missing/disabled audio device degrades to silence
        # instead of crashing. Scenes play these by key off self.sounds; the
        # shared button click is also handed to ShapeButton.
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        for key in ("click", "switch_ready", "switch_unready"):
            try:
                self.sounds[key] = pygame.mixer.Sound(str(self.assets.sound_path(key)))
            except pygame.error as error:
                self.debug_log(f"[AUDIO] sound '{key}' unavailable: {error}")
        ShapeButton.set_click_sound(self.sounds.get("click"))

        # Session state shared across scenes.
        self.mode: Mode | None = None
        self.player_info = None

        # Game owns the active scene and forwards the loop to it. The lobby is
        # persistent (kept across a play session so we can return to it); the
        # gameplay scene is created on start() and dropped on back-to-menu.
        self.lobby = LobbyScene(self)
        self.gameplay: GameplayScene | None = None
        self.active_scene = self.lobby

        # Incoming server message -> handler. Mirrors the server's _handlers dict;
        # both dispatch on the shared net.commands.Command names. Lobby-phase
        # messages go to self.lobby; gameplay-phase ones are routed to
        # self.gameplay (and safely no-op when not in-world).
        self._message_handlers = {
            Command.SET_PLAYER_COUNT: self.lobby.update_player_count,
            Command.UPDATE_ROOM: self._on_update_room,
            Command.LEAVE_ROOM: self._on_leave_room,
            Command.START_GAME: self._on_start_game,
            Command.UPDATE_PLAYER: self._on_update_player,
            Command.SHOOT: self._on_shoot,
            Command.SPAWN: self._on_spawn,
            Command.UPDATE_MOBS: self._on_update_mobs,
            Command.DISCONNECT: self._on_disconnect_message,
        }

        self.start_client()
        self.lobby.open_panel("main_menu")

    @property
    def is_game_started(self) -> bool:
        return self.gameplay is not None and self.active_scene is self.gameplay

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
        # Building the scene fully before swapping it in keeps the loop thread
        # safe: it only ever sees the old lobby or the finished gameplay scene.
        self.gameplay = GameplayScene(self)
        self.active_scene = self.gameplay

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
        if self.gameplay:
            self.gameplay.update_player_position(value[0], value[1])
            self.gameplay.update_player_angle(value[0], value[2])

    def _on_shoot(self, value) -> None:
        if self.gameplay:
            player = self.gameplay.players.get_player_with_id(value)
            if player:
                player.shoot()

    def _on_spawn(self, value) -> None:
        if self.gameplay:
            self.gameplay.spawn_mob(value)

    def _on_update_mobs(self, value) -> None:
        if self.gameplay:
            self.gameplay.update_mobs(value)

    def _on_disconnect_message(self, value) -> None:
        if self.player_info and self.player_info.id == value:
            # Server told us we're gone: drop the socket first so exit() doesn't
            # try to send a redundant !DISCONNECT back.
            self.client.disconnect()
            self.exit()
        elif self.gameplay:
            self.gameplay.remove_player(value)

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
            # Drop the gameplay scene so stale in-world messages no-op, and
            # return to the menu.
            self.gameplay = None
            self.active_scene = self.lobby
            self.lobby.open_panel("main_menu")
        else:
            self.lobby.handle_back()

    @override
    def handle_event(self, event: pygame.event.Event) -> None:
        self.active_scene.handle_event(event)

    @override
    def update(self) -> None:
        self.active_scene.update()

    @override
    def draw(self) -> None:
        self.active_scene.draw()

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
