from settings import *
from object import Object
from input_box import InputBox
from button import TriangleButton, EllipseButton
from text import Text
from path import ImagePath

class Menu():

	def __init__(self, game) -> None:

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

		#region Create gui objects
			
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
		self.roomText = Text(("CENTER", 20), "ROOM 0", 40, spriteGroups=self.tabs["roomMenu"], parentRect=self.panel.screenRect)
		self.leaveRoom = EllipseButton(("CENTER", self.panel.rect.height-200), (300, 60), Blue, Red, spriteGroups=self.tabs["roomMenu"], parentRect=self.panel.screenRect, text="LEAVE ROOM", textSize=40)

		#endregion

	def OpenTab(self, tab: str) -> None:
	
		if not self.game.client.isConnected:

			self.createRoomButton.Disable()
			self.connectButton.Disable()

		else:

			self.createRoomButton.Enable()
			self.connectButton.Enable()
		
		for sprite in self.tabs[tab]:
			
			if hasattr(self.game, "mousePosition") and hasattr(sprite, "UpdateColor"):

				sprite.UpdateColor(self.game.mousePosition)
				sprite.Rerender()

		self.tab = tab

	def UpdatePlayersInRoom(self, players):

		self.playerTexts = []
		areAllReady = True

		for i, player in enumerate(players):
			
			if player.isRuler:

				color = Red
				text = player.name + " (Ruler)"

			elif player.isReady:

				color = Green
				text = player.name + " (Ready)"

			else:

				color = White
				text = player.name
				areAllReady = False

			self.playerTexts.append(Text(("CENTER", (i+1)*60 + 23), text, 25, color=color, parentRect=self.panel.screenRect))

		# firstly remove the existing button to update with new one
		if hasattr(self, 'startGame'):

			self.startGame.kill()

		if hasattr(self, 'ready'):

				self.ready.kill()

		if hasattr(self, 'unready'):

				self.unready.kill()

		# if the client is ruler of the room it should have start button else ready button
		if self.game.playerInfo.isRuler:

			self.startGame = EllipseButton(("CENTER", self.panel.rect.height-115), (300, 60), Green, Red, spriteGroups=self.tabs["roomMenu"], parentRect=self.panel.screenRect, text="START GAME", textSize=40)

			if not areAllReady: # disable start button if others arent ready 

				self.startGame.Disable()
		
		else:
	
			if self.game.playerInfo.isReady:

				self.unready = EllipseButton(("CENTER", self.panel.rect.height-115), (300, 60), Red, Blue, spriteGroups=self.tabs["roomMenu"], parentRect=self.panel.screenRect, text="UNREADY", textSize=40)

			else:

				self.ready = EllipseButton(("CENTER", self.panel.rect.height-115), (300, 60), Green, Red, spriteGroups=self.tabs["roomMenu"], parentRect=self.panel.screenRect, text="READY", textSize=40)
			
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
				
				self.game.mode = "offline"
				self.OpenTab("createRoomMenu")

			elif self.createRoomButton.isMouseClick(event, mousePosition):
		
				self.game.mode = "online"
				self.OpenTab("createRoomMenu")

			elif self.connectButton.isMouseClick(event, mousePosition):
		
				self.game.mode = "online"
				self.OpenTab("connectMenu")

			elif self.backButton2.isMouseClick(event, mousePosition):

				self.OpenTab("playerMenu")

		elif self.tab == "createRoomMenu":

			if self.createButton.isMouseClick(event, mousePosition):
				
				mapName = "level2"
				self.game.CreateRoom(mapName)

			elif self.backButton3.isMouseClick(event, mousePosition):

				self.OpenTab("gameTypeMenu")

		elif self.tab == "connectMenu":
			
			if self.joinButton.isMouseClick(event, mousePosition):

				roomID = int(self.roomIDEntry.text) if self.roomIDEntry.text.isnumeric() else 0
				self.game.JoinRoom(roomID)

			elif self.backButton4.isMouseClick(event, mousePosition):

				self.OpenTab("gameTypeMenu")

		elif self.tab == "roomMenu":

			if self.game.playerInfo.isRuler:

				if self.startGame.isMouseClick(event, mousePosition):
					
					self.game.client.SendData("!START_GAME")

			else:

				if self.game.playerInfo.isReady:

					if self.unready.isMouseClick(event, mousePosition):

						self.game.client.SendData("!GET_UNREADY")

				else:

					if self.ready.isMouseClick(event, mousePosition):

						self.game.client.SendData("!GET_READY")

			if self.leaveRoom.isMouseClick(event, mousePosition):

				self.game.client.SendData("!LEAVE_ROOM")

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
