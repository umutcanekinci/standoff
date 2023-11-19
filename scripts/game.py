#region Import Packages

from typing import List, Optional


from pygame.rect import Rect
from pygame.surface import Surface


try:

	import pygame
	from pygame.math import Vector2 as Vec
	import math
	from default.application import Application
	from default.path import *
	from default.color import *
	from settings import *
	from level import *
	from client import Client
	
except ImportError as e:

	print("An error occured while importing packages:  " + str(e))

#endregion

#region Functions

#-# Image Function #-#
def GetImage(path: ImagePath, size=(0, 0)):

	if not (size[0] or size[1]):

		return pygame.image.load(path).convert_alpha()
	
	return pygame.transform.scale(pygame.image.load(path).convert_alpha(), size)

def CollideHitRect(one, two):
	return one.hitRect.colliderect(two.rect)

#endregion

class Object(pygame.sprite.Sprite):

	def __init__(self, position: tuple=("CENTER", "CENTER"), size: tuple=(0, 0), imagePath: ImagePath=None, spriteGroups=[], parentRect: pygame.Rect = WINDOW_RECT):

		super().__init__(spriteGroups)

		self.image = pygame.Surface(size, pygame.SRCALPHA)
		self.rect = self.image.get_rect()
		self.screenRect = self.rect.copy()

		self.SetImage(imagePath)
		self.SetparentRect(parentRect)
		self.SetPosition(position)

	def Rerender(self):

		self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA)
		self.SetImage(self.imagePath)

	def SetImage(self, imagePath):
		
		self.imagePath = imagePath

		if imagePath:	
			
			image = GetImage(imagePath, self.rect.size)

			if not self.rect.size == image.get_rect().size:

				self.screenRect.size = self.rect.size = image.get_rect().size

			self.image.blit(image, (0, 0))

	def SetparentRect(self, rect: pygame.Rect):

		self.parentRect = rect

	def SetPosition(self, position: tuple) -> None:

		self.SetX(position[0])
		self.SetY(position[1])

	def SetX(self, x: int) -> None:

		if x == "CENTER":
		
			self.rect.x = (self.parentRect.width - self.rect.width) / 2
			
		elif x == "LEFT":

			self.rect.x = 0

		elif x == "RIGHT":

			self.rect.x = self.parentRect.width - self.rect.width

		else:

			self.rect.x = x

		self.screenRect.x = self.parentRect.x + self.rect.x # image rect is the screen rect of the parent

	def SetY(self, y: int) -> None:

		if y == "CENTER":
		
			self.rect.y = (self.parentRect.height - self.rect.height) / 2
			
		elif y == "TOP":

			self.rect.y = 0

		elif y == "BOTTOM":

			self.rect.y = self.parentRect.height - self.rect.height

		else:

			self.rect.y = y

		self.screenRect.y = self.parentRect.y + self.rect.y # image rect is the screen rect of the parent

	def isMouseOver(self, mousePosition: tuple) -> bool:
		
		if mousePosition != None and self.screenRect.collidepoint(mousePosition):

			return True
		
		return False

	def isMouseClick(self, event: pygame.event.Event, mousePosition: tuple) -> bool:

		if self.isMouseOver(mousePosition) and event.type == pygame.MOUSEBUTTONUP:

			return True
		
		return False

	def Draw(self, image: pygame.Surface):

		image.blit(self.image, self.rect)

class Text(Object):

	def __init__(self, position, text='', textSize=25, antialias=True, color=White, backgroundColor=None, fontPath = None, spriteGroups: list=[], parentRect: pygame.Rect=WINDOW_RECT) -> None:

		super().__init__(position, (0, 0), None, spriteGroups, parentRect)

		self.position = position
		self.AddText(text, textSize, antialias, color, backgroundColor, fontPath)

	def AddText(self, text, textSize, antialias=True, color=White, backgroundColor=None, fontPath=None):

		self.text, self.textSize, self.antialias, self.color, self.backgroundColor, self.fontPath = text, textSize, antialias, color, backgroundColor, fontPath
		self.image = pygame.font.Font(fontPath, textSize).render(text, antialias, color, backgroundColor)
		self.rect = self.image.get_rect()
		self.SetPosition(self.position)
 
	def UpdateText(self, text) -> None:

		self.AddText(text, self.textSize, self.antialias, self.color, self.backgroundColor, self.fontPath)

