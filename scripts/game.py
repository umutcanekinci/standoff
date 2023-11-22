#region Import Packages

try:
	
	from settings import *
	import math
	from pygame.math import Vector2 as Vec
	from path import *
	
	from client import Client
	from object import Object, GetImage
	from application import Application
	from text import Text
	import pytmx
	from player_info import PlayerInfo
	from room import Room

except ImportError as e:

	print("An error occured while importing packages:  " + str(e))

#endregion

#region Functions

def CollideHitRect(one, two):
	return one.hitRect.colliderect(two.rect)

#endregion

class Button(Object):

	def __init__(self, position: tuple=("CENTER", "CENTER"), size: tuple=(0, 0), imagePath: ImagePath=None, spriteGroups: list=[], parentRect: pygame.Rect=None, text: str="", textSize: int=20, textColor: tuple=White, textFontPath: pygame.font.Font=None):

		super().__init__(position, size, imagePath, spriteGroups, parentRect)

		if text:

			self.SetText(text, textSize, True, textColor, None, textFontPath)

	def SetText(self, text: str, textSize: int, antialias: bool, color: tuple, backgroundColor, fontPath: pygame.font.Font = None) -> None:

		self.text = Text(("CENTER", "CENTER"), text, textSize, antialias, color, backgroundColor, fontPath, (), self.screenRect)
		self.text.Draw(self.image)

	def SetColor(self, color: tuple):

		self.image.fill(color)
		self.text.Draw(self.image)

class InputBox(Object):

	def __init__(self, position, size, text='', inactiveText = '', spriteGroups: list=[], parentRect: pygame.Rect=None):

		super().__init__(position, size, spriteGroups=spriteGroups, parentRect=parentRect)
		
		self.color = pygame.Color('dodgerblue2') # ('lightskyblue3')
		self.text = text
		self.inactiveText = inactiveText
		self.active = True
		
		self.Rerender()

	def HandleEvents(self, event, mousePosition, keys):

		if event.type == pygame.MOUSEBUTTONDOWN:

			# If the user clicked on the input_box rect.
			if self.screenRect.collidepoint(mousePosition):

				# Toggle the active variable.
				self.active = True #not self.active

			else:

				self.active = False

			# Change the current color of the input box.
			self.color = pygame.Color('dodgerblue2') if self.active else Gray
			self.Rerender()

		if event.type == pygame.KEYDOWN:

			if self.active:

				if event.key == pygame.K_BACKSPACE:

					self.text = self.text[:-1]

				elif self.textSurface.get_width() < self.rect.width - 25:

					self.text += event.unicode

				self.Rerender()

	def Rerender(self):

		self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA)

		if self.active or self.text:
			
			self.textSurface = pygame.font.Font(None, 32).render(self.text, True, self.color)
		
		else:

			self.textSurface = pygame.font.Font(None, 20).render(self.inactiveText, True, self.color)
	
		pygame.draw.rect(self.image, self.color, pygame.Rect((0, 0), self.rect.size), 2)
		self.image.blit(self.textSurface, (self.rect.width/2-self.textSurface.get_width()/2, self.rect.height/2-self.textSurface.get_height()/2))

class Tile(Object):
	
	def __init__(self, tileType, rowNumber, columnNumber, spriteGroups) -> None:
		
		super().__init__((TILE_SIZE*columnNumber, TILE_SIZE*rowNumber), (TILE_SIZE, TILE_SIZE), ImagePath("tile_" + str(tileType), "tiles"), spriteGroups)

class Wall(Tile):

	def __init__(self, tileType, rowNumber, columnNumber, spriteGroups) -> None:
		
		super().__init__(tileType, rowNumber, columnNumber, spriteGroups)
		self.image = GetImage(ImagePath("tile_383", "tiles"))

class Tree(Tile):

	def __init__(self, rowNumber, columnNumber, spriteGroups) -> None:
		
		super().__init__(rowNumber, columnNumber, spriteGroups)
		self.HP = 100

	def LoseHP(self, value):

		self.HP -= value

		if self.HP <= 0:

			self.kill()

class Bullet(Object):

	def __init__(self, position, screenPosition, targetPosition, game) -> None:

		super().__init__(position, (10, 5), spriteGroups=[game.bullets, game.allSprites])

		self.rect = self.image.get_rect(center=position)
		self.image.fill(White)
		self.velocity = (Vec(targetPosition) - Vec(screenPosition.center)).normalize()

	def Rotate(self, angle):

		self.image = pygame.transform.rotate(self.image, angle)
		self.rect = self.image.get_rect(center=self.rect.center)

	def Move(self):

		self.rect.topleft += self.velocity

	def update(self) -> None:
		
		self.Move()

