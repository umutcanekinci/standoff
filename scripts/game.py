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

			self.characters.append(Object(("CENTER", 195), CHARACTER_SIZE, ImagePath("idle", "characters/"+characterName), parentRect=self.panel.screenRect))

			words = characterName.split("_")
			characterName = ""

			for text in words:

				if not characterName == "":

					characterName += " "

				characterName += text.capitalize()
		
			self.characterTexts.append(Text(("CENTER", 145), characterName, 40, parentRect=self.panel.screenRect))

		self.creditsButton = EllipseButton(("CENTER", "CENTER"), (300, 75), Red, Blue, spriteGroups=self.tabs["mainMenu"], parentRect=self.panel.screenRect, text="CREDITS", textSize=45, isActive=False)
		self.playButton = EllipseButton(("CENTER", self.creditsButton.rect.y - 90), (300, 75), Red, Blue, spriteGroups=self.tabs["mainMenu"], parentRect=self.panel.screenRect, text="PLAY", textSize=45)
		self.exitButton = EllipseButton(("CENTER", self.creditsButton.rect.y + 90), (300, 75), Red, Blue, spriteGroups=self.tabs["mainMenu"], parentRect=self.panel.screenRect, text="EXIT", textSize=45)
		
		self.offlineButton = EllipseButton(("CENTER", "CENTER"), (300, 75), Red, Blue, spriteGroups=self.tabs["gameTypeMenu"], parentRect=self.panel.screenRect, text="PLAY OFFLINE", textSize=45)
		self.onlineButton = EllipseButton(("CENTER", self.offlineButton.rect.y - 90), (300, 75), Red, Blue, spriteGroups=self.tabs["gameTypeMenu"], parentRect=self.panel.screenRect, text="PLAY ONLINE", textSize=45)
		self.backButton = EllipseButton(("CENTER", self.offlineButton.rect.y + 90), (300, 75), Red, Blue, spriteGroups=self.tabs["gameTypeMenu"], parentRect=self.panel.screenRect, text="BACK", textSize=45)
		
		self.playerNameText = Text(("CENTER", 40), "PLAYER NAME", 40, spriteGroups=self.tabs["playerMenu"], parentRect=self.panel.screenRect)
		self.playerNameEntry = InputBox(("CENTER", 90), (300, 40), '', 'Please enter a player name...', self.tabs["playerMenu"], self.panel.screenRect)
		self.previous = TriangleButton((75, self.backButton.rect.y - 110), (50, 50), Blue, Red, spriteGroups=self.tabs["playerMenu"], parentRect=self.panel.screenRect, rotation="LEFT")
		self.next = TriangleButton((275, self.backButton.rect.y - 110), (50, 50), Blue, Red, spriteGroups=self.tabs["playerMenu"], parentRect=self.panel.screenRect)
		self.confirmButton = EllipseButton(("CENTER", self.backButton.rect.y), (300, 75), Red, Blue, spriteGroups=[self.tabs["playerMenu"]], parentRect=self.panel.screenRect, text="CONFIRM", textSize=45)
		self.backButton2 = EllipseButton(("CENTER", self.confirmButton.rect.y + 90), (300, 75), Red, Blue, spriteGroups=[self.tabs["playerMenu"]], parentRect=self.panel.screenRect, text="BACK", textSize=45)

		self.joinTeamButton = EllipseButton(("CENTER", 100), (300, 75), Red, Blue, spriteGroups=self.tabs["teamTypeMenu"], parentRect=self.panel.screenRect, text="JOIN A TEAM", textSize=45)
		self.createTeamButton = EllipseButton(("CENTER", 190), (300, 75), Red, Blue, spriteGroups=self.tabs["teamTypeMenu"], parentRect=self.panel.screenRect, text="CREATE A TEAM", textSize=45)
		self.soloModeButton = EllipseButton(("CENTER", 280), (300, 75), Red, Blue, spriteGroups=self.tabs["teamTypeMenu"], parentRect=self.panel.screenRect, text="SOLO MODE", textSize=45)
		self.backButton3 = EllipseButton(("CENTER", 370), (300, 75), Red, Blue, spriteGroups=[self.tabs["teamTypeMenu"]], parentRect=self.panel.screenRect, text="BACK", textSize=45)
		
		self.joinTeamText = Text(("CENTER", 50), "JOIN TEAM", 40, spriteGroups=self.tabs["joinTeamMenu"], parentRect=self.panel.screenRect)
		self.teamIDEntry = InputBox(("CENTER", 100), (300, 40), '', 'Please enter a team ID...', self.tabs["joinTeamMenu"], self.panel.screenRect)
		self.createTeamButton = EllipseButton(("CENTER", self.panel.rect.height-285), (300, 75), Blue, Red, spriteGroups=self.tabs["joinTeamMenu"], parentRect=self.panel.screenRect, text="CREATE", textSize=45)
		self.joinButton = EllipseButton(("CENTER", self.panel.rect.height-200), (300, 75), Blue, Red, spriteGroups=self.tabs["joinTeamMenu"], parentRect=self.panel.screenRect, text="JOIN", textSize=45)
		
		self.teamText = Text(("CENTER", 20), "TEAM 0", 40, spriteGroups=self.tabs["teamMenu"], parentRect=self.panel.screenRect)
		self.startGame = EllipseButton(("CENTER", self.panel.rect.height-115), (300, 75), Blue, Red, spriteGroups=self.tabs["teamMenu"], parentRect=self.panel.screenRect, text="START GAME", textSize=45)
		self.exitTeam = EllipseButton(("CENTER", self.panel.rect.height-200), (300, 75), Blue, Red, spriteGroups=self.tabs["teamMenu"], parentRect=self.panel.screenRect, text="EXIT FROM TEAM", textSize=45)

	def OpenTab(self, tab: str) -> None:

		for sprite in self.tabs[tab]:
			
			if hasattr(self.game, "mousePosition") and hasattr(sprite, "UpdateColor"):

				sprite.UpdateColor(self.game.mousePosition)
				sprite.Rerender()

		self.tab = tab

	def UpdatePlayersInTeam(self, players):

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
		
				if not self.game.client.isConnected:

					self.onlineButton.Disable() 

				self.OpenTab("gameTypeMenu")

			elif self.creditsButton.isMouseClick(event, mousePosition):

				self.game.Exit()

			elif self.exitButton.isMouseClick(event, mousePosition):

				self.game.Exit()

		elif self.tab == "gameTypeMenu":

			if self.onlineButton.isMouseClick(event, mousePosition) and self.game.client.isConnected:
		
				self.game.mode = "online"
				self.OpenTab("playerMenu")

			elif self.offlineButton.isMouseClick(event, mousePosition):

				self.game.mode = "offline"
				self.OpenTab("playerMenu")

			elif self.backButton.isMouseClick(event, mousePosition):

				self.OpenTab("mainMenu")

		elif self.tab == "playerMenu":
			
			if self.previous.isMouseClick(event, mousePosition):

				if self.selectedCharacter > 0:

					self.selectedCharacter -= 1

			elif self.next.isMouseClick(event, mousePosition):

				if self.selectedCharacter+1 < len(self.characters):

					self.selectedCharacter += 1

			elif self.confirmButton.isMouseClick(event, mousePosition):

				if self.game.mode == "online":

					self.game.EnterLobby(self.playerNameEntry.text, self.characters[self.selectedCharacter])
				
				elif self.game.mode == "offline":
				
					self.game.StartGameInOfflineMode(self.playerNameEntry.text, self.characters[self.selectedCharacter])

			elif self.backButton2.isMouseClick(event, mousePosition):

				self.OpenTab("gameTypeMenu")

		elif self.tab == "teamTypeMenu":

			if self.joinTeamButton.isMouseClick(event, mousePosition):

				self.OpenTab("joinTeamMenu")

			elif self.createTeamButton.isMouseClick(event, mousePosition):

				self.OpenTab("createTeamMenu")

			elif self.soloModeButton.isMouseClick(event, mousePosition):

				self.OpenTab("joinTeamMenu")

			elif self.backButton3.isMouseClick(event, mousePosition):

				self.OpenTab("playerMenu")

		elif self.tab == "joinTeamMenu":
			
			if self.joinButton.isMouseClick(event, mousePosition):
				
				teamID = int(self.teamIDEntry.text) if self.teamIDEntry.text.isnumeric() else 0
				self.game.JoinTeam(teamID)

			elif self.createTeamButton.isMouseClick(event, mousePosition):
				
				self.game.client.SendData({'command' : "!CREATE_TEAM", 'value' : self.game.player.ID})

		elif self.tab == "teamMenu":

			if self.startGame.isMouseClick(event, mousePosition):
				
				self.game.client.SendData({'command' : "!START_GAME", 'value' : self.game.player.team.ID})

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

		elif self.tab == "teamMenu":
	
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
	
		self.player = self.players.Add(1, playerName, PLAYER_SIZE, self.map.spawnPoints[1])
		#self.zombies.add(Zombie(self.player, PLAYER_SIZE, (200, 200), self))
		self.isGameStarted = True

	def EnterLobby(self, playerName, characterName) -> None:

		self.client.SendData({'command' : "!ENTER_LOBBY", 'value' : [self.player.ID, playerName]})
		self.menu.OpenTab("teamTypeMenu")

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

					if not hasattr(self.player, "team") or not self.player.team:
						
						self.menu.teamText.UpdateText("Team " + str(team.ID))
						self.menu.OpenTab("teamMenu")

					self.player.team = team
					self.menu.UpdatePlayersInTeam(team)

				else:

					self.Exit()

			elif data['command'] == "!START_GAME":

				self.StartGame()

			elif data['command'] == "!SET_PLAYERS":
				
				self.playerList = data['value']
					
				self.menu.playerCountText.SetColor(Yellow)
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

		else:

			self.player.HandleEvents(event, self.mousePosition, self.keys)

		return super().HandleEvents(event)

	def HandleExitEvents(self, event: pygame.event.Event) -> None:
		
		if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):

			if self.isGameStarted:

				self.isGameStarted = False
				self.menu.OpenTab("mainMenu")

			elif self.menu.tab == "gameTypeMenu":

				self.menu.OpenTab("mainMenu")

			elif self.menu.tab == "playerMenu":

				self.menu.OpenTab("gameTypeMenu")

			elif self.menu.tab == "teamTypeMenu":
				
				self.menu.OpenTab("playerMenu")

			elif self.menu.tab == "createTeamMenu":
				
				self.menu.OpenTab("teamTypeMenu")

			elif self.menu.tab == "joinTeamMenu":
				
				self.menu.OpenTab("teamTypeMenu")

			elif self.menu.tab == "mainMenu":

				self.Exit()

	def Update(self) -> None:

		if not self.isGameStarted:

			self.menu.update()

		else:
				
			self.allSprites.update()
			
			self.camera.Follow(self.player.rect)

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
			