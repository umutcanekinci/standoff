#region Import Packages

from settings import *
from path import *
from client import Client
from application import Application
from object import Object
from input_box import InputBox
from button import Button, EllipseButton
from text import Text
from tilemap import TileMap
from player import Players
from bullet import Bullets
from player_info import PlayerInfo
from team import Team

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

class Menu():

	def __init__(self, game) -> None:

		super().__init__()

		self.game = game

		self.tabs = {

			"mainMenu" : pygame.sprite.Group(),
			"gameTypeMenu" : pygame.sprite.Group(),
			"playerMenu" : pygame.sprite.Group(),
			"teamTypeMenu" : pygame.sprite.Group(),
			"createTeamMenu" : pygame.sprite.Group(),
			"joinTeamMenu" : pygame.sprite.Group(),
			"teamMenu" : pygame.sprite.Group()

		}

		self.panel = Object(size=(400, 500))
		self.title = Text(("CENTER", self.panel.rect.y-100), WINDOW_TITLE, 60, color=Red)
		self.playerCountText = Text(("CENTER", self.panel.rect.bottom+30), "You are playing in offline mode !", 24, backgroundColor=Black, color=Red)		

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

		self.creditsButton = EllipseButton(("CENTER", "CENTER"), (300, 75), Red, Blue, spriteGroups=self.tabs["mainMenu"], parentRect=self.panel.screenRect, text="CREDITS", textSize=45)
		self.playButton = EllipseButton(("CENTER", self.creditsButton.rect.y - 100), (300, 75), Red, Blue, spriteGroups=self.tabs["mainMenu"], parentRect=self.panel.screenRect, text="PLAY", textSize=45)
		self.exitButton = EllipseButton(("CENTER", self.creditsButton.rect.y + 100), (300, 75), Red, Blue, spriteGroups=self.tabs["mainMenu"], parentRect=self.panel.screenRect, text="EXIT", textSize=45)
		
		self.offlineButton = EllipseButton(("CENTER", "CENTER"), (300, 75), Red, Blue, spriteGroups=self.tabs["gameTypeMenu"], parentRect=self.panel.screenRect, text="PLAY OFFLINE", textSize=45)
		self.onlineButton = EllipseButton(("CENTER", self.offlineButton.rect.y - 100), (300, 75), Red, Blue, spriteGroups=self.tabs["gameTypeMenu"], parentRect=self.panel.screenRect, text="PLAY ONLINE", textSize=45)
		self.backButton = EllipseButton(("CENTER", self.offlineButton.rect.y + 100), (300, 75), Red, Blue, spriteGroups=[self.tabs["gameTypeMenu"], self.tabs["playerMenu"]], parentRect=self.panel.screenRect, text="BACK", textSize=45)
		
		self.playerNameText = Text(("CENTER", 60), "PLAYER NAME", 40, spriteGroups=self.tabs["playerMenu"], parentRect=self.panel.screenRect)
		self.playerNameEntry = InputBox(("CENTER", 110), (300, 40), '', 'Please enter a player name...', self.tabs["playerMenu"], self.panel.screenRect)
		self.previous = EllipseButton((75, 270), (50, 50), Blue, Red, spriteGroups=self.tabs["playerMenu"], parentRect=self.panel.screenRect)
		self.next = EllipseButton((275, 270), (50, 50), Blue, Red, spriteGroups=self.tabs["playerMenu"], parentRect=self.panel.screenRect)
		pygame.draw.polygon(self.previous.image, Red, [(0, 25), (50, 0), (50, 50)])
		pygame.draw.polygon(self.next.image, Red, [(0, 0), (50, 25), (0, 50)])

		self.joinTeamText = Text(("CENTER", 50), "JOIN TEAM", 40, spriteGroups=self.tabs["joinTeamMenu"], parentRect=self.panel.screenRect)
		self.teamIDEntry = InputBox(("CENTER", 100), (300, 40), '', 'Please enter a team ID...', self.tabs["joinTeamMenu"], self.panel.screenRect)
		self.createTeamButton = EllipseButton(("CENTER", self.panel.rect.height-285), (300, 75), Blue, Red, spriteGroups=self.tabs["joinTeamMenu"], parentRect=self.panel.screenRect, text="CREATE", textSize=45)
		self.joinButton = EllipseButton(("CENTER", self.panel.rect.height-200), (300, 75), Blue, Red, spriteGroups=self.tabs["joinTeamMenu"], parentRect=self.panel.screenRect, text="JOIN", textSize=45)
		
		self.teamText = Text(("CENTER", 20), "TEAM 0", 40, spriteGroups=self.tabs["teamMenu"], parentRect=self.panel.screenRect)
		self.startGame = EllipseButton(("CENTER", self.panel.rect.height-115), (300, 75), Blue, Red, spriteGroups=self.tabs["teamMenu"], parentRect=self.panel.screenRect, text="START GAME", textSize=45)
		self.exitTeam = EllipseButton(("CENTER", self.panel.rect.height-200), (300, 75), Blue, Red, spriteGroups=self.tabs["teamMenu"], parentRect=self.panel.screenRect, text="EXIT FROM TEAM", textSize=45)

	def OpenTab(self, tab: str) -> None:

		self.tab = tab

	def UpdatePlayersInTeam(self, players):

		self.playersInTeam = players
		self.playerTexts = []

		for i, player in enumerate(self.playersInTeam):

			self.playerTexts.append(Text(("CENTER", (i+1)*60 + 23), player.name, 25, parentRect=self.panel.screenRect))

	def HandleEvents(self, event, mousePosition, keys):

		"""playerName = self.playerNameEntry.text

		if self.client.isConnected:

			self.EnterLobby(playerName, self.characters[self.selectedCharacter])

		else:

			self.StartGameInOfflineMode(playerName, self.characters[self.selectedCharacter])"""

		for sprite in self.tabs[self.tab]:

			if hasattr(sprite, "HandleEvents"):

				sprite.HandleEvents(event, mousePosition, keys)

		if self.tab == "mainMenu":
				
			if self.playButton.isMouseClick(event, mousePosition):
		
				self.OpenTab("gameTypeMenu")

			elif self.creditsButton.isMouseClick(event, mousePosition):

				self.game.Exit()

			elif self.exitButton.isMouseClick(event, mousePosition):

				self.game.Exit()

		elif self.tab == "gameTypeMenu":

			if self.onlineButton.isMouseClick(event, mousePosition) and self.game.client.isConnected:
		
				self.OpenTab("playerMenu")

			elif self.offlineButton.isMouseClick(event, mousePosition):

				self.OpenTab("playerMenu")

			elif self.backButton.isMouseClick(event, mousePosition):

				self.OpenTab("mainMenu")

		elif self.tab == "playerMenu":

			if self.previous.isMouseOver(mousePosition):

				pygame.draw.polygon(self.previous.image, LightRed, [(0, 25), (50, 0), (50, 50)])

			else:

				pygame.draw.polygon(self.previous.image, Red, [(0, 25), (50, 0), (50, 50)])

			if self.next.isMouseOver(mousePosition):

				pygame.draw.polygon(self.next.image, LightRed, [(0, 0), (50, 25), (0, 50)])

			else:

				pygame.draw.polygon(self.next.image, Red, [(0, 0), (50, 25), (0, 50)])
			
			if self.previous.isMouseClick(event, mousePosition):

				if self.selectedCharacter > 0:

					self.selectedCharacter -= 1

			if self.next.isMouseClick(event, mousePosition):

				if self.selectedCharacter+1 < len(self.characters):

					self.selectedCharacter += 1

			if self.backButton.isMouseClick(event, mousePosition):

				self.OpenTab("gameTypeMenu")

		elif self.tab == "joinTeamMenu":
			
			if self.joinButton.isMouseClick(event, mousePosition):
				
				teamID = int(self.teamIDEntry.text) if self.teamIDEntry.text.isnumeric() else 0
				self.JoinTeam(teamID)

			elif self.createTeamButton.isMouseClick(event, mousePosition):
				
				self.client.SendData({'command' : "!CREATE_TEAM", 'value' : self.player.ID})

		elif self.tab == "teamMenu":

			if self.startGame.isMouseClick(event, self.mousePosition):
				
				self.client.SendData({'command' : "!START_GAME", 'value' : self.player.team.ID})

		elif self.tab == "game":

			if event.type == pygame.MOUSEBUTTONDOWN:

				if hasattr(self, "player"):
					
					self.player.Fire()

	def update(self):

		pass

	def draw(self, image):

		image.fill(BACKGROUND_COLORS["menu"])

		self.title.Draw(image)
		self.playerCountText.Draw(image)

		self.panel.Rerender()
		self.panel.image.fill((*Gray, 100))

		"""for sprite in self.tabs[self.tab]:

			sprite.Draw(self.panel.image)"""
		
		self.tabs[self.tab].draw(self.panel.image)

		if self.tab == "player":
			
			self.characters[self.selectedCharacter].Draw(self.panel.image)
			self.characterTexts[self.selectedCharacter].Draw(self.panel.image)

		elif self.tab == "team":
	
			for i in range(6):

				pygame.draw.line(self.panel.image, White, (0, (i+1)*60), (self.panel.rect.width, (i+1)*60))

			pygame.draw.line(self.panel.image, White, (0, 0), (0, self.panel.rect.height))
			pygame.draw.line(self.panel.image, White, (self.panel.rect.width, 0), (self.panel.rect.width, self.panel.rect.height))

			for playerText in self.playerTexts:

				playerText.Draw(self.panel.image)
		
		self.panel.Draw(image)