class Player(Object):

	def __init__(self, ID, name, size, position, game) -> None:

		super().__init__(position, (size, size), {}, (game.players, game.allSprites))
		
		self.ID = ID
		self.name = name
		self.state = "menu"
		self.HP = 100
		self.game = game

		self.map = game.map
		self.camera = game.camera
		self.nameText = Text((0, 0), self.name, 25, color=Yellow)
		
		# Player graphic
		self.originalImage = GetImage(ImagePath("idle", "characters/hitman"))
		self.image = self.originalImage.copy()

		self.hitRect = PLAYER_HIT_RECT
		self.hitRect.center = self.rect.center

		#region Physical Variables

		# Force (Newton)
		self.force = Vec(3, 3)
		self.frictionalForce = Vec(-1., -1.)
		self.netForce = Vec()

		# Acceleration (m/s**2)
		self.acceleration = Vec()
		self.maxAcceleration = 5

		# Velocity / Speed (m/s*2)
		self.velocity = Vec()
		self.maxMovSpeed = 5

		# Rotation
		self.forceRotation = Vec()

		# Weight (Kilogram)
		self.density = 25 # d (kg/piksel**2)
		self.weight = (self.rect.width/TILE_SIZE * self.rect.height/TILE_SIZE) * self.density # m = d*v

		#endregion

	def LoseHP(self, value):

		self.HP -= value

		if self.HP <= 0:

			self.kill()

	def Rotate(self):

		distanceX = self.game.mousePosition[0] - self.game.camera.Apply(self.rect)[0]
		distanceY = self.game.mousePosition[1] - self.game.camera.Apply(self.rect)[1]

		self.angle = math.atan2(-distanceY, distanceX)
		self.angle = math.degrees(self.angle)  # Convert radians to degrees

		self.image = pygame.transform.rotate(self.originalImage, self.angle)
		
		self.rect = self.image.get_rect(center=self.rect.center)

	def Move(self):

		#region Get the rotation of force

		if self.game.keys[pygame.K_LEFT] or self.game.keys[pygame.K_a]:

			self.forceRotation.x = -1

		elif self.game.keys[pygame.K_RIGHT] or self.game.keys[pygame.K_d]:
			
			self.forceRotation.x = 1

		else:

			self.forceRotation.x = 0

		if self.game.keys[pygame.K_UP] or self.game.keys[pygame.K_w]:
			
			self.forceRotation.y = -1

		elif self.game.keys[pygame.K_DOWN] or self.game.keys[pygame.K_s]:
			
			self.forceRotation.y = 1

		else:

			self.forceRotation.y = 0

		#endregion

		# Normalize force rotation
		if self.forceRotation.length() != 0:
		
			self.forceRotation.normalize()

		# Calculate net force
		self.netForce = self.force.elementwise() * self.forceRotation

		# apply frictional force
		if self.velocity.length() != 0:

			if abs(self.netForce.x) > self.frictionalForce.x:

				self.netForce.x += self.frictionalForce.x * self.velocity.normalize().x * self.game.deltaTime

			if abs(self.netForce.y) > self.frictionalForce.y:

				self.netForce.y += self.frictionalForce.y * self.velocity.normalize().y * self.game.deltaTime
			
		# Calculate acceleration
		self.acceleration = self.netForce / self.weight

		# Clamp acceleration
		self.acceleration.x = max(-self.maxAcceleration, min(self.maxAcceleration, self.acceleration.x))
		self.acceleration.y = max(-self.maxAcceleration, min(self.maxAcceleration, self.acceleration.y))

		# Update velocity
		self.velocity += self.acceleration * self.game.deltaTime

		# Limit velocity to a maximum speed
		if self.velocity.length() > self.maxMovSpeed:

			self.velocity.scale_to_length(self.maxMovSpeed)

		if abs(self.velocity.x) < 0.01:

			self.velocity.x = 0

		if abs(self.velocity.y) < 0.01:
			
			self.velocity.y = 0
		
		self.delta = (self.velocity * self.game.deltaTime) + (0.5 * self.acceleration * self.game.deltaTime * self.game.deltaTime)

		self.hitRect.centerx += self.delta.x
		self.CollideWithWalls('x')
		self.hitRect.centery += self.delta.y
		self.CollideWithWalls('y')

		"""
		for wall in self.game.walls:

			if self.hitRect.colliderect(wall.rect):

				if self.delta.x > 0:

					self.hitRect.centerx = wall.rect.left - self.hitRect.width / 2 - 5
				
				elif self.delta.x < 0:

					self.hitRect.centerx = wall.rect.right + self.hitRect.width / 2 + 5

				self.delta.x = 0
				self.velocity.x = 0
				self.acceleration.x = 0

		self.hitRect.centery += self.delta.y

		for wall in self.map.walls:

			if self.hitRect.colliderect(wall.rect):

				if self.delta.y > 0:

					self.hitRect.centery = wall.rect.top - self.hitRect.height / 2 - 5
				
				elif self.delta.y < 0:

					self.hitRect.centery = wall.rect.bottom + self.hitRect.height / 2 + 5

				self.delta.y = 0
				self.velocity.y = 0
				self.acceleration.y = 0
		"""
				
		self.UpdatePosition(self.hitRect.center)

	def CollideWithWalls(self, dir):

		if dir == 'x':

			hits = pygame.sprite.spritecollide(self, self.game.walls, False, CollideHitRect)
			
			if hits:

				if self.velocity.x > 0:

					self.hitRect.x = hits[0].rect.left - self.hitRect.width / 2.0

				if self.velocity.x < 0:

					self.hitRect.x = hits[0].rect.right + self.hitRect.width / 2.0

				self.velocity.x = 0

				self.hitRect.centerx = self.hitRect.x

		if dir == 'y':

			hits = pygame.sprite.spritecollide(self, self.game.walls, False, CollideHitRect)

			if hits:

				if self.velocity.y > 0:

					self.hitRect.y = hits[0].rect.top - self.hitRect.height / 2.0

				if self.velocity.y < 0:

					self.hitRect.y = hits[0].rect.bottom + self.hitRect.height / 2.0

				self.velocity.y = 0
				self.hitRect.centery = self.hitRect.y

	def Fire(self):

		time = pygame.time.get_ticks() / 1000
		fireRate = .1

		if not hasattr(self, "lastFireTime"):

			self.lastFireTime = 0

		if time - self.lastFireTime > fireRate:

			bullet = Bullet(self.rect.center, self.camera.Apply(self.rect), self.game.mousePosition, self.game)
			bullet.Rotate(self.angle)
			self.game.bullets.add(bullet)
			self.lastFireTime = time

	def UpdatePosition(self, position):

		self.hitRect.center = self.rect.center = position
		self.nameText.rect.center = (self.hitRect.centerx, self.hitRect.top - 30)
	
	def update(self):
		
		if hasattr(self.game, "player") and self.game.player.ID == self.ID:

			self.Rotate()
			self.Move()