class Button(Object):

	def __init__(self, position: tuple=("CENTER", "CENTER"), size: tuple=(0, 0), imagePath: ImagePath=None, spriteGroups: list=[], parentRect: pygame.Rect=None, text: str="", textSize: int=20, textColor: tuple=White, textFontPath: pygame.font.Font=None):

		super().__init__(position, size, imagePath, spriteGroups, parentRect)

		if text:

			self.SetText(text, textSize, True, textColor, None, textFontPath)

	def SetText(self, text: str, textSize: int, antialias: bool, color: tuple, backgroundColor, fontPath: pygame.font.Font = None) -> None:

		self.text = Text(("CENTER", "CENTER"), text, textSize, antialias, color, backgroundColor, fontPath, self.groups(), self.screenRect)

	def Draw(self, image):

		if hasattr(self, "text"):
			
			self.text.Draw(self.image)

		super().Draw(image)

class InputBox(Object):

	def __init__(self, position, size, text='', spriteGroups: list=[], parentRect: pygame.Rect=None):

		super().__init__(position, size, spriteGroups=spriteGroups, parentRect=parentRect)
		
		self.color = pygame.Color('dodgerblue2') # ('lightskyblue3')
		self.text = text
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
			self.color = pygame.Color('dodgerblue2') if self.active else pygame.Color('lightskyblue3')
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
		self.textSurface = pygame.font.Font(None, 32).render(self.text, True, self.color)
		pygame.draw.rect(self.image, self.color, pygame.Rect((0, 0), self.rect.size), 2)
		self.image.blit(self.textSurface, (10, self.rect.height/2-self.textSurface.get_height()/2))


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

class Bullet(pygame.sprite.Sprite):

	def __init__(self, position, screenPosition, targetPosition, game) -> None:

		super().__init__(game.bullets, game.allSprites)

		self.image = pygame.Surface((10, 5))
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

		super().__init__(position, (size, size), ImagePath("idle", "characters/hitman"), (game.players, game.allSprites))

		self.name = name
		self.ID = ID
		self.HP = 100
		self.game = game

		self.map = game.map
		self.camera = game.camera
		self.nameText = Text((0, 0), self.name, 25, color=Yellow)
		
		# Player graphic
		self.originalImage = GetImage(ImagePath("idle", "characters/hitman")) #pygame.image.load(ImagePath("idle", "characters/hitman")).convert_alpha()
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
		return
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

class MainPlayer(Player):

	def __init__(self, ID, name, size, position, game) -> None:
		
		super().__init__(ID, name, size, position, game)

class TileMap(pygame.sprite.Group):

	def __init__(self, game):

		self.game = game
		super().__init__()

	def LoadLevel(self, level, tileSize, borderWidth):

		#region control level

		if not level or len(level) == 0:

			print("This level is not suitable for rendering!")
			return ImportError
		
		for i in range(len(level)):

			if len(level[i]) != len(level[0]):

				print("This level is not suitable for rendering!")
				return ImportError
		
		#endregion

		self.level = level
		self.borderWidth = borderWidth
		self.rowCount = len(self.level)
		self.columnCount = len(self.level[0])
		self.tileSize = tileSize
		self.map = Object((0, 0), (self.columnCount*self.tileSize + borderWidth/2, self.rowCount*self.tileSize + borderWidth/2), spriteGroups=self.game.allSprites)

		self.CreateTiles()

	def CreateTiles(self):

		if hasattr(self, "level") and self.level:

			self.spawnPoints = {}

			for rowNumber, row in enumerate(self.level):

				for columnNumber, tileType in enumerate(row):
					
					if "P" in tileType:

						self.spawnPoints[int(tileType[1:])] = self.tileSize*columnNumber, self.tileSize*rowNumber
						tileType = "01"

					elif tileType not in MOVABLE_TILES:
					
						Wall(tileType, rowNumber, columnNumber, (self.game.walls, self.game.allSprites))

					Tile(tileType, rowNumber, columnNumber, self)

		else:

			print("Please load a level before rendering!")

	def Render(self):

		if hasattr(self, "level") and self.level:

			self.DrawTiles()
			self.DrawGrid()

		else:

			print("Please load a level before rendering!")

	def DrawTiles(self):

		super().draw(self.map.image)

	def DrawGrid(self):

		# Draw column lines
		for columnNumber in range(self.columnCount+1):

			pygame.draw.line(self.map.image, Gray, (columnNumber*self.tileSize, 0), (columnNumber*self.tileSize, self.map.rect.height), self.borderWidth)

		# Draw row lines
		for rowNumber in range(self.rowCount+1):

			pygame.draw.line(self.map.image, Gray, (0, rowNumber*self.tileSize), (self.map.rect.width, rowNumber*self.tileSize), self.borderWidth)

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

	def HandleEvents(self, event, mousePosition, keys):

		if hasattr(self.game, "player"):

			self.game.player.HandleEvents(event, mousePosition, keys)

class Camera():

	def __init__(self, size: tuple, map: TileMap):
		
		self.rect = pygame.Rect((0, 0), size)
		self.map = map.map
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

