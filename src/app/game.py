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

        self.gunFlashes = [ImagePath('muzzle_0' + str(i + 1), 'effects/muzzle_flashes') for i in range(5)]

        self.isGameStarted = False

        self.allSprites = pygame.sprite.LayeredUpdates()
        self.walls = pygame.sprite.Group()

        self.menu = Menu(self)

        self.StartClient()

        self.menu.OpenTab("mainMenu")

    # region Networking / game flow (called by the menu + client callbacks)

    def DebugLog(self, text):
        # Kept for the network client, which logs connection status here.
        self._debug_text = str(text)

    def StartClient(self) -> None:
        self.client = Client(self)
        self.client.Start()

    def SetPlayer(self, name, characterName) -> None:
        self.playerInfo = PlayerInfo(name=name, characterName=characterName)
        self.client.SendData("!SET_PLAYER", [name, characterName])

    def CreateRoom(self, mapName):
        basePoints = Map(self, AssetPath(mapName, "maps", "tmx"), 2).basePoints

        if self.mode == "online":
            self.client.SendData("!CREATE_ROOM", (mapName, basePoints))
        elif self.mode == "offline":
            self.playerInfo.JoinRoom(Room(1, mapName, basePoints, False), True)
            self.Start()

    def JoinRoom(self, roomID):
        if self.mode == "online":
            self.client.SendData("!JOIN_ROOM", roomID)

    def Start(self):
        self.map = Map(self, AssetPath(self.playerInfo.room.mapName, "maps", "tmx"), 2)
        self.map.Render()
        self.players = Players(self)
        self.mobs = Mobs(self)
        self.camera = Camera(self.size, self.map)
        self.bullets = Bullets()

        self.player = self.players.Add(self.playerInfo, Green)

        if self.mode == "online":
            for player in self.playerInfo.room:
                if not player.ID == self.player.ID:
                    self.players.Add(player, Yellow)

        elif self.mode == "offline":
            thread = threading.Thread(target=self.playerInfo.room.HandleSpawner, args=(self.SpawnMob,))
            thread.start()

        self.isGameStarted = True

    def UpdatePlayerCount(self, count: int):
        self.menu.playerCountText.SetColor(Yellow)
        self.menu.playerCountText.UpdateText(str(count) + " Players are Online")

    def UpdateRoom(self):
        room = self.playerInfo.room
        if room:
            self.menu.roomText.UpdateText("Room " + str(room.ID))
            self.menu.OpenTab("roomMenu")
            self.menu.UpdatePlayersInRoom(room)

    def UpdatePlayerRect(self, playerID, delta: tuple):
        self.players.GetPlayerWithID(playerID).delta = delta

    def UpdatePlayerAngle(self, playerID, angle):
        self.players.GetPlayerWithID(playerID).angle = angle

    def Shoot(self):
        if self.player.isShooting:
            if self.mode == 'online':
                self.client.SendData('!SHOOT', self.player.ID)
            elif self.mode == 'offline':
                self.player.Shoot()

    def RemovePlayer(self, playerID):
        if self.isGameStarted:
            self.players.remove(self.players.GetPlayerWithID(playerID))

    def SpawnMob(self, mobInfo):
        self.mobs.Add(mobInfo)

    def GetData(self, data) -> None:
        if data:
            command = data['command']
            value = data['value'] if 'value' in data else None

            print(command, value)

            if command == '!SET_PLAYER_COUNT':
                self.UpdatePlayerCount(value)
            elif command == '!UPDATE_ROOM' and value:
                self.playerInfo = value
                self.UpdateRoom()
            elif command == '!LEAVE_ROOM':
                self.menu.OpenTab("gameTypeMenu")
            elif command == '!START_GAME':
                self.Start()
            elif command == '!UPDATE_PLAYER':
                self.UpdatePlayerRect(value[0], value[1])
                self.UpdatePlayerAngle(value[0], value[2])
            elif command == '!SHOOT':
                self.players.GetPlayerWithID(value).Shoot()
            elif command == '!SPAWN':
                self.SpawnMob(value)
            elif command == '!DISCONNECT':
                if getattr(self, 'playerInfo', None) and self.playerInfo.ID == value:
                    self.client.isConnected = False
                    self.exit()
                else:
                    self.RemovePlayer(value)

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
        if self.isGameStarted:
            self.isGameStarted = False
            self.menu.OpenTab("mainMenu")
        elif self.menu.tab == "playerMenu":
            self.menu.OpenTab("mainMenu")
        elif self.menu.tab == "gameTypeMenu":
            self.menu.OpenTab("playerMenu")
        elif self.menu.tab == "createRoomMenu":
            self.menu.OpenTab("gameTypeMenu")
        elif self.menu.tab == "connectMenu":
            self.menu.OpenTab("gameTypeMenu")
        elif self.menu.tab == "mainMenu":
            self.exit()

    @override
    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.isGameStarted:
            self.menu.HandleEvents(event, self.mouse.position, self.keys)
        else:
            self.player.HandleEvents(event, self.mouse.position, self.keys)

    @override
    def update(self) -> None:
        # Compat attributes the gameplay/networking code reads via self.game.*
        self.deltaTime = self.clock.get_time() * .001 * FPS
        self.mousePosition = self.mouse.position

        if not self.isGameStarted:
            self.menu.update()
        else:
            self.allSprites.update()
            self.camera.Follow(self.player.rect)
            self.Shoot()

            if hasattr(self, "player"):
                self.player.RotateToMouse()
                self.player.Move()

            if self.mode == "online":
                self.client.SendData("!UPDATE_PLAYER", [self.playerInfo.ID, self.player.delta, self.player.angle])
            elif self.mode == "offline":
                self.playerInfo.room.Update(self.SpawnMob)

    @override
    def draw(self) -> None:
        if not self.isGameStarted:
            self.menu.draw(self.window)
        else:
            self.camera.Draw(self.window, [self.map])
            self.camera.Draw(self.window, self.allSprites)

            for mob in self.mobs:
                mob.DrawName(self.window, self.camera)
                mob.DrawHealthBar(self.window, self.camera)
                if self._is_in_debug_mode:
                    mob.DrawRects(self.window, self.camera)

            for player in self.players:
                player.DrawName(self.window, self.camera)
                player.DrawHealthBar(self.window, self.camera)
                if self._is_in_debug_mode:
                    player.DrawRects(self.window, self.camera)

            if self._is_in_debug_mode:
                for wall in self.walls:
                    wall.DrawRect(self.window)

    @override
    def draw_debug(self) -> None:
        Debug.draw(self.window, self.debug_font, [
            ("Application", {
                "FPS": round(self.clock.get_fps()),
                "Mouse": self.mouse.position,
                "Game started": self.isGameStarted,
            }),
            ("Client", {"Log": self._debug_text}),
        ])

    @override
    def exit(self) -> None:
        # Best-effort notify the server, then always tear down the socket and exit -
        # don't depend on the server echoing !DISCONNECT back to close the window.
        if self.client.isConnected:
            self.client.SendData('!DISCONNECT')
        self.client.DisconnectFromServer()
        super().exit()

    # endregion
