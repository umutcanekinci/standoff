"""Menu + lobby phase: main menu, character select, room creation/joining.

Owns the panel UI and the pre-game flow. The in-world phase lives in
GameplayScene. Shared session state (client, player_info, mode) lives on Game;
this scene writes those when the player commits a choice and reads them back.
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pygame

from util.constants import (
    BACKGROUND_COLORS,
    MAX_ROOM_SIZE,
    CHARACTER_LIST,
    CHARACTER_SIZE,
    CLIENT_IP,
    CLIENT_PORT,
    UI_REFERENCE_SIZE,
    Mode,
    Red,
    Green,
    Yellow,
    White,
    Blue,
)

# How many room rows the browser shows at once (no scrolling yet); extra public
# rooms are reported in the status line.
BROWSER_ROWS = 4
from pygame_core.asset_path import AssetPath
from pygame_core.panel_manager import PanelManager
from pygame_core.panel_loader_ext import PanelLoaderExt
from pygame_core import panel_factory
from pygame_core.ecs.components.transform import Transform
from pygame_core.ecs.state_object import StateObject
from pygame_core.ui_widgets.text_object import TextObject

from app.scene import Scene
from gameplay.controls import is_android
from gameplay.map import Map
from net.commands import Command
from net.player_info import PlayerInfo
from net.room import Room
from ui.widgets import (
    InputObject,
    ShapeButton,
    make_ellipse_button_factory,
    make_triangle_button_factory,
    make_input_factory,
    make_text_factory,
)

if TYPE_CHECKING:
    from app.game import Game


class LobbyScene(Scene):
    # Built in _load_panels / _build_dynamic_objects, both called from __init__.
    panel_manager: PanelManager
    character_preview: StateObject
    character_name_text: TextObject
    room_slots: list
    room_action_button: ShapeButton
    room_rows: list  # clickable room-browser rows (connect_menu)
    room_row_ids: list  # room id behind each row, parallel to room_rows

    def __init__(self, game: "Game") -> None:
        super().__init__(game)

        # The panels are authored for UI_REFERENCE_SIZE; map them onto the actual
        # window (which is a lower logical resolution on mobile), and enlarge a
        # little on touch devices for fat-finger targets. Applied to the YAML
        # panels via the loader in _load_panels AND to the objects built in code
        # below, so static chrome and the dynamic preview/name/slots stay aligned.
        touch = is_android() or os.environ.get("STANDOFF_TOUCH")
        self._ui_scale = (self.game.size[1] / UI_REFERENCE_SIZE[1]) * (
            1.35 if touch else 1.0
        )
        self._menu_font = pygame.font.Font(None, round(40 * self._ui_scale))
        self._slot_font = pygame.font.Font(None, round(25 * self._ui_scale))

        self.selected_character = 0
        self.room_action = None  # 'start' | 'ready' | 'unready'

        self._load_panels()
        self._build_dynamic_objects()
        # Pre-fill the SERVER menu with the current defaults (editable by the user).
        self._connecting = False
        self._connect_deadline = 0
        self._on_connected = None  # continuation run once an async dial succeeds
        self._auto_joined = False  # one auto-join per browser visit (single room)
        self._text_input_on = False  # whether the soft keyboard is currently up
        self.panel_manager["server_menu"]["ip_input"].set_text(CLIENT_IP)
        self.panel_manager["server_menu"]["port_input"].set_text(str(CLIENT_PORT))
        self.handlers = {
            "main_menu": self._handle_main_menu,
            "player_menu": self._handle_player_menu,
            "game_type_menu": self._handle_game_type_menu,
            "create_room_menu": self._handle_create_room_menu,
            "connect_menu": self._handle_connect_menu,
            "server_menu": self._handle_server_menu,
            "room_menu": self._handle_room_menu,
        }

    # Panel / menu setup

    def _load_panels(self) -> None:
        self.panel_manager = PanelManager(starting_tab="main_menu")
        loader = PanelLoaderExt(
            self.panel_manager, Transform((0, 0), self.game.size), self.game.assets
        )
        loader.scale = self._ui_scale
        loader.authored_size = UI_REFERENCE_SIZE
        loader.register(
            "object", panel_factory.make_factory(self.game.assets), default=True
        )
        loader.register("text", make_text_factory())
        loader.register("ellipse_button", make_ellipse_button_factory())
        loader.register("triangle_button", make_triangle_button_factory())
        loader.register("input", make_input_factory())
        loader.load("config/panels.yaml")

    def _build_dynamic_objects(self) -> None:
        pm = self.panel_manager
        assets = self.game.assets
        k = self._ui_scale  # keep these in register with the scaled YAML panels

        # Character carousel (player_menu): a preview image + a name label.
        player_bg = pm["player_menu"]["panel_bg"].rect
        self.character_preview = StateObject(
            parent=player_bg,
            pos=("CENTER", round(195 * k)),
            size=tuple(round(c * k) for c in CHARACTER_SIZE),
        )
        for character in CHARACTER_LIST:
            self.character_preview.add_state(
                character, assets.image_path(f"char_{character}_idle")
            )
        self.character_preview.set_base_state(CHARACTER_LIST[0])
        pm.add_object("player_menu", "character_preview", self.character_preview)

        self.character_name_text = TextObject(
            player_bg,
            ("CENTER", round(145 * k)),
            self._display_name(CHARACTER_LIST[0]),
            self._menu_font,
        )
        pm.add_object("player_menu", "character_name", self.character_name_text)

        # Room player-slot pool + the start/ready/unready action button (room_menu).
        room_bg = pm["room_menu"]["panel_bg"].rect
        self.room_slots = []
        for i in range(MAX_ROOM_SIZE):
            slot = TextObject(
                room_bg, ("CENTER", round(((i + 1) * 60 + 23) * k)), "", self._slot_font
            )
            slot.active = False
            pm.add_object("room_menu", f"player_slot_{i}", slot)
            self.room_slots.append(slot)

        self.room_action_button = ShapeButton(
            room_bg,
            ("CENTER", round(385 * k)),
            (round(300 * k), round(60 * k)),
            normal_color=Green,
            hover_color=Red,
            text="",
        )
        # This button is a contextual toggle (start / ready / unready); its sound
        # is chosen per action in _handle_room_menu, so skip the generic click.
        self.room_action_button.plays_click = False
        pm.add_object("room_menu", "action_button", self.room_action_button)

        # Room-browser rows (connect_menu): a pool of buttons, each a clickable
        # room. Filled/hidden by show_room_list; the room id behind each lives in
        # the parallel room_row_ids list. Built inactive (no rooms yet).
        browser_bg = pm["connect_menu"]["panel_bg"].rect
        self.room_rows = []
        self.room_row_ids = []
        for i in range(BROWSER_ROWS):
            row = ShapeButton(
                browser_bg,
                ("CENTER", round((66 + i * 48) * k)),
                (round(360 * k), round(42 * k)),
                normal_color=Blue,
                hover_color=Green,
                text="",
                text_size=round(24 * k),
            )
            row.active = False
            pm.add_object("connect_menu", f"room_row_{i}", row)
            self.room_rows.append(row)
            self.room_row_ids.append(None)

    def open_panel(self, name: str) -> None:
        self.panel_manager.current_panel = name
        if name == "game_type_menu":
            connected = self.game.client.is_connected
            self.panel_manager[name]["create_room"].set_enabled(connected)
            self.panel_manager[name]["connect"].set_enabled(connected)
            # The Android build is client-only (no inbound sockets), so it can't
            # host — grey the button there. Desktop can always host.
            self.panel_manager[name]["host"].set_enabled(not is_android())
        elif name == "server_menu":
            # Reflect the live state when entering (e.g. already connected locally).
            self._connecting = False
            if self.game.client.is_connected:
                self._set_server_status("Connected", Green)
            else:
                self._set_server_status("", White)
        elif name == "connect_menu":
            # Open the browser empty and ask the server for its public rooms; the
            # reply lands in show_room_list. Reset the one-shot auto-join.
            self._auto_joined = False
            for row in self.room_rows:
                row.active = False
            self._set_browser_status("Loading rooms...", White)
            self.game.client.send(Command.LIST_ROOMS)

    @staticmethod
    def _display_name(name: str) -> str:
        return " ".join(word.capitalize() for word in name.split("_"))

    def _refresh_character(self) -> None:
        character = CHARACTER_LIST[self.selected_character]
        self.character_preview.set_base_state(character)
        self.character_name_text.set_text(self._display_name(character))

    def _clicked(self, button, event) -> bool:
        return button.is_clicked(event, self.game.mouse.position)

    # Loop hooks (driven by Game while this scene is active)

    def handle_event(self, event) -> None:
        self.panel_manager.handle_event(event, self.game.mouse.position)
        handler = self.handlers.get(self.panel_manager.current_panel)
        if handler:
            handler(event)

    def update(self) -> None:
        self.panel_manager.update()
        self._sync_soft_keyboard()
        # Both the SERVER menu (remote dial) and the HOST flow (loopback dial,
        # which leaves us on game_type_menu) wait on an async connect.
        if self.panel_manager.current_panel in ("server_menu", "game_type_menu"):
            self._poll_connection()

    def _sync_soft_keyboard(self) -> None:
        # Raise the on-screen keyboard (Android) only while a text field is focused,
        # and point the IME at it; lower it otherwise. Driven once per frame off the
        # fields' own `editing` flags, so it can't fight the per-widget click order.
        # On desktop this just gates TEXTINPUT the same way (harmless).
        focused = None
        if self.panel_manager.current_panel in self.panel_manager:
            for obj in self.panel_manager[self.panel_manager.current_panel].values():
                if isinstance(obj, InputObject) and obj.editing:
                    focused = obj
                    break
        if focused is not None:
            if not self._text_input_on:
                pygame.key.start_text_input()
                self._text_input_on = True
            pygame.key.set_text_input_rect(focused.rect)
        elif self._text_input_on:
            pygame.key.stop_text_input()
            self._text_input_on = False

    def draw(self) -> None:
        self.game.window.fill(BACKGROUND_COLORS["menu"])
        self.panel_manager.draw(self.game.window)

    def handle_back(self) -> None:
        """Esc/back navigation within the menus."""
        current = self.panel_manager.current_panel
        if current == "player_menu":
            self.open_panel("main_menu")
        elif current == "game_type_menu":
            self.open_panel("player_menu")
        elif current in ("create_room_menu", "connect_menu", "server_menu"):
            self.open_panel("game_type_menu")
        elif current == "main_menu":
            self.game.exit()

    # Per-panel event handlers

    def _handle_main_menu(self, event) -> None:
        panel = self.panel_manager["main_menu"]
        if self._clicked(panel["play"], event):
            self.open_panel("player_menu")
        elif self._clicked(panel["exit"], event):
            self.game.exit()

    def _handle_player_menu(self, event) -> None:
        panel = self.panel_manager["player_menu"]
        if self._clicked(panel["previous"], event):
            if self.selected_character > 0:
                self.selected_character -= 1
                self._refresh_character()
        elif self._clicked(panel["next"], event):
            if self.selected_character + 1 < len(CHARACTER_LIST):
                self.selected_character += 1
                self._refresh_character()
        elif self._clicked(panel["confirm"], event):
            self.set_player(
                panel["name_input"].text, CHARACTER_LIST[self.selected_character]
            )
            self.open_panel("game_type_menu")
        elif self._clicked(panel["back"], event):
            self.open_panel("main_menu")

    def _handle_game_type_menu(self, event) -> None:
        panel = self.panel_manager["game_type_menu"]
        if self._clicked(panel["new_game"], event):
            self.game.mode = Mode.OFFLINE
            self.open_panel("create_room_menu")
        elif self._clicked(panel["host"], event):
            self._host_game()
        elif self._clicked(panel["server"], event):
            self.open_panel("server_menu")
        elif self._clicked(panel["create_room"], event):
            self.game.mode = Mode.ONLINE
            self.open_panel("create_room_menu")
        elif self._clicked(panel["connect"], event):
            self.game.mode = Mode.ONLINE
            self.open_panel("connect_menu")
        elif self._clicked(panel["back"], event):
            self.open_panel("player_menu")

    def _handle_server_menu(self, event) -> None:
        panel = self.panel_manager["server_menu"]
        if self._clicked(panel["connect"], event):
            self._connect_to_server(panel["ip_input"].text, panel["port_input"].text)
        elif self._clicked(panel["back"], event):
            self.open_panel("game_type_menu")

    def _connect_to_server(self, ip: str, port: str) -> None:
        # Fall back to the defaults for blank/garbage fields so a mistyped port
        # can't crash the connect. The actual dial is async (see _poll_connection).
        ip = ip.strip() or CLIENT_IP
        port = int(port) if port.strip().isdigit() else CLIENT_PORT
        self.game.mode = Mode.ONLINE
        self.game.connect_to_server(ip, port)
        self._set_server_status(f"Connecting to {ip}:{port}...", Yellow)
        self._begin_connect()

    def _host_game(self) -> None:
        # Desktop only (gated in open_panel); start an in-process server and dial
        # our own client at it, then drop into room creation as the ruler once
        # the loopback connect lands. The dial is async like the SERVER menu's.
        if not self.game.host_server():
            return  # bind failed (port busy); the reason is in the debug log
        self.game.mode = Mode.ONLINE
        self._begin_connect(then=lambda: self.open_panel("create_room_menu"))

    def _begin_connect(self, then=None) -> None:
        """Arm the async-connect poll. `then` (if given) runs once on success,
        replacing the default 'back to the SERVER menu' behaviour."""
        self._connecting = True
        self._on_connected = then
        self._connect_deadline = pygame.time.get_ticks() + 4000

    def _poll_connection(self) -> None:
        # Connecting is off-thread, so watch is_connected for the result and give
        # up after the deadline. On success, re-announce our player (a fresh
        # connection doesn't know our name) and run the continuation, or fall back
        # to returning to the now-enabled SERVER menu.
        if not self._connecting:
            return
        if self.game.client.is_connected:
            self._connecting = False
            if self.game.player_info is not None:
                self.game.client.send(
                    Command.SET_PLAYER,
                    [self.game.player_info.name, self.game.player_info.character_name],
                )
            then, self._on_connected = self._on_connected, None
            if then is not None:
                then()
            else:
                self._set_server_status("Connected!", Green)
                self.open_panel("game_type_menu")
        elif pygame.time.get_ticks() > self._connect_deadline:
            self._connecting = False
            self._on_connected = None
            self._set_server_status("Could not connect", Red)

    def _set_server_status(self, text: str, color) -> None:
        status = self.panel_manager["server_menu"]["status_text"]
        status.set_text(text)
        status.set_color(color)

    def _handle_create_room_menu(self, event) -> None:
        panel = self.panel_manager["create_room_menu"]
        if self._clicked(panel["create"], event):
            self.create_room("level2")
        elif self._clicked(panel["back"], event):
            self.open_panel("game_type_menu")

    def _handle_connect_menu(self, event) -> None:
        panel = self.panel_manager["connect_menu"]
        # A click on a listed room joins it directly (public rooms).
        for i, row in enumerate(self.room_rows):
            if row.active and self._clicked(row, event):
                self.join_room(self.room_row_ids[i])
                return
        # The text field is for private rooms, which aren't listed.
        if self._clicked(panel["join"], event):
            text = panel["room_id_input"].text
            self.join_room(int(text) if text.isnumeric() else 0)
        elif self._clicked(panel["back"], event):
            self.open_panel("game_type_menu")

    def show_room_list(self, rooms) -> None:
        """Render a LIST_ROOMS reply into the row pool. `rooms` is a list of
        {id, map_name, players, size, started}. Auto-joins a lone open room once
        per visit so a local listen-server (one room) needs no clicks."""
        # Ignore a reply that lands after the player left the browser, so a stale
        # single-room list can't auto-join (or repaint) them elsewhere.
        if self.panel_manager.current_panel != "connect_menu":
            return
        for i, row in enumerate(self.room_rows):
            if i < len(rooms):
                room = rooms[i]
                full = room["players"] >= room["size"]
                tag = " (in game)" if room["started"] else ""
                row.set_label(
                    f"Room {room['id']}  {room['players']}/{room['size']}{tag}"
                )
                row.set_enabled(not full)  # can't join a full room
                row.active = True
                self.room_row_ids[i] = room["id"]
            else:
                row.active = False
                self.room_row_ids[i] = None

        if not rooms:
            self._set_browser_status("No public rooms — create one", White)
        elif len(rooms) > len(self.room_rows):
            self._set_browser_status(
                f"Showing {len(self.room_rows)} of {len(rooms)} rooms", White
            )
        else:
            self._set_browser_status("", White)

        # One open room: drop straight in (the listen-server case). Guarded so a
        # later refresh with the same single room doesn't yank a browsing player.
        if (
            not self._auto_joined
            and len(rooms) == 1
            and rooms[0]["players"] < rooms[0]["size"]
        ):
            self._auto_joined = True
            self.join_room(rooms[0]["id"])

    def _set_browser_status(self, text: str, color) -> None:
        status = self.panel_manager["connect_menu"]["status_text"]
        status.set_text(text)
        status.set_color(color)

    def _handle_room_menu(self, event) -> None:
        panel = self.panel_manager["room_menu"]
        if self.room_action and self._clicked(panel["action_button"], event):
            # Each action picks its own feedback: a switch for the ready/unready
            # toggle, the plain click for starting the game.
            command, sound_key = {
                "start": (Command.START_GAME, "click"),
                "join": (Command.JOIN_GAME, "switch_ready"),
                "ready": (Command.GET_READY, "switch_ready"),
                "unready": (Command.GET_UNREADY, "switch_unready"),
            }[self.room_action]
            self.game.client.send(command)
            sound = self.game.sounds.get(sound_key)
            if sound is not None:
                sound.play()
        if self._clicked(panel["leave_room"], event):
            self.game.client.send(Command.LEAVE_ROOM)

    # Lobby actions (button-triggered; orchestrate session + network)

    def set_player(self, name, character_name) -> None:
        self.game.player_info = PlayerInfo(name=name, character_name=character_name)
        self.game.client.send(Command.SET_PLAYER, [name, character_name])

    def create_room(self, map_name):
        # Parse the map only for its base points. Map builds wall Obstacles into
        # its world's .walls as a side effect, but no gameplay scene exists yet,
        # so give it a throwaway sink to collect (and discard) them.
        sink = SimpleNamespace(walls=[])
        base_points = Map(sink, AssetPath(map_name, "maps", "tmx"), 2).base_points

        if self.game.mode == Mode.ONLINE:
            self.game.client.send(Command.CREATE_ROOM, (map_name, base_points))
        elif self.game.mode == Mode.OFFLINE:
            self.game.player_info.join_room(Room(1, map_name, base_points, False), True)
            self.game.start()

    def join_room(self, room_id):
        if self.game.mode == Mode.ONLINE:
            self.game.client.send(Command.JOIN_ROOM, room_id)

    # Lobby state updates (called by Game's network message router)

    def update_player_count(self, count: int):
        for tab in self.panel_manager.keys():
            text = self.panel_manager[tab]["player_count_text"]
            text.set_color(Yellow)
            text.set_text(str(count) + " Players are Online")

    def update_room(self):
        room = self.game.player_info.room
        if room:
            self.panel_manager["room_menu"]["room_text"].set_text(
                "Room " + str(room.id)
            )
            self.open_panel("room_menu")
            self.update_players_in_room(room)

    def update_players_in_room(self, room):
        all_ready = True
        for i, slot in enumerate(self.room_slots):
            if i < len(room):
                player = room[i]
                if player.is_ruler:
                    text, color = player.name + " (Ruler)", Red
                elif player.is_ready:
                    text, color = player.name + " (Ready)", Green
                else:
                    text, color = player.name, White
                    all_ready = False
                slot.set_text(text)
                slot.set_color(color)
                slot.active = True
            else:
                slot.active = False

        me = self.game.player_info
        if me.is_ruler:
            self.room_action = "start"
            self.room_action_button.set_label("START GAME")
            self.room_action_button.set_enabled(all_ready)
        else:
            # One button for guests: ready up before the match, or drop into a
            # match already in progress. The server picks which, per room.started.
            self.room_action = "join"
            self.room_action_button.set_label("JOIN GAME")
            self.room_action_button.set_enabled(True)