class Zombie(pygame.sprite.Sprite):

	def __init__(self, target, size, position, game) -> None:

		super().__init__(game.allSprites, game.zombies)

		self.target = target
		self.HP = 100
		self.game = game
		self.map = game.map
		self.camera = game.camera
		self.name = "Zombie"
		self.nameText = Text((0, 0), self.name, 25, color=Yellow)
		
		# Player graphic
		self.image = pygame.Surface((size, size), pygame.SRCALPHA)
		self.rect = self.image.get_rect()

		self.originalImage = GetImage(ImagePath("idle", "characters/zombie"))
		self.image.blit(self.originalImage, self.rect)

		self.rect.topleft = position
		self.hitRect = PLAYER_HIT_RECT
		self.hitRect.center = self.rect.center

		#region Physical Variables

		# Force (Newton)
		self.force = Vec(3, 3)
		self.frictionalForce = Vec(-1., -1.)
		self.netForce = Vec()

		# Acceleration (m/s**2)
		self.acceleration = Vec()
		self.maxAcceleration = 5

		# Velocity / Speed (m/s*2)
		self.velocity = Vec()
		self.maxMovSpeed = 5

		# Rotation
		self.forceRotation = Vec()

		# Weight (Kilogram)
		self.density = 25 # d (kg/piksel**2)
		self.weight = (self.rect.width/TILE_SIZE * self.rect.height/TILE_SIZE) * self.density # m = d*v

		#endregion

	def LoseHP(self, value):

		self.HP -= value

		if self.HP <= 0:

			self.kill()

	def Rotate(self):

		distanceX = self.target.rect.x - self.game.camera.Apply(self.rect)[0]
		distanceY = self.target.rect.y - self.game.camera.Apply(self.rect)[1]

		self.angle = math.atan2(-distanceY, distanceX)
		self.angle = math.degrees(self.angle)  # Convert radians to degrees

		self.image = pygame.transform.rotate(self.originalImage, self.angle)

		self.rect = self.image.get_rect(center=self.rect.center)

	def Move(self):
		
		self.forceRotation = Vec(Vec(self.target.rect.center) - Vec(self.rect.center))

		# Normalize force rotation
		if self.forceRotation.length() != 0:
		
			self.forceRotation.normalize()

		# Calculate net force
		self.netForce = self.force.elementwise() * self.forceRotation

		# apply frictional force
		if self.velocity.length() != 0:

			if abs(self.netForce.x) > self.frictionalForce.x:

				self.netForce.x += self.frictionalForce.x * self.velocity.normalize().x * self.game.deltaTime

			if abs(self.netForce.y) > self.frictionalForce.y:

				self.netForce.y += self.frictionalForce.y * self.velocity.normalize().y * self.game.deltaTime
			
		# Calculate acceleration
		self.acceleration = self.netForce / self.weight

		# Clamp acceleration
		self.acceleration.x = max(-self.maxAcceleration, min(self.maxAcceleration, self.acceleration.x))
		self.acceleration.y = max(-self.maxAcceleration, min(self.maxAcceleration, self.acceleration.y))

		# Update velocity
		self.velocity += self.acceleration * self.game.deltaTime

		# Limit velocity to a maximum speed
		if self.velocity.length() > self.maxMovSpeed:

			self.velocity.scale_to_length(self.maxMovSpeed)

		if abs(self.velocity.x) < 0.01:

			self.velocity.x = 0

		if abs(self.velocity.y) < 0.01:
			
			self.velocity.y = 0
		
		self.delta = (self.velocity * self.game.deltaTime) + (0.5 * self.acceleration * self.game.deltaTime * self.game.deltaTime)

		self.hitRect.centerx += self.delta.x
		self.CollideWithWalls('x')
		self.hitRect.centery += self.delta.y
		self.CollideWithWalls('y')

		self.UpdatePosition(self.hitRect.center)

	def CollideWithWalls(self, dir):

		if dir == 'x':

			hits = pygame.sprite.spritecollide(self, self.game.walls, False, CollideHitRect)
			
			if hits:

				if self.velocity.x > 0:

					self.hitRect.x = hits[0].rect.left - self.hitRect.width / 2.0

				if self.velocity.x < 0:

					self.hitRect.x = hits[0].rect.right + self.hitRect.width / 2.0

				self.velocity.x = 0

				self.hitRect.centerx = self.hitRect.x

		if dir == 'y':

			hits = pygame.sprite.spritecollide(self, self.game.walls, False, CollideHitRect)

			if hits:

				if self.velocity.y > 0:

					self.hitRect.y = hits[0].rect.top - self.hitRect.height / 2.0

				if self.velocity.y < 0:

					self.hitRect.y = hits[0].rect.bottom + self.hitRect.height / 2.0

				self.velocity.y = 0
				self.hitRect.centery = self.hitRect.y

	def UpdatePosition(self, position):

		self.hitRect.center = self.rect.center = position
		self.nameText.rect.center = (self.hitRect.centerx, self.hitRect.top - 30)
	
	def update(self):
		pass
		#self.Rotate()
		#self.Move()

