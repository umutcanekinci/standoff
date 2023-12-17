#region Import Packages

from settings import *
from path import *
from client import Client
from application import Application
from object import Object
from input_box import InputBox
from button import TriangleButton, EllipseButton
from text import Text
from tilemap import TileMap
from player import Players
from zombie import Zombies
from bullet import Bullets
from player_info import PlayerInfo
from room import Room

#endregion

class Game(Application):

	def __init__(self) -> None:

		super().__init__(developMode=DEVELOP_MODE)

		self.isGameStarted = False
		self.menu = Menu(self)

		self.allSprites = pygame.sprite.Group()
		self.walls = pygame.sprite.Group()
		self.map = TileMap(self, FilePath("level1", "maps", "tmx"), 2)
		self.players = Players(self)
		self.zombies = Zombies(self)
		self.camera = Camera(self.rect.size, self.map)
		self.bullets = Bullets(self)

		self.StartClient()

		#self.SetPlayer("Player", 'hitman')

		# Fast offline
		#self.Start('offline')
		self.menu.OpenTab("mainMenu")

	def StartClient(self) -> None:

		self.client = Client(self)
		self.client.Start()

	def SetPlayer(self, playerName, characterName) -> None:

		self.playerInfo = PlayerInfo(name=playerName, characterName=characterName)
		self.client.SendData("!SET_PLAYER", [playerName, characterName])

	def JoinRoom(self, roomID):

		self.client.SendData("!JOIN_ROOM", roomID)

	def CreateRoom(self):

		self.client.SendData("!CREATE_ROOM")

	def Start(self, mode):
		
		self.isGameStarted = True
		self.mode = mode
		
		self.player = self.players.Add(self.playerInfo.ID, self.playerInfo.name, self.playerInfo.characterName, PLAYER_SIZE, (self.playerInfo.ID*200, self.playerInfo.ID*200))
		#self.zombies.Add(1, self.player)

		if self.mode == "online":

			for player in self.playerInfo.room:

				if not player.ID == self.player.ID:

					self.players.Add(player.ID, player.name, player.characterName, PLAYER_SIZE)

	def UpdatePlayerCount(self, count: int):

		self.menu.playerCountText.SetColor(Yellow)
		self.menu.playerCountText.UpdateText(str(count) + " Players are Online")

	def UpdateRoom(self):

		room = self.playerInfo.room

		self.menu.teamText.UpdateText("Room " + str(room.ID))
		self.menu.OpenTab("roomMenu")
		self.menu.UpdatePlayersInRoom(room)

	def UpdatePlayerRect(self, playerID, playerRect: pygame.Rect):

		self.players.GetPlayerWithID(playerID).UpdatePosition(playerRect.center)
	
	def UpdatePlayerAngle(self, playerID, angle):

		self.player.GetPlayerWithID(playerID).Rotate(angle)

	def RemovePlayer(self, playerID):

		self.players.remove(self.players.GetPlayerWithID(playerID))

	def GetData(self, data) -> None:

		if data:

			command = data['command']
			value = data['value'] if 'value' in data else None

			print(command, value)

			if command == "!SET_PLAYER_COUNT":
					
				self.UpdatePlayerCount(value)

			elif command == "!SET_ROOM" and value:

				self.playerInfo = value

				self.UpdateRoom()

			elif command == "!START_GAME":

				self.Start("online")

			elif command == "!SET_PLAYER_RECT":

				self.UpdatePlayerRect(*value)

			elif command == "!SET_PLAYER_ANGLE":

				self.UpdatePlayerAngle(*value)

			elif command == "!DISCONNECT":

				self.RemovePlayer(value)

	def HandleEvents(self, event: pygame.event.Event) -> None:

		if not self.isGameStarted:

			self.menu.HandleEvents(event, self.mousePosition, self.keys)

		else:

			self.player.HandleEvents(event, self.mousePosition, self.keys)

		return super().HandleEvents(event)

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

			if self.mode == "online":
				
				self.client.SendData("!SET_PLAYER_ANGLE", [self.playerInfo.ID, self.player.angle])
				self.client.SendData("!SET_PLAYER_RECT", [self.playerInfo.ID, self.player.rect])

	def Draw(self):
		
		if not self.isGameStarted:

			self.menu.draw(self.window)
			
		else:

			self.camera.Draw(self.window, self.allSprites)

			for zombie in self.zombies:

				if hasattr(zombie, "nameText"):

					self.window.blit(zombie.nameText.image, self.camera.Apply(zombie.nameText.rect))

				if self.developMode:

					pygame.draw.rect(self.window, Red, self.camera.Apply(zombie.rect), 2)
					pygame.draw.rect(self.window, Blue, self.camera.Apply(zombie.hitRect), 2)

			for player in self.players:

				if hasattr(player, "nameText"):

					self.window.blit(player.nameText.image, self.camera.Apply(player.nameText.rect))

				if self.developMode:

					pygame.draw.rect(self.window, Red, self.camera.Apply(player.rect), 2)
					pygame.draw.rect(self.window, Blue, self.camera.Apply(player.hitRect), 2)

		return super().Draw()

	def Exit(self) -> None:

		self.client.DisconnectFromServer()
		return super().Exit()
			
class Camera():

	def __init__(self, size: tuple, map: TileMap):
		
		self.rect = pygame.Rect((0, 0), size)
		self.map = map
		self.map.camera = self
		
	def Follow(self, targetRect):
		
		self.rect.x, self.rect.y = -targetRect.centerx + (self.rect.width / 2), -targetRect.centery + (self.rect.height / 2)
		
		self.rect.x = max(self.rect.width - self.map.rect.width, min(0, self.rect.x))
		self.rect.y = max(self.rect.height - self.map.rect.height, min(0, self.rect.y))

	def Apply(self, rect: pygame.Rect):
		
		return pygame.Rect((self.rect.x + rect.x, self.rect.y + rect.y), rect.size)

	def Draw(self, image, objects):

		for object in objects:
			
			image.blit(object.image, self.Apply(object.rect))

class Menu():

	def __init__(self, game: Game) -> None:

		super().__init__()

		self.game = game

		self.tabs = {

			"mainMenu" : pygame.sprite.Group(),
			"playerMenu" : pygame.sprite.Group(),
			"gameTypeMenu" : pygame.sprite.Group(),
			"createRoomMenu" : pygame.sprite.Group(),
			"connectMenu" : pygame.sprite.Group(),
			"roomMenu" : pygame.sprite.Group()

		}

		self.panel = Object(("CENTER", "CENTER"), size=(400, 500))

		self.title = Text(("CENTER", self.panel.rect.y-80), WINDOW_TITLE, 60, color=Red)
		self.playerCountText = Text(("CENTER", self.panel.rect.bottom+30), "You are playing in offline mode !", 24, backgroundColor=Black, color=Red)		

		self.selectedCharacter = 0
		self.characterTexts = []
		self.characters = []

		for characterName in CHARACTER_LIST:

			self.characters.append(Object(("CENTER", 195), CHARACTER_SIZE, ImagePath("idle", "characters/"+characterName), parentRect=self.panel.screenRect))

			words = characterName.split("_")
			characterName = ""

			for text in words:

				if not characterName == "":

					characterName += " "

				characterName += text.capitalize()
		
			self.characterTexts.append(Text(("CENTER", 145), characterName, 40, parentRect=self.panel.screenRect))
	
		# Main menu
		self.settingsButton = EllipseButton(("CENTER", "CENTER"), (300, 60), Red, Blue, spriteGroups=self.tabs["mainMenu"], parentRect=self.panel.screenRect, text="SETTINGS", textSize=40, isActive=False)
		self.playButton = EllipseButton(("CENTER", self.settingsButton.rect.y - 140), (300, 60), Red, Blue, spriteGroups=self.tabs["mainMenu"], parentRect=self.panel.screenRect, text="PLAY", textSize=40)
		self.achievmentsButton = EllipseButton(("CENTER", self.settingsButton.rect.y - 70), (300, 60), Red, Blue, spriteGroups=self.tabs["mainMenu"], parentRect=self.panel.screenRect, text="ACHIEVMENTS", textSize=40, isActive=False)
		self.creditsButton = EllipseButton(("CENTER", self.settingsButton.rect.y + 70), (300, 60), Red, Blue, spriteGroups=self.tabs["mainMenu"], parentRect=self.panel.screenRect, text="CREDITS", textSize=40, isActive=False)
		self.exitButton = EllipseButton(("CENTER", self.settingsButton.rect.y + 140), (300, 60), Red, Blue, spriteGroups=self.tabs["mainMenu"], parentRect=self.panel.screenRect, text="EXIT", textSize=40)

		# Player menu
		self.playerNameText = Text(("CENTER", 40), "PLAYER NAME", 40, spriteGroups=self.tabs["playerMenu"], parentRect=self.panel.screenRect)
		self.playerNameEntry = InputBox(("CENTER", 90), (300, 40), '', 'Please enter a player name...', self.tabs["playerMenu"], self.panel.screenRect)
		self.previous = TriangleButton((75, 185), (50, 50), Blue, Red, spriteGroups=self.tabs["playerMenu"], parentRect=self.panel.screenRect, rotation="LEFT")
		self.next = TriangleButton((275, 185), (50, 50), Blue, Red, spriteGroups=self.tabs["playerMenu"], parentRect=self.panel.screenRect)
		self.confirmButton = EllipseButton(("CENTER", self.creditsButton.rect.y), (300, 60), Red, Blue, spriteGroups=[self.tabs["playerMenu"]], parentRect=self.panel.screenRect, text="CONFIRM", textSize=40)
		self.backButton = EllipseButton(("CENTER", self.exitButton.rect.y), (300, 60), Red, Blue, spriteGroups=[self.tabs["playerMenu"]], parentRect=self.panel.screenRect, text="BACK", textSize=40)

		# Game type menu
		self.createRoomButton = EllipseButton(("CENTER", "CENTER"), (300, 60), Red, Blue, spriteGroups=self.tabs["gameTypeMenu"], parentRect=self.panel.screenRect, text="CREATE ROOM", textSize=40)
		self.newGameButton = EllipseButton(("CENTER", self.settingsButton.rect.y - 140), (300, 60), Red, Blue, spriteGroups=self.tabs["gameTypeMenu"], parentRect=self.panel.screenRect, text="NEW GAME", textSize=40)
		self.continueButton = EllipseButton(("CENTER", self.settingsButton.rect.y - 70), (300, 60), Red, Blue, spriteGroups=self.tabs["gameTypeMenu"], parentRect=self.panel.screenRect, text="CONTINUE", textSize=40, isActive=False)	
		self.connectButton = EllipseButton(("CENTER", self.settingsButton.rect.y + 70), (300, 60), Red, Blue, spriteGroups=self.tabs["gameTypeMenu"], parentRect=self.panel.screenRect, text="CONNECT", textSize=40)
		self.backButton2 = EllipseButton(("CENTER", self.settingsButton.rect.y + 140), (300, 60), Red, Blue, spriteGroups=self.tabs["gameTypeMenu"], parentRect=self.panel.screenRect, text="BACK", textSize=40)

		# Create room menu
		self.createButton = EllipseButton(("CENTER", self.settingsButton.rect.y + 70), (300, 60), Red, Blue, spriteGroups=self.tabs["createRoomMenu"], parentRect=self.panel.screenRect, text="CREATE", textSize=40)
		self.backButton3 = EllipseButton(("CENTER", self.settingsButton.rect.y + 140), (300, 60), Red, Blue, spriteGroups=self.tabs["createRoomMenu"], parentRect=self.panel.screenRect, text="BACK", textSize=40)

		# Join room menu
		self.joinRoomText = Text(("CENTER", 100), "JOIN A ROOM", 40, spriteGroups=self.tabs["connectMenu"], parentRect=self.panel.screenRect)
		self.roomIDEntry = InputBox(("CENTER", 150), (300, 40), '', 'Please enter a room ID...', self.tabs["connectMenu"], self.panel.screenRect)
		self.joinButton = EllipseButton(("CENTER", 250), (300, 60), Red, Blue, spriteGroups=self.tabs["connectMenu"], parentRect=self.panel.screenRect, text="JOIN", textSize=40)
		self.backButton4 = EllipseButton(("CENTER", 320), (300, 60), Red, Blue, spriteGroups=self.tabs["connectMenu"], parentRect=self.panel.screenRect, text="BACK", textSize=40)

		# Room menu
		self.teamText = Text(("CENTER", 20), "TEAM 0", 40, spriteGroups=self.tabs["roomMenu"], parentRect=self.panel.screenRect)
		self.startGame = EllipseButton(("CENTER", self.panel.rect.height-115), (300, 60), Blue, Red, spriteGroups=self.tabs["roomMenu"], parentRect=self.panel.screenRect, text="START GAME", textSize=40)
		self.exitTeam = EllipseButton(("CENTER", self.panel.rect.height-200), (300, 60), Blue, Red, spriteGroups=self.tabs["roomMenu"], parentRect=self.panel.screenRect, text="EXIT FROM TEAM", textSize=40)

	def OpenTab(self, tab: str) -> None:
	
		if not self.game.client.isConnected:

			self.createRoomButton.Disable()
			self.connectButton.Disable()

		for sprite in self.tabs[tab]:
			
			if hasattr(self.game, "mousePosition") and hasattr(sprite, "UpdateColor"):

				sprite.UpdateColor(self.game.mousePosition)
				sprite.Rerender()

		self.tab = tab

	def UpdatePlayersInRoom(self, players):

		self.playersInTeam = players
		self.playerTexts = []

		for i, player in enumerate(self.playersInTeam):

			self.playerTexts.append(Text(("CENTER", (i+1)*60 + 23), player.name, 25, parentRect=self.panel.screenRect))

	def HandleEvents(self, event, mousePosition, keys):

		for sprite in self.tabs[self.tab]:

			if hasattr(sprite, "HandleEvents"):

				sprite.HandleEvents(event, mousePosition, keys)

		if self.tab == "mainMenu":
				
			if self.playButton.isMouseClick(event, mousePosition):

				self.OpenTab("playerMenu")

			elif self.exitButton.isMouseClick(event, mousePosition):

				self.game.Exit()

		elif self.tab == "playerMenu":
			
			if self.previous.isMouseClick(event, mousePosition):

				if self.selectedCharacter > 0:

					self.selectedCharacter -= 1

			elif self.next.isMouseClick(event, mousePosition):

				if self.selectedCharacter+1 < len(self.characters):

					self.selectedCharacter += 1

			elif self.confirmButton.isMouseClick(event, mousePosition):

				self.game.SetPlayer(self.playerNameEntry.text, CHARACTER_LIST[self.selectedCharacter])
				self.OpenTab("gameTypeMenu")

			elif self.backButton.isMouseClick(event, mousePosition):

				self.OpenTab("mainMenu")

		elif self.tab == "gameTypeMenu":

			if self.newGameButton.isMouseClick(event, mousePosition):

				self.game.Start("offline")

			elif self.createRoomButton.isMouseClick(event, mousePosition):
		
				self.OpenTab("createRoomMenu")

			elif self.connectButton.isMouseClick(event, mousePosition):
		
				self.OpenTab("connectMenu")

			elif self.backButton2.isMouseClick(event, mousePosition):

				self.OpenTab("playerMenu")

		elif self.tab == "createRoomMenu":

			if self.createButton.isMouseClick(event, mousePosition):
				
				self.game.CreateRoom()

			elif self.backButton3.isMouseClick(event, mousePosition):

				self.OpenTab("gameTypeMenu")

		elif self.tab == "connectMenu":
			
			if self.joinButton.isMouseClick(event, mousePosition):

				roomID = int(self.roomIDEntry.text) if self.roomIDEntry.text.isnumeric() else 0
				self.game.JoinRoom(roomID)

			elif self.backButton4.isMouseClick(event, mousePosition):

				self.OpenTab("gameTypeMenu")

		elif self.tab == "roomMenu":

			if self.startGame.isMouseClick(event, mousePosition):
				
				self.game.client.SendData("!START_GAME")

	def update(self):

		pass

	def draw(self, image):
		
		image.fill(BACKGROUND_COLORS["menu"])

		self.title.Draw(image)
		self.playerCountText.Draw(image)

		self.panel.Rerender()
		self.panel.image.fill((*Gray, 100))
		
		self.tabs[self.tab].draw(self.panel.image)

		if self.tab == "playerMenu":
			
			self.characters[self.selectedCharacter].Draw(self.panel.image)
			self.characterTexts[self.selectedCharacter].Draw(self.panel.image)

		elif self.tab == "roomMenu":
	
			for i in range(6):

				pygame.draw.line(self.panel.image, White, (0, (i+1)*60), (self.panel.rect.width, (i+1)*60))

			pygame.draw.line(self.panel.image, White, (0, 0), (0, self.panel.rect.height))
			pygame.draw.line(self.panel.image, White, (self.panel.rect.width, 0), (self.panel.rect.width, self.panel.rect.height))

			for playerText in self.playerTexts:

				playerText.Draw(self.panel.image)
		
		self.panel.Draw(image)
