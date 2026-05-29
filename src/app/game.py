import threading
from typing import override

from util.constants import *
from pygame_core.application import Application
from pygame_core.asset_manager import AssetManager
from pygame_core.asset_path import AssetPath
from pygame_core.debug import Debug
from pygame_core.panel_manager import PanelManager
from pygame_core.panel_loader_ext import PanelLoaderExt
from pygame_core import panel_factory
from pygame_core.ecs.components.transform import Transform
from pygame_core.ecs.state_object import StateObject
from pygame_core.ui_widgets.text_object import TextObject

from net.client import Client
from gameplay.map import Map
from gameplay.camera import Camera
from gameplay.player import Players
from gameplay.mob import Mobs
from gameplay.bullet import Bullets
from net.player_info import PlayerInfo
from net.room import Room
from ui.widgets import (ShapeButton, make_ellipse_button_factory,
                        make_triangle_button_factory, make_input_factory)


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
        self._menu_font = pygame.font.Font(None, 40)

        self.window.fill(BACKGROUND_COLORS['menu'])
        pygame.display.update()

        self.gun_flashes = [self.assets.image_path(f"muzzle_{i + 1}") for i in range(5)]

        self.is_game_started = False
        self.mode = None
        self.selected_character = 0
        self.room_action = None  # 'start' | 'ready' | 'unready'

        self.all_sprites = pygame.sprite.LayeredUpdates()
        self.walls = pygame.sprite.Group()

        self._load_panels()
        self._build_dynamic_objects()
        self.handlers = {
            "main_menu":        self._handle_main_menu,
            "player_menu":      self._handle_player_menu,
            "game_type_menu":   self._handle_game_type_menu,
            "create_room_menu": self._handle_create_room_menu,
            "connect_menu":     self._handle_connect_menu,
            "room_menu":        self._handle_room_menu,
        }

        self.start_client()
        self.open_panel("main_menu")

    # region Panel / menu setup

    def _load_panels(self) -> None:
        self.panel_manager = PanelManager(starting_tab="main_menu")
        loader = PanelLoaderExt(self.panel_manager, Transform((0, 0), self.size), self.assets)
        loader.register("object", panel_factory.make_factory(self.assets), default=True)
        loader.register("text", panel_factory.make_text_factory(self.assets))
        loader.register("ellipse_button", make_ellipse_button_factory())
        loader.register("triangle_button", make_triangle_button_factory())
        loader.register("input", make_input_factory())
        loader.load("config/panels.yaml")

    def _build_dynamic_objects(self) -> None:
        pm = self.panel_manager

        # Character carousel (player_menu): a preview image + a name label.
        player_bg = pm["player_menu"]["panel_bg"].rect
        self.character_preview = StateObject(parent=player_bg, pos=("CENTER", 195), size=CHARACTER_SIZE)
        for character in CHARACTER_LIST:
            self.character_preview.add_state(character, self.assets.image_path(f"char_{character}_idle"))
        self.character_preview.set_base_state(CHARACTER_LIST[0])
        pm.add_object("player_menu", "character_preview", self.character_preview)

        self.character_name_text = TextObject(
            player_bg, ("CENTER", 145), self._display_name(CHARACTER_LIST[0]), self._menu_font)
        pm.add_object("player_menu", "character_name", self.character_name_text)

        # Room player-slot pool + the start/ready/unready action button (room_menu).
        room_bg = pm["room_menu"]["panel_bg"].rect
        self.room_slots = []
        for i in range(MAX_ROOM_SIZE):
            slot = TextObject(room_bg, ("CENTER", (i + 1) * 60 + 23), "", self._menu_font)
            slot.active = False
            pm.add_object("room_menu", f"player_slot_{i}", slot)
            self.room_slots.append(slot)

        self.room_action_button = ShapeButton(
            room_bg, ("CENTER", 385), (300, 60), normal_color=Green, hover_color=Red)
        pm.add_object("room_menu", "action_button", self.room_action_button)
        self.room_action_text = TextObject(
            self.room_action_button.rect, ("CENTER", "CENTER"), "", self._menu_font)
        pm.add_object("room_menu", "action_text", self.room_action_text)

    def open_panel(self, name: str) -> None:
        self.panel_manager.current_panel = name
        if name == "game_type_menu":
            connected = self.client.is_connected
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
        return button.is_clicked(event, self.mouse.position)

    # endregion

    # region Per-panel event handlers

    def _handle_main_menu(self, event) -> None:
        panel = self.panel_manager["main_menu"]
        if self._clicked(panel["play"], event):
            self.open_panel("player_menu")
        elif self._clicked(panel["exit"], event):
            self.exit()

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
            self.set_player(panel["name_input"].text, CHARACTER_LIST[self.selected_character])
            self.open_panel("game_type_menu")
        elif self._clicked(panel["back"], event):
            self.open_panel("main_menu")

    def _handle_game_type_menu(self, event) -> None:
        panel = self.panel_manager["game_type_menu"]
        if self._clicked(panel["new_game"], event):
            self.mode = "offline"
            self.open_panel("create_room_menu")
        elif self._clicked(panel["create_room"], event):
            self.mode = "online"
            self.open_panel("create_room_menu")
        elif self._clicked(panel["connect"], event):
            self.mode = "online"
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
            command = {"start": "!START_GAME", "ready": "!GET_READY", "unready": "!GET_UNREADY"}[self.room_action]
            self.client.send_data(command)
        if self._clicked(panel["leave_room"], event):
            self.client.send_data("!LEAVE_ROOM")

    # endregion

    # region Networking / game flow (called by the handlers + client callbacks)

    def debug_log(self, text):
        # Kept for the network client, which logs connection status here.
        self._debug_text = str(text)

    def start_client(self) -> None:
        self.client = Client(self)
        self.client.start()

    def set_player(self, name, character_name) -> None:
        self.player_info = PlayerInfo(name=name, character_name=character_name)
        self.client.send_data("!SET_PLAYER", [name, character_name])

    def create_room(self, map_name):
        base_points = Map(self, AssetPath(map_name, "maps", "tmx"), 2).base_points

        if self.mode == "online":
            self.client.send_data("!CREATE_ROOM", (map_name, base_points))
        elif self.mode == "offline":
            self.player_info.join_room(Room(1, map_name, base_points, False), True)
            self.start()

    def join_room(self, room_id):
        if self.mode == "online":
            self.client.send_data("!JOIN_ROOM", room_id)

    def start(self):
        self.map = Map(self, AssetPath(self.player_info.room.map_name, "maps", "tmx"), 2)
        self.map.render()
        self.players = Players(self)
        self.mobs = Mobs(self)
        self.camera = Camera(self.size, self.map)
        self.bullets = Bullets()

        self.player = self.players.add_player(self.player_info, Green)

        if self.mode == "online":
            for player in self.player_info.room:
                if not player.id == self.player.id:
                    self.players.add_player(player, Yellow)

        elif self.mode == "offline":
            thread = threading.Thread(target=self.player_info.room.handle_spawner, args=(self.spawn_mob,))
            thread.start()

        self.is_game_started = True

    def update_player_count(self, count: int):
        for tab in self.panel_manager.keys():
            text = self.panel_manager[tab]["player_count_text"]
            text.set_color(Yellow)
            text.set_text(str(count) + " Players are Online")

    def update_room(self):
        room = self.player_info.room
        if room:
            self.panel_manager["room_menu"]["room_text"].set_text("Room " + str(room.id))
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

        me = self.player_info
        if me.is_ruler:
            self.room_action = "start"
            self.room_action_text.set_text("START GAME")
            self.room_action_button.set_enabled(all_ready)
        elif me.is_ready:
            self.room_action = "unready"
            self.room_action_text.set_text("UNREADY")
            self.room_action_button.set_enabled(True)
        else:
            self.room_action = "ready"
            self.room_action_text.set_text("READY")
            self.room_action_button.set_enabled(True)

    def update_player_rect(self, player_id, delta: tuple):
        self.players.get_player_with_id(player_id).delta = delta

    def update_player_angle(self, player_id, angle):
        self.players.get_player_with_id(player_id).angle = angle

    def shoot(self):
        if self.player.is_shooting:
            if self.mode == 'online':
                self.client.send_data('!SHOOT', self.player.id)
            elif self.mode == 'offline':
                self.player.shoot()

    def remove_player(self, player_id):
        if self.is_game_started:
            self.players.remove(self.players.get_player_with_id(player_id))

    def spawn_mob(self, mob_info):
        self.mobs.add_mob(mob_info)

    def get_data(self, data) -> None:
        if data:
            command = data['command']
            value = data['value'] if 'value' in data else None

            print(command, value)

            if command == '!SET_PLAYER_COUNT':
                self.update_player_count(value)
            elif command == '!UPDATE_ROOM' and value:
                self.player_info = value
                self.update_room()
            elif command == '!LEAVE_ROOM':
                self.open_panel("game_type_menu")
            elif command == '!START_GAME':
                self.start()
            elif command == '!UPDATE_PLAYER':
                self.update_player_rect(value[0], value[1])
                self.update_player_angle(value[0], value[2])
            elif command == '!SHOOT':
                self.players.get_player_with_id(value).shoot()
            elif command == '!SPAWN':
                self.spawn_mob(value)
            elif command == '!DISCONNECT':
                if getattr(self, 'player_info', None) and self.player_info.id == value:
                    self.client.is_connected = False
                    self.exit()
                else:
                    self.remove_player(value)

    # endregion

    # region Application overrides

    @override
    def _handle_core_event(self, event: pygame.event.Event) -> None:
        # Esc/QUIT drive menu/in-game back-navigation (not a hard exit), matching the
        # original game; keep F1 (debug) and F11 (fullscreen) from the base.
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            self._handle_back()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F1:
                self._is_in_debug_mode = not self._is_in_debug_mode
            elif event.key == pygame.K_F11:
                self.minimize() if self.size != self.minimized_size else self.full_screen()

    def _handle_back(self) -> None:
        current = self.panel_manager.current_panel
        if self.is_game_started:
            self.is_game_started = False
            self.open_panel("main_menu")
        elif current == "player_menu":
            self.open_panel("main_menu")
        elif current == "game_type_menu":
            self.open_panel("player_menu")
        elif current in ("create_room_menu", "connect_menu"):
            self.open_panel("game_type_menu")
        elif current == "main_menu":
            self.exit()

    @override
    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.is_game_started:
            self.panel_manager.handle_event(event, self.mouse.position)
            handler = self.handlers.get(self.panel_manager.current_panel)
            if handler:
                handler(event)
        else:
            self.player.handle_events(event, self.mouse.position, self.keys)

    @override
    def update(self) -> None:
        # Compat attributes the gameplay/networking code reads via self.game.*
        self.delta_time = self.clock.get_time() * .001 * FPS
        self.mouse_position = self.mouse.position

        if not self.is_game_started:
            self.panel_manager.update()
        else:
            self.all_sprites.update()
            self.camera.follow(self.player.rect)
            self.shoot()

            if hasattr(self, "player"):
                self.player.rotate_to_mouse()
                self.player.move()

            if self.mode == "online":
                self.client.send_data("!UPDATE_PLAYER", [self.player_info.id, self.player.delta, self.player.angle])
            elif self.mode == "offline":
                self.player_info.room.update(self.spawn_mob)

    @override
    def draw(self) -> None:
        if not self.is_game_started:
            self.window.fill(BACKGROUND_COLORS['menu'])
            self.panel_manager.draw(self.window)
        else:
            self.camera.draw(self.window, [self.map])
            self.camera.draw(self.window, self.all_sprites)

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
        Debug.draw(self.window, self.debug_font, [
            ("Application", {
                "FPS": round(self.clock.get_fps()),
                "Mouse": self.mouse.position,
                "Game started": self.is_game_started,
            }),
            ("Client", {"Log": self._debug_text}),
        ])

    @override
    def exit(self) -> None:
        # Best-effort notify the server, then always tear down the socket and exit -
        # don't depend on the server echoing !DISCONNECT back to close the window.
        if self.client.is_connected:
            self.client.send_data('!DISCONNECT')
        self.client.disconnect_from_server()
        super().exit()

    # endregion