class TileMap(Object):

	def __init__(self, game, fileName, borderWidth):

		self.spawnPoints = {0 : (120, 120), 1 : (220, 220)}
		self.game = game
		self.borderWidth = borderWidth
		self.tilemap =  pytmx.load_pygame(fileName, pixelalpha=True)
		self.tileWidth, self.tileHeight = self.tilemap.tilewidth, self.tilemap.tileheight
		self.columnCount, self.rowCount = self.tilemap.width, self.tilemap.height

		super().__init__((0, 0), (self.columnCount * self.tileWidth + self.borderWidth / 2, self.rowCount * self.tileHeight + self.borderWidth / 2), spriteGroups=self.game.allSprites)
		self.Render()

	def Render(self):

		self.image = pygame.Surface((self.columnCount * self.tileWidth + self.borderWidth / 2, self.rowCount * self.tileHeight + self.borderWidth / 2), pygame.SRCALPHA)
		
		tileImage = self.tilemap.get_tile_image_by_gid

		for layer in self.tilemap.visible_layers:

			if isinstance(layer, pytmx.TiledTileLayer):

				for x, y, gid in layer:

					tile = tileImage(gid)

					if tile:

						self.image.blit(tile, (x * self.tileWidth, y * self.tileHeight))

		self.DrawGrid()

	def DrawGrid(self):

		# Draw column lines
		for columnNumber in range(self.columnCount+1):

			pygame.draw.line(self.image, Gray, (columnNumber*self.tileWidth, 0), (columnNumber*self.tileWidth, self.rect.height), self.borderWidth)

		# Draw row lines
		for rowNumber in range(self.rowCount+1):

			pygame.draw.line(self.image, Gray, (0, rowNumber*self.tileHeight), (self.rect.width, rowNumber*self.tileHeight), self.borderWidth)

