#region Import Packages

from settings import *
from path import *
from client import Client
from application import Application

from menu import Menu
from map import Map
from camera import Camera
from player import Players
from mob import Mobs
from bullet import Bullets
from player_info import PlayerInfo
from room import Room
import threading

#endregion

class Game(Application):

	def __init__(self) -> None:

		super().__init__(developMode=DEVELOP_MODE)

		self.window.fill(BACKGROUND_COLORS['menu'])
		pygame.display.update()

		self.gunFlashes = [ImagePath('muzzle_0'+str(i+1), 'effects/muzzle_flashes') for i in range(5)]

		self.isGameStarted = False

		self.allSprites = pygame.sprite.LayeredUpdates()
		self.walls = pygame.sprite.Group()
		
		self.menu = Menu(self)

		self.StartClient()

		self.menu.OpenTab("mainMenu")

	def StartClient(self) -> None:

		self.client = Client(self)
		self.client.Start()

	def SetPlayer(self, name, characterName) -> None:

		self.playerInfo = PlayerInfo(name=name, characterName=characterName)
		self.client.SendData("!SET_PLAYER", [name, characterName])

	def CreateRoom(self, mapName):

		basePoints = Map(self, FilePath(mapName, "maps", "tmx"), 2).basePoints

		if self.mode == "online":

			self.client.SendData("!CREATE_ROOM", (mapName, basePoints))

		elif self.mode == "offline":

			self.playerInfo.JoinRoom(Room(1, mapName, basePoints, False), True)
			self.Start()

	def JoinRoom(self, roomID):

		if self.mode == "online":

			self.client.SendData("!JOIN_ROOM", roomID)

	def Start(self):
		
		self.map = Map(self, FilePath(self.playerInfo.room.mapName, "maps", "tmx"), 2)
		self.map.Render()
		self.players = Players(self)
		self.mobs = Mobs(self)
		self.camera = Camera(self.rect.size, self.map)
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

	def UpdateRoom(self): # Update room text after a player joined to your room

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

				if self.playerInfo.ID == value:

					self.client.isConnected = False
					self.Exit()
				
				else:

					self.RemovePlayer(value)

	def HandleEvents(self, event: pygame.event.Event) -> None:

		if not self.isGameStarted:

			self.menu.HandleEvents(event, self.mousePosition, self.keys)

		else:

			self.player.HandleEvents(event, self.mousePosition, self.keys)

		super().HandleEvents(event)

	def HandleExitEvents(self, event: pygame.event.Event) -> None:
		
		if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):

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

				self.Exit()

	def Update(self) -> None:

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

	def Draw(self):
		
		if not self.isGameStarted:

			self.menu.draw(self.window)
			
		else:

			self.camera.Draw(self.window, [self.map])
			self.camera.Draw(self.window, self.allSprites)

			for mob in self.mobs:

				mob.DrawName(self.window, self.camera)
				mob.DrawHealthBar(self.window, self.camera)

				if self.developMode:

					mob.DrawRects(self.window, self.camera)

			for player in self.players:

				player.DrawName(self.window, self.camera)
				player.DrawHealthBar(self.window, self.camera)

				if self.developMode:

					player.DrawRects(self.window, self.camera)

			if self.developMode:

				for wall in self.walls:

					wall.DrawRect(self.window)

		return super().Draw()

	def Exit(self) -> None:
		
		if self.client.isConnected:
			
			self.client.SendData('!DISCONNECT')

		else:
			
			self.client.DisconnectFromServer()
			
			super().Exit()