"""Menu + lobby phase: main menu, character select, room creation/joining.

Owns the panel UI and the pre-game flow. The in-world phase lives in
GameplayScene. Shared session state (client, player_info, mode) lives on Game;
this scene writes those when the player commits a choice and reads them back.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pygame

from util.constants import (
    BACKGROUND_COLORS,
    MAX_ROOM_SIZE,
    CHARACTER_LIST,
    CHARACTER_SIZE,
    Red,
    Green,
    Yellow,
    White,
)
from pygame_core.asset_path import AssetPath
from pygame_core.panel_manager import PanelManager
from pygame_core.panel_loader_ext import PanelLoaderExt
from pygame_core import panel_factory
from pygame_core.ecs.components.transform import Transform
from pygame_core.ecs.state_object import StateObject
from pygame_core.ui_widgets.text_object import TextObject

from app.scene import Scene
from gameplay.map import Map
from net.commands import Command
from net.player_info import PlayerInfo
from net.room import Room
from ui.widgets import (
    ShapeButton,
    make_ellipse_button_factory,
    make_triangle_button_factory,
    make_input_factory,
    make_text_factory,
)

if TYPE_CHECKING:
    from app.game import Game


class LobbyScene(Scene):
    def __init__(self, game: "Game") -> None:
        super().__init__(game)

        self._menu_font = pygame.font.Font(None, 40)
        self._slot_font = pygame.font.Font(None, 25)

        self.selected_character = 0
        self.room_action = None  # 'start' | 'ready' | 'unready'

        self._load_panels()
        self._build_dynamic_objects()
        self.handlers = {
            "main_menu": self._handle_main_menu,
            "player_menu": self._handle_player_menu,
            "game_type_menu": self._handle_game_type_menu,
            "create_room_menu": self._handle_create_room_menu,
            "connect_menu": self._handle_connect_menu,
            "room_menu": self._handle_room_menu,
        }

    # Panel / menu setup

    def _load_panels(self) -> None:
        self.panel_manager = PanelManager(starting_tab="main_menu")
        loader = PanelLoaderExt(
            self.panel_manager, Transform((0, 0), self.game.size), self.game.assets
        )
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

        # Character carousel (player_menu): a preview image + a name label.
        player_bg = pm["player_menu"]["panel_bg"].rect
        self.character_preview = StateObject(
            parent=player_bg, pos=("CENTER", 195), size=CHARACTER_SIZE
        )
        for character in CHARACTER_LIST:
            self.character_preview.add_state(
                character, assets.image_path(f"char_{character}_idle")
            )
        self.character_preview.set_base_state(CHARACTER_LIST[0])
        pm.add_object("player_menu", "character_preview", self.character_preview)

        self.character_name_text = TextObject(
            player_bg,
            ("CENTER", 145),
            self._display_name(CHARACTER_LIST[0]),
            self._menu_font,
        )
        pm.add_object("player_menu", "character_name", self.character_name_text)

        # Room player-slot pool + the start/ready/unready action button (room_menu).
        room_bg = pm["room_menu"]["panel_bg"].rect
        self.room_slots = []
        for i in range(MAX_ROOM_SIZE):
            slot = TextObject(
                room_bg, ("CENTER", (i + 1) * 60 + 23), "", self._slot_font
            )
            slot.active = False
            pm.add_object("room_menu", f"player_slot_{i}", slot)
            self.room_slots.append(slot)

        self.room_action_button = ShapeButton(
            room_bg,
            ("CENTER", 385),
            (300, 60),
            normal_color=Green,
            hover_color=Red,
            text="",
        )
        pm.add_object("room_menu", "action_button", self.room_action_button)

    def open_panel(self, name: str) -> None:
        self.panel_manager.current_panel = name
        if name == "game_type_menu":
            connected = self.game.client.is_connected
            self.panel_manager[name]["create_room"].set_enabled(connected)
            self.panel_manager[name]["connect"].set_enabled(connected)

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
        elif current in ("create_room_menu", "connect_menu"):
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
            self.game.mode = "offline"
            self.open_panel("create_room_menu")
        elif self._clicked(panel["create_room"], event):
            self.game.mode = "online"
            self.open_panel("create_room_menu")
        elif self._clicked(panel["connect"], event):
            self.game.mode = "online"
            self.open_panel("connect_menu")
        elif self._clicked(panel["back"], event):
            self.open_panel("player_menu")

    def _handle_create_room_menu(self, event) -> None:
        panel = self.panel_manager["create_room_menu"]
        if self._clicked(panel["create"], event):
            self.create_room("level2")
        elif self._clicked(panel["back"], event):
            self.open_panel("game_type_menu")

    def _handle_connect_menu(self, event) -> None:
        panel = self.panel_manager["connect_menu"]
        if self._clicked(panel["join"], event):
            text = panel["room_id_input"].text
            self.join_room(int(text) if text.isnumeric() else 0)
        elif self._clicked(panel["back"], event):
            self.open_panel("game_type_menu")

    def _handle_room_menu(self, event) -> None:
        panel = self.panel_manager["room_menu"]
        if self.room_action and self._clicked(panel["action_button"], event):
            command = {
                "start": Command.START_GAME,
                "ready": Command.GET_READY,
                "unready": Command.GET_UNREADY,
            }[self.room_action]
            self.game.client.send(command)
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

        if self.game.mode == "online":
            self.game.client.send(Command.CREATE_ROOM, (map_name, base_points))
        elif self.game.mode == "offline":
            self.game.player_info.join_room(Room(1, map_name, base_points, False), True)
            self.game.start()

    def join_room(self, room_id):
        if self.game.mode == "online":
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
        elif me.is_ready:
            self.room_action = "unready"
            self.room_action_button.set_label("UNREADY")
            self.room_action_button.set_enabled(True)
        else:
            self.room_action = "ready"
            self.room_action_button.set_label("READY")
            self.room_action_button.set_enabled(True)