class Bullets(pygame.sprite.Group):

	def __init__(self, game):

		super().__init__()
		self.game = game
		self.camera = self.game.camera

	def Draw(self, image):

		for bullet in self:

			for wall in self.game.walls:

				if bullet.rect.colliderect(wall.rect):

					if bullet in self:
						
						self.remove(bullet)

			bullet.Move()
			self.camera.Draw(image, bullet.image, bullet.rect)

class Players(pygame.sprite.Group):

	def __init__(self, game) -> None:
		
		super().__init__()
		self.game = game

	def Add(self, playerID, playerName, playerSize=TILE_SIZE, playerPosition=(0, 0)):
		
		player = Player(playerID, playerName, playerSize, playerPosition, self.game)
		return player

	def GetPlayerWithID(self):

		for player in self.sprites():

			return player

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
		self.lobby = pygame.sprite.Group()
		self.room = pygame.sprite.Group()
		
		self.panel = Object(size=(400, 500))
		self.title = Text(("CENTER", self.panel.rect.y-100), WINDOW_TITLE, 60, color=Red)
		self.playerCountText = Text(("CENTER", self.panel.rect.bottom+30), "You are playing in offline mode !", 24, backgroundColor=Black, color=Red)

		self.playerNameText = Text(("CENTER", 70), "PLAYER NAME", 40, spriteGroups=self, parentRect=self.panel.screenRect)
		self.playerNameEntry = InputBox(("CENTER", 120), (300, 40), '', 'Please enter a player name...', self, self.panel.screenRect)
		self.playButton = Button(("CENTER", self.panel.rect.height-115), (300, 75), spriteGroups=self, parentRect=self.panel.screenRect, text="PLAY", textSize=45)
		
		self.characterText = Text(("CENTER", 200), "CHARACTER", 40, spriteGroups=self, parentRect=self.panel.screenRect)
		self.character = Object(("CENTER", 270), (45, 45), ImagePath("idle", "characters/hitman"), spriteGroups=self, parentRect=self.panel.screenRect)


		self.next = Object((275, 270), (50, 50), spriteGroups=self, parentRect=self.panel.screenRect)
		pygame.draw.polygon(self.next.image, Red, [(0, 0), (50, 25), (0, 50)])


		self.previous = Object((75, 270), (50, 50), spriteGroups=self, parentRect=self.panel.screenRect)
		pygame.draw.polygon(self.previous.image, Red, [(0, 25), (50, 0), (50, 50)])

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

	def StartGameInOfflineMode(self, playerName):

		self.mode = "offline"
		self.player = self.players.Add(1, playerName, TILE_SIZE, self.map.spawnPoints[1])
		#self.zombies.add(Zombie(self.player, TILE_SIZE, (200, 200), self))
		self.OpenTab("game")

	def EnterLobby(self, playerName) -> None:

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

					self.player.room = room
					self.menu.playersInRoom = room
					self.menu.roomText.UpdateText("Room " + str(room.ID))
					self.OpenTab("room")

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

					if player.ID == data['value'][0]:
						
						self.players.remove(player)
						break

	def HandleEvents(self, event: pygame.event.Event) -> None:

		if self.tab == "mainMenu":
			
			self.menu.playerNameEntry.HandleEvents(event, self.mousePosition, self.keys)
			
			if self.menu.playButton.isMouseOver(self.mousePosition):

				self.menu.playButton.SetColor(Gray)

			else:

				self.menu.playButton.SetColor(Black)
			
			if self.menu.playButton.isMouseClick(event, self.mousePosition):
		
				playerName = self.menu.playerNameEntry.text

				if self.client.isConnected:

					self.EnterLobby(playerName)

				else:

					self.StartGameInOfflineMode(playerName)

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
			