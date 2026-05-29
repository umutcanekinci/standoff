import threading
from typing import override

from util.constants import *
from pygame_core.application import Application
from pygame_core.asset_path import ImagePath, AssetPath
from pygame_core.debug import Debug

from net.client import Client
from gui.menu import Menu
from gameplay.map import Map
from gameplay.camera import Camera
from gameplay.player import Players
from gameplay.mob import Mobs
from gameplay.bullet import Bullets
from net.player_info import PlayerInfo
from net.room import Room


class Game(Application):

    def __init__(self) -> None:
        super().__init__(WINDOW_SIZE, WINDOW_TITLE, FPS)

        self._debug_text = ""
        self.debug_font = pygame.font.Font(None, 25)

        self.window.fill(BACKGROUND_COLORS['menu'])
        pygame.display.update()

        self.gun_flashes = [ImagePath('muzzle_0' + str(i + 1), 'effects/muzzle_flashes') for i in range(5)]

        self.is_game_started = False

        self.all_sprites = pygame.sprite.LayeredUpdates()
        self.walls = pygame.sprite.Group()

        self.menu = Menu(self)

        self.start_client()

        self.menu.open_tab("mainMenu")

    # region Networking / game flow (called by the menu + client callbacks)

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
        self.menu.player_count_text.set_color(Yellow)
        self.menu.player_count_text.update_text(str(count) + " Players are Online")

    def update_room(self):
        room = self.player_info.room
        if room:
            self.menu.room_text.update_text("Room " + str(room.id))
            self.menu.open_tab("roomMenu")
            self.menu.update_players_in_room(room)

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
                self.menu.open_tab("gameTypeMenu")
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
        if self.is_game_started:
            self.is_game_started = False
            self.menu.open_tab("mainMenu")
        elif self.menu.tab == "playerMenu":
            self.menu.open_tab("mainMenu")
        elif self.menu.tab == "gameTypeMenu":
            self.menu.open_tab("playerMenu")
        elif self.menu.tab == "createRoomMenu":
            self.menu.open_tab("gameTypeMenu")
        elif self.menu.tab == "connectMenu":
            self.menu.open_tab("gameTypeMenu")
        elif self.menu.tab == "mainMenu":
            self.exit()

    @override
    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.is_game_started:
            self.menu.handle_events(event, self.mouse.position, self.keys)
        else:
            self.player.handle_events(event, self.mouse.position, self.keys)

    @override
    def update(self) -> None:
        # Compat attributes the gameplay/networking code reads via self.game.*
        self.delta_time = self.clock.get_time() * .001 * FPS
        self.mouse_position = self.mouse.position

        if not self.is_game_started:
            self.menu.update()
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
            self.menu.draw(self.window)
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