class Game(Application):

	def __init__(self) -> None:

		super().__init__(developMode=DEVELOP_MODE)
		self.isGameStarted = False
		self.menu = Menu(self)

		self.allSprites = pygame.sprite.Group()
		self.walls = pygame.sprite.Group()
		self.zombies = pygame.sprite.Group()
		self.map = TileMap(self, FilePath("level1", "maps", "tmx"), 2)
		self.players = Players(self)
		self.camera = Camera(self.rect.size, self.map)
		self.bullets = Bullets(self)

		self.StartClient()
		self.menu.OpenTab("mainMenu")

	def StartClient(self) -> None:

		self.client = Client(self)
		self.client.Start()

	def StartGameInOfflineMode(self, playerName, characterName):

		self.mode = "offline"
		self.player = self.players.Add(1, playerName, PLAYER_SIZE, self.map.spawnPoints[1])
		#self.zombies.add(Zombie(self.player, PLAYER_SIZE, (200, 200), self))
		self.isGameStarted = True

	def EnterLobby(self, playerName, characterName) -> None:

		self.mode = "online"
		self.client.SendData({'command' : "!ENTER_LOBBY", 'value' : [self.player.ID, playerName]})
		self.menu.OpenTab("lobby")

	def JoinTeam(self, teamID):

		self.client.SendData({'command' : "!JOIN_TEAM", 'value' : [self.player.ID, teamID]})

	def StartGame(self):

		self.isGameStarted = True
		
		for player in self.player.team:

			if not player.ID == self.player.ID:

				self.players.Add(player.ID, player.name, PLAYER_SIZE)

	def GetData(self, data) -> None:

		if data:

			print(data)

			if data['command'] == "!SET_PLAYER_ID":

				self.player = self.players.Add(data['value'], self.menu.playerNameEntry.text, PLAYER_SIZE, (data['value']*100, data['value']*100))

			elif data['command'] == "!JOIN_TEAM":

				team = data['value']

				if team:

					if not self.player.team:
						
						self.menu.teamText.UpdateText("Team " + str(team.ID))
						self.menu.OpenTab("team")

					self.player.team = team
					self.menu.UpdatePlayersInTeam(team)

				else:

					self.Exit()

			elif data['command'] == "!START_GAME":

				self.StartGame()

			elif data['command'] == "!SET_PLAYERS":
				
				self.playerList = data['value']
					
				self.menu.playerCountText.UpdateColor(Yellow)
				self.menu.playerCountText.UpdateText(str(len(self.playerList)) + " Players are Online")

			elif data['command'] == "!SET_PLAYER_RECT":

				for player in self.players:

					if player.ID == data['value'][0]:
						
						player.UpdatePosition(self.camera.Apply(data['value'][1]).center)
						break

			elif data['command'] == "!DISCONNECT":

				for player in self.players:

					if player.ID == data['value']:
						
						self.players.remove(player)
						break

	def HandleEvents(self, event: pygame.event.Event) -> None:

		if not self.isGameStarted:

			self.menu.HandleEvents(event, self.mousePosition, self.keys)

		return super().HandleEvents(event)

	def HandleExitEvents(self, event: pygame.event.Event) -> None:
		
		if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):

			if self.menu.tab == "lobby":

				self.menu.OpenTab("mainMenu")

			elif self.menu.tab == "team":

				self.menu.OpenTab("lobby")

			elif self.menu.tab == "game":
				
				if self.mode == "offline":

					self.menu.OpenTab("mainMenu")

				elif self.mode == "online":

					self.menu.OpenTab("team")

			elif self.menu.tab == "mainMenu":

				self.Exit()

	def Update(self) -> None:

		if not self.isGameStarted:

			self.menu.update()

		else:

			if hasattr(self, "player"):
				
				self.allSprites.update()
				
				self.camera.Follow(self.player.rect)

				self.DebugLog(self.players)

				if self.client.isConnected:

					self.client.SendData({'command' : "!SET_PLAYER_RECT", 'value' : [self.player.ID, pygame.Rect(self.player.hitRect.centerx - self.map.rect.x, self.player.hitRect.centery - self.map.rect.y, self.player.rect.w, self.player.rect.h)]})

	def Draw(self) -> None:

		super().Draw()

		if not self.isGameStarted:

			self.menu.draw(self.window)
			
		else:

			self.camera.Draw(self.window, self.allSprites)
			
			for player in self.players:

				if hasattr(player, "nameText"):

					self.window.blit(player.nameText.image, self.camera.Apply(player.nameText.rect))

				if self.developMode:

					pygame.draw.rect(self.window, Red, self.camera.Apply(player.rect), 2)
					pygame.draw.rect(self.window, Blue, self.camera.Apply(player.hitRect), 2)
					
	def Exit(self) -> None:

		self.client.DisconnectFromServer()
		return super().Exit()
			