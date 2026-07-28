from __future__ import annotations

import threading
import time
from typing import override

import pygame

from util.constants import (
    WINDOW_TITLE,
    WINDOW_SIZE,
    RENDER_SCALE,
    BACKGROUND_COLORS,
    FPS,
    CLIENT_ADDR,
    SERVER_PORT,
    SPLASH_FADE_MS,
    SPLASH_HOLD_MS,
    Mode,
)
from pygame_core.application import Application
from pygame_core.asset_manager import AssetManager
from pygame_core.debug import Debug
from pygame_core.splash_screen import SplashScreen
from pygame_core.save_store import SaveStore
from pygame_core.ecs.game_audio import GameAudio, SFX_CHANNEL

from pygame_core.net.transport import BaseClient
from net.game_server import GameServer
from net.wire import make_protocol
from app.lobby_scene import LobbyScene
from app.gameplay_scene import GameplayScene
from net.commands import Command
from ui.widgets import ShapeButton


class Game(Application):
    client: BaseClient  # created in start_client(), which __init__ calls

    def __init__(self) -> None:
        super().__init__(WINDOW_SIZE, WINDOW_TITLE, FPS, render_scale=RENDER_SCALE)

        self.settings_store = SaveStore("settings")
        self._saved_settings = self.settings_store.load()
        self.restore_window_settings(self._saved_settings)

        self.assets = AssetManager()
        self.assets.load_manifest("config/assets.yaml")
        missing = self.assets.validate()
        if missing:
            raise FileNotFoundError("Missing assets:\n  " + "\n  ".join(missing))

        self.splash = SplashScreen(
            [self.assets.image_path("pygame_logo")],
            fade_ms=SPLASH_FADE_MS, hold_ms=SPLASH_HOLD_MS,
        )

        self._debug_text = ""
        self.debug_font = pygame.font.Font(None, 25)

        # self.window is the offscreen logical render target -- only
        # Application._present() (run() loop) blits it onto the real screen,
        # which hasn't started yet here, so fill the real display directly.
        self.display_surface.fill(BACKGROUND_COLORS["menu"])
        pygame.display.update()

        # GameAudio owns the music/sfx channel volumes (Settings menu controls
        # these); there's no music asset yet, so it never gets a music_path --
        # set_music_volume() still works, it just has nothing to apply to
        # until a track exists.
        self.audio = GameAudio()
        self.audio.set_music_volume(self._saved_settings.get("music_volume", 1.0))
        self.audio.set_sfx_volume(self._saved_settings.get("sfx_volume", 1.0))

        # UI sound effects, loaded once (the mixer is up via Application). Each
        # load is guarded so a missing/disabled audio device degrades to silence
        # instead of crashing. Scenes play these by key off self.sounds, via the
        # SFX channel (SFX_CHANNEL) so GameAudio's volume control reaches them;
        # the shared button click is also handed to ShapeButton the same way.
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        for key in ("click", "switch_ready", "switch_unready"):
            try:
                self.sounds[key] = pygame.mixer.Sound(str(self.assets.sound_path(key)))
            except (pygame.error, OSError) as error:
                # pygame-ce raises FileNotFoundError (an OSError), not
                # pygame.error, when a sound file can't be opened — catch both so
                # a missing/disabled audio asset degrades to silence, never a crash.
                self.debug_log(f"[AUDIO] sound '{key}' unavailable: {error}")
        ShapeButton.set_click_sound(self.sounds.get("click"))

        # Session state shared across scenes.
        self.mode: Mode | None = None
        self.player_info = None

        # When the player hosts from the menu we run a GameServer in-process (a
        # "listen server"); the host plays through the same loopback socket as a
        # remote client, so it's never privileged. None when we're a pure client.
        self.server: GameServer | None = None

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
            Command.LIST_ROOMS: self._on_list_rooms,
            Command.UPDATE_ROOM: self._on_update_room,
            Command.LEAVE_ROOM: self._on_leave_room,
            Command.START_GAME: self._on_start_game,
            Command.UPDATE_PLAYER: self._on_update_player,
            Command.SHOOT: self._on_shoot,
            Command.SPAWN: self._on_spawn,
            Command.UPDATE_MOBS: self._on_update_mobs,
            Command.KILL_MOB: self._on_kill_mob,
            Command.DISCONNECT: self._on_disconnect_message,
        }

        self.start_client()
        self.lobby.open_panel("main_menu")

    @property
    def is_game_started(self) -> bool:
        return self.gameplay is not None and self.active_scene is self.gameplay

    # Settings persistence (SaveStore-backed). Window mode/resolution
    # persistence itself lives in Application now (restore_window_settings/
    # window_settings/reset_window_settings) -- these just merge that with
    # this project's own audio settings.

    def _save_settings(self) -> None:
        self.settings_store.save({
            **self.window_settings(),
            "sfx_volume":   self.audio.sfx_volume(),
            "music_volume": self.audio.music_volume(),
        })

    def _reset_settings(self) -> None:
        """Restores window mode/size and both volumes to the shipped
        defaults, then persists immediately -- Reset is a deliberate
        action, not a live drag, so it shouldn't wait for the player to
        also press Back."""
        self.reset_window_settings()
        self.audio.set_sfx_volume(1.0)
        self.audio.set_music_volume(1.0)
        self._save_settings()

    # Networking / game flow (called by the lobby + client callbacks)

    def debug_log(self, text):
        # Kept for the network client, which logs connection status here.
        self._debug_text = str(text)

    def start_client(self) -> None:
        # Connect to the default address at startup (a server on this machine, for
        # local play). The SERVER menu can re-point us elsewhere via
        # connect_to_server — e.g. a phone dialling a desktop host.
        self._connect(CLIENT_ADDR)

    def connect_to_server(self, ip: str, port: int) -> None:
        """(Re)connect the client to a chosen address (the SERVER menu)."""
        if getattr(self, "client", None) is not None:
            self.client.disconnect()
        self._connect((ip, port))

    def host_server(self, port: int = SERVER_PORT) -> bool:
        """Start an in-process server on this machine, then dial our own client
        at it. Returns whether the server came up.

        Binds to 0.0.0.0 ("") so LAN friends (or an ngrok tunnel on the same
        port) can reach it, while our local client always connects via loopback.
        Idempotent: calling it again while already hosting is a no-op.
        """
        if self.server is not None and self.server.is_running:
            return True

        self.server = GameServer(on_status=self.debug_log)
        threading.Thread(
            target=self.server.serve, args=(("", port),), daemon=True
        ).start()

        # serve() binds+listens before flipping is_running; wait briefly so our
        # client doesn't dial the loopback port before accept() is up (which
        # would just fail the connect). A local bind needs only a few ms.
        deadline = time.time() + 1.0
        while not self.server.is_running and time.time() < deadline:
            time.sleep(0.01)
        if not self.server.is_running:
            self.debug_log("[HOST] server did not start (port already in use?)")
            self.server = None
            return False

        self.connect_to_server("127.0.0.1", port)
        return True

    def stop_hosting(self) -> None:
        if self.server is not None:
            self.server.close()
            self.server = None

    def disconnect_from_server(self) -> None:
        """Leave the current server from the lobby (the DISCONNECT button).

        Politely tell the server we're going, drop our socket, then tear down the
        embedded server if we were the host. stop_hosting() runs last so that
        while the socket closes self.server is still set — that makes
        _on_server_lost treat it as our own teardown and ignore it.
        """
        if self.client.is_connected:
            self.client.send(Command.DISCONNECT)
        self.client.disconnect()
        self.stop_hosting()

    def _connect(self, address) -> None:
        # The transport client is game-unaware: it just pumps decoded messages
        # to get_data and connection status to debug_log. Connect off-thread so a
        # slow/refused connect never blocks the game loop. The codec comes from
        # net.wire so client and server can never drift apart.
        client = BaseClient(
            on_message=self.get_data,
            # Bind the handler to THIS client so a stale disconnect from a client
            # we've already replaced (reconnect) can be ignored.
            on_disconnect=lambda: self._on_server_lost(client),
            on_status=self.debug_log,
            protocol=make_protocol(),
        )
        self.client = client
        threading.Thread(target=client.connect, args=(address,), daemon=True).start()

    def _on_server_lost(self, client) -> None:
        self.debug_log("[CLIENT] connection lost")
        # Ignore the disconnect of a client we've already swapped out (e.g. when
        # the SERVER menu reconnects elsewhere), and don't react to our own host
        # teardown — exit() is already bringing the whole app down.
        if client is not self.client or self.server is not None:
            return
        # The server vanished mid-match (e.g. a listen-server host quit). Without
        # this the remote players just froze in a dead world; bail out. We're no
        # longer connected, so leave_match lands on the main menu.
        if self.is_game_started:
            self.leave_match(to_lobby=True)

    def leave_match(self, to_lobby: bool) -> None:
        """Tear down the gameplay scene and leave the current match.

        Online: tell the server we're leaving the room so it frees our slot and
        room-mates see us go (otherwise our avatar freezes in their world); then,
        while still connected, drop to the lobby hub if `to_lobby` else the main
        menu. Offline — or once the server is already gone — there's nothing to
        notify and no lobby to return to, so go straight to the main menu.
        """
        online = self.mode == Mode.ONLINE
        self.gameplay = None
        self.active_scene = self.lobby
        if online and self.client.is_connected:
            self.client.send(Command.LEAVE_ROOM)
            if to_lobby:
                # Still on the server, just out of the room -> the server lobby.
                self.lobby.open_panel("server_lobby_menu")
                return
        self.lobby.open_panel("main_menu")

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

    def _on_list_rooms(self, value) -> None:
        self.lobby.show_room_list(value or [])

    def _on_update_room(self, value) -> None:
        if value:
            self.player_info = value
            self.lobby.update_room()

    def _on_start_game(self, _value) -> None:
        self.start()

    def _on_leave_room(self, _value) -> None:
        # The lobby "Leave Room" button lives on room_menu and wants the hub next.
        # When LEAVE_ROOM was instead part of quitting a match (leave_match), we've
        # already chosen our destination, so don't let this async reply override it.
        if self.lobby.panel_manager.current_panel == "room_menu":
            self.lobby.open_panel("server_lobby_menu")

    def _on_update_player(self, value) -> None:
        if self.gameplay:
            self.gameplay.update_player_position(value[0], value[1])
            self.gameplay.update_player_angle(value[0], value[2])
            self.gameplay.set_player_alive(
                value[0], value[3] if len(value) > 3 else True
            )

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

    def _on_kill_mob(self, value) -> None:
        if self.gameplay:
            self.gameplay.kill_mob(value)

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
    def on_canvas_resized(self, new_size: tuple[int, int]) -> None:
        # Fires during Application.__init__ (via restore_window_settings(), called
        # before self.lobby is built) as well as later from the settings menu's
        # window mode/resolution picker or F11 -- only the latter needs a reflow;
        # __init__ builds the lobby fresh against the already-current size anyway.
        if not hasattr(self, "lobby"):
            return
        self.lobby.reflow()
        # GameplayScene doesn't reflow (out of scope for the settings menu --
        # it has its own camera/HUD layout this doesn't touch), so a resize
        # mid-match may leave it visually stale until the next leave_match().

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
                self.cycle_window_mode()  # fullscreen -> borderless -> windowed -> ...

    def _handle_back(self) -> None:
        if self.is_game_started:
            # Esc/back out of a match: to the multiplayer lobby online, else menu.
            self.leave_match(to_lobby=True)
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
        self._save_settings()  # safety net -- normally already saved on leaving settings_menu
        # Best-effort notify the server, then always tear down the socket and exit -
        # don't depend on the server echoing !DISCONNECT back to close the window.
        if self.client.is_connected:
            self.client.send(Command.DISCONNECT)
        self.client.disconnect()
        self.stop_hosting()  # tear down the embedded server if we were hosting
        super().exit()