class Spritesheet():

	def __init__(self, imagePath) -> None:
		
		self.sheet = pygame.image.load(imagePath).convert()
		self.rect = self.sheet.get_rect()

	def GetSprite(self, rect):

		sprite = pygame.Surface(rect.size)
		sprite.blit(self.sheet, (0, 0), rect)
		sprite.set_colorkey(Black)
		return sprite

class MainMenu(pygame.sprite.Group):

	def __init__(self) -> None:

		super().__init__()

		self.panel = Object(size=(400, 400))
		self.title = Text(("CENTER", self.panel.rect.y-100), WINDOW_TITLE, 60, color=Red, spriteGroups=[self])
		self.playerNameText = Text(("CENTER", 50), "PLAYER NAME", 40, spriteGroups=self, parentRect=self.panel.screenRect)
		self.playerNameEntry = InputBox(("CENTER", 100), (300, 40), '', self, self.panel.screenRect)
		self.playButton = Button(("CENTER", 200), (300, 75), spriteGroups=self, parentRect=self.panel.screenRect, text="PLAY", textSize=45)
		self.playerCountText = Text(("CENTER", 350), "0 Players are Online", 20, backgroundColor=Black, color=Yellow, spriteGroups=self, parentRect= self.panel.screenRect)

	def draw(self, image):
		
		self.title.Draw(image)
		self.panel.Rerender()
		self.panel.image.fill((*Gray, 100))
		super().draw(self.panel.image)
		self.panel.Draw(image)

class Game(Application):

	def __init__(self) -> None:

		super().__init__(developMode=DEVELOP_MODE)

		self.menu = MainMenu()

		self.allSprites = pygame.sprite.Group()

		self.walls = pygame.sprite.Group()
		self.zombies = pygame.sprite.Group()
		self.map = TileMap(self)
		self.map.LoadLevel(level1, TILE_SIZE, BORDER_WIDTH)
		self.map.Render()
		self.players = Players(self)
		self.camera = Camera(self.rect.size, self.map)
		self.bullets = Bullets(self)
		self.players = Players(self)

		self.StartClient()
		self.OpenTab("mainMenu")
		
	def StartClient(self) -> None:

		self.client = Client(self)
		self.client.Start()
		self.client.SendData({'command' : '!GET_PLAYERS'})

	def StartGame(self) -> None:
		
		playerName = self.menu.playerNameEntry.text

		if self.client.isConnected:

			self.client.SendData({'command' : "!GET_PLAYER_ID", 'value' : playerName})

		else:

			self.player = self.players.Add(1, playerName, TILE_SIZE, self.map.spawnPoints[1], Yellow)
			self.zombies.add(Zombie(self.player, TILE_SIZE, (200, 200), self))

		self.OpenTab("game")

	def GetData(self, data) -> None:

		if data:

			if data['command'] == "!PLAYERS":

				for playerID, playerName in data['value']:

					self.players.Add(playerID, playerName)

				self.menu.playerCountText.UpdateText(str(len(self.players)) + " Players are Online")

			elif data['command'] == "!PLAYER_ID":
				
				self.player = self.players.Add(data['value'], self.menu.playerNameEntry.text, TILE_SIZE, self.map.spawnPoints[1])
				self.zombies.add(Zombie(self.player, TILE_SIZE, (200, 200), self))

			elif data['command'] == "!NEW_PLAYER":
				
				self.players.Add(*data['value'])

			elif data['command'] == "!PLAYER_RECT":

				for player in self.players:

					if player.ID == data['value'][0]:
						
						player.UpdatePosition(data['value'][1].topleft)
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

				self.menu.playButton.image.fill(Gray)
			else:
				self.menu.playButton.image.fill(Black)
			
			if self.menu.playButton.isMouseClick(event, self.mousePosition):

				self.StartGame()

		if self.tab == "game":

			if event.type == pygame.MOUSEBUTTONDOWN:

				if hasattr(self, "player"):
					
					self.player.Fire()

		return super().HandleEvents(event)

	def Update(self) -> None:

		if self.tab == "mainMenu":

			self.menu.update()

		elif self.tab == "game":

			self.allSprites.update()

			if hasattr(self, "player"):

				self.camera.Follow(self.player.rect)

				if self.client.isConnected:

					self.client.SendData({'command' : "!PLAYER_RECT", 'value' : [self.player.ID, pygame.Rect(self.player.rect.x - self.map.map.rect.x, self.player.rect.y - self.map.map.rect.y, self.player.rect.w, self.player.rect.h)]})

	def Draw(self) -> None:

		super().Draw()
		
		if self.tab == "mainMenu":

			self.menu.draw(self.window)

		elif self.tab == "game":

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
			