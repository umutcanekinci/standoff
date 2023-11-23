#region Import Packages

try:
	
	from settings import *
	from path import *
	from client import Client
	from application import Application
	from object import Object
	from input_box import InputBox
	from button import Button
	from text import Text
	from tilemap import TileMap
	from player import Players
	from bullet import Bullets
	from player_info import PlayerInfo
	from room import Room

except ImportError as e:

	print("An error occured while importing packages:  " + str(e))

#endregion

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

class MainMenu(pygame.sprite.Group):

	def __init__(self, game) -> None:

		super().__init__()

		self.game = game
		self.panel = Object(size=(400, 500))
		self.lobby = pygame.sprite.Group()
		self.room = pygame.sprite.Group()

		self.selectedCharacter = 0
		self.characterTexts = []
		self.characters = []

		for characterName in CHARACTER_LIST:

			self.characters.append(Object(("CENTER", 270), CHARACTER_SIZE, ImagePath("idle", "characters/"+characterName), parentRect=self.panel.screenRect))

			words = characterName.split("_")
			characterName = ""

			for text in words:

				if not characterName == "":

					characterName += " "

				characterName += text.capitalize()
		
			self.characterTexts.append(Text(("CENTER", 200), characterName, 40, parentRect=self.panel.screenRect))

		self.title = Text(("CENTER", self.panel.rect.y-100), WINDOW_TITLE, 60, color=Red)

		self.playerCountText = Text(("CENTER", self.panel.rect.bottom+30), "You are playing in offline mode !", 24, backgroundColor=Black, color=Red)

		self.playerNameText = Text(("CENTER", 60), "PLAYER NAME", 40, spriteGroups=self, parentRect=self.panel.screenRect)
		self.playerNameEntry = InputBox(("CENTER", 110), (300, 40), '', 'Please enter a player name...', self, self.panel.screenRect)
		self.playButton = Button(("CENTER", self.panel.rect.height-115), (300, 75), spriteGroups=self, parentRect=self.panel.screenRect, text="PLAY", textSize=45)
		
		self.previous = Button((75, 270), (50, 50), spriteGroups=self, parentRect=self.panel.screenRect)
		self.next = Button((275, 270), (50, 50), spriteGroups=self, parentRect=self.panel.screenRect)
		
		pygame.draw.polygon(self.previous.image, Red, [(0, 25), (50, 0), (50, 50)])
		pygame.draw.polygon(self.next.image, Red, [(0, 0), (50, 25), (0, 50)])

		self.joinRoomText = Text(("CENTER", 50), "JOIN ROOM", 40, spriteGroups=self.lobby, parentRect=self.panel.screenRect)
		self.roomIDEntry = InputBox(("CENTER", 100), (300, 40), '', 'Please enter a room ID...', self.lobby, self.panel.screenRect)
		self.createRoomButton = Button(("CENTER", self.panel.rect.height-200), (300, 75), spriteGroups=self.lobby, parentRect=self.panel.screenRect, text="CREATE", textSize=45)
		self.joinButton = Button(("CENTER", self.panel.rect.height-115), (300, 75), spriteGroups=self.lobby, parentRect=self.panel.screenRect, text="JOIN", textSize=45)
		
		self.roomText = Text(("CENTER", 20), "ROOM 0", 40, spriteGroups=self.room, parentRect=self.panel.screenRect)
		self.startGame = Button(("CENTER", self.panel.rect.height-115), (300, 75), spriteGroups=self.room, parentRect=self.panel.screenRect, text="START GAME", textSize=45)
		self.playersInRoom = []

		self.playButton.SetColor(Black)
		self.joinButton.SetColor(Black)

	def draw(self, image):
		
		self.title.Draw(image)
		self.playerCountText.Draw(image)

		self.panel.Rerender()
		self.panel.image.fill((*Gray, 100))

		if self.game.tab == "mainMenu":

			super().draw(self.panel.image)
			self.characters[self.selectedCharacter].Draw(self.panel.image)
			self.characterTexts[self.selectedCharacter].Draw(self.panel.image)

		elif self.game.tab == "lobby":

			self.lobby.draw(self.panel.image)

		elif self.game.tab == "room":
	
			for i in range(6):

				pygame.draw.line(self.panel.image, White, (0, (i+1)*60), (self.panel.rect.width, (i+1)*60))

			pygame.draw.line(self.panel.image, White, (0, 0), (0, self.panel.rect.height))
			pygame.draw.line(self.panel.image, White, (self.panel.rect.width, 0), (self.panel.rect.width, self.panel.rect.height))

			for i, player in enumerate(self.playersInRoom):
				print(i, player.name)
				Text(("CENTER", 50*i), player.name, 25, spriteGroups=self.room, parentRect=self.panel.screenRect).Draw(self.panel.image)
				
			self.room.draw(self.panel.image)
		
		self.panel.Draw(image)

class Game(Application):

	def __init__(self) -> None:

		super().__init__(developMode=DEVELOP_MODE)

		self.menu = MainMenu(self)

		self.allSprites = pygame.sprite.Group()
		self.walls = pygame.sprite.Group()
		self.zombies = pygame.sprite.Group()
		self.map = TileMap(self, FilePath("level1", "maps", "tmx"), 2)
		self.players = Players(self)
		self.camera = Camera(self.rect.size, self.map)
		self.bullets = Bullets(self)

		self.StartClient()
		
	def StartClient(self) -> None:

		self.client = Client(self)
		self.client.Start()
		self.OpenTab("mainMenu")

	def StartGameInOfflineMode(self, playerName, characterName):

		self.mode = "offline"
		self.player = self.players.Add(1, playerName, TILE_SIZE, self.map.spawnPoints[1])
		#self.zombies.add(Zombie(self.player, TILE_SIZE, (200, 200), self))
		self.OpenTab("game")

	def EnterLobby(self, playerName, characterName) -> None:

		self.mode = "online"
		self.client.SendData({'command' : "!ENTER_LOBBY", 'value' : [self.player.ID, playerName]})
		self.OpenTab("lobby")

	def JoinRoom(self, roomID):

		self.client.SendData({'command' : "!JOIN_ROOM", 'value' : [self.player.ID, roomID]})

	def GetData(self, data) -> None:

		if data:

			print(data)

			if data['command'] == "!SET_PLAYER_ID":

				self.player = self.players.Add(data['value'], self.menu.playerNameEntry.text, TILE_SIZE, (data['value']*100, data['value']*100))

			elif data['command'] == "!JOIN_ROOM":

				room = data['value']

				if room:

					if not self.player.room:
						
						self.menu.roomText.UpdateText("Room " + str(room.ID))
						self.OpenTab("room")

					self.player.room = room
					self.menu.playersInRoom = room

				else:

					pass

			elif data['command'] == "!START_GAME":

				self.OpenTab("game")

			elif data['command'] == "!SET_PLAYERS":
				
				self.playerList = data['value']
					
				self.menu.playerCountText.UpdateColor(Yellow)
				self.menu.playerCountText.UpdateText(str(len(self.playerList)) + " Players are Online")

			elif data['command'] == "!SET_PLAYER_RECT":
				return
				for player in self.players:

					if player.ID == data['value'][0]:
						
						player.UpdatePosition(data['value'][1].center)
						break

			elif data['command'] == "!DISCONNECT":

				for player in self.players:

					if player.ID == data['value']:
						
						self.players.remove(player)
						break

	def HandleEvents(self, event: pygame.event.Event) -> None:

		if self.tab == "mainMenu":
			
			self.menu.playerNameEntry.HandleEvents(event, self.mousePosition, self.keys)
			

			if self.menu.previous.isMouseOver(self.mousePosition):

				pygame.draw.polygon(self.menu.previous.image, LightRed, [(0, 25), (50, 0), (50, 50)])

			else:

				pygame.draw.polygon(self.menu.previous.image, Red, [(0, 25), (50, 0), (50, 50)])

			if self.menu.next.isMouseOver(self.mousePosition):

				pygame.draw.polygon(self.menu.next.image, LightRed, [(0, 0), (50, 25), (0, 50)])

			else:

				pygame.draw.polygon(self.menu.next.image, Red, [(0, 0), (50, 25), (0, 50)])
			
			if self.menu.previous.isMouseClick(event, self.mousePosition):

				if self.menu.selectedCharacter > 0:

					self.menu.selectedCharacter -= 1

			if self.menu.next.isMouseClick(event, self.mousePosition):

				if self.menu.selectedCharacter+1 < len(self.menu.characters):

					self.menu.selectedCharacter += 1

			if self.menu.playButton.isMouseOver(self.mousePosition):

				self.menu.playButton.SetColor(Gray)

			else:

				self.menu.playButton.SetColor(Black)
			
			if self.menu.playButton.isMouseClick(event, self.mousePosition):
		
				playerName = self.menu.playerNameEntry.text

				if self.client.isConnected:

					self.EnterLobby(playerName, self.menu.characters[self.menu.selectedCharacter])

				else:

					self.StartGameInOfflineMode(playerName, self.menu.characters[self.menu.selectedCharacter])

		elif self.tab == "lobby":

			self.menu.roomIDEntry.HandleEvents(event, self.mousePosition, self.keys)
			
			if self.menu.joinButton.isMouseOver(self.mousePosition):

				self.menu.joinButton.SetColor(Gray)

			else:

				self.menu.joinButton.SetColor(Black)
			
			if self.menu.joinButton.isMouseClick(event, self.mousePosition):
				
				roomID = int(self.menu.roomIDEntry.text) if self.menu.roomIDEntry.text.isnumeric() else 0
				self.JoinRoom(roomID)

			elif self.menu.createRoomButton.isMouseClick(event, self.mousePosition):
				
				self.client.SendData({'command' : "!CREATE_ROOM", 'value' : self.player.ID})

			if self.menu.createRoomButton.isMouseOver(self.mousePosition):

				self.menu.createRoomButton.SetColor(Gray)

			else:

				self.menu.createRoomButton.SetColor(Black)
			


		elif self.tab == "room":
			
			if self.menu.startGame.isMouseOver(self.mousePosition):

				self.menu.startGame.SetColor(Gray)

			else:

				self.menu.startGame.SetColor(Black)
			
			if self.menu.startGame.isMouseClick(event, self.mousePosition):
				
				self.client.SendData({'command' : "!START_GAME", 'value' : self.player.room.ID})

		elif self.tab == "game":

			if event.type == pygame.MOUSEBUTTONDOWN:

				if hasattr(self, "player"):
					
					self.player.Fire()

		return super().HandleEvents(event)

	def HandleExitEvents(self, event: pygame.event.Event) -> None:
		
		if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):

			if self.tab == "lobby":

				self.OpenTab("mainMenu")

			elif self.tab == "room":

				self.OpenTab("lobby")

			elif self.tab == "game":
				
				if self.mode == "offline":

					self.OpenTab("mainMenu")

				elif self.mode == "online":

					self.OpenTab("room")

			elif self.tab == "mainMenu":

				self.Exit()

	def Update(self) -> None:

		if self.tab == "mainMenu" or self.tab == "lobby":

			self.menu.update()

		elif self.tab == "game":

			if hasattr(self, "player"):
				
				self.allSprites.update()
				
				self.camera.Follow(self.player.rect)

				self.DebugLog(self.players)

				if self.client.isConnected:

					self.client.SendData({'command' : "!PLAYER_RECT", 'value' : [self.player.ID, pygame.Rect(self.player.hitRect.centerx - self.map.rect.x, self.player.hitRect.centery - self.map.rect.y, self.player.rect.w, self.player.rect.h)]})

	def Draw(self) -> None:

		super().Draw()

		if self.tab == "game":
			
			self.camera.Draw(self.window, self.allSprites)
			
			for player in self.players:

				if hasattr(player, "nameText"):

					self.window.blit(player.nameText.image, self.camera.Apply(player.nameText.rect))

				if self.developMode:

					pygame.draw.rect(self.window, Red, self.camera.Apply(player.rect), 2)
					pygame.draw.rect(self.window, Blue, self.camera.Apply(player.hitRect), 2)
					

		else:

			self.menu.draw(self.window)

	def Exit(self) -> None:

		self.client.DisconnectFromServer()
		return super().Exit()
			