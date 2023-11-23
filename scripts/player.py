from object import Object, GetImage
from path import ImagePath
from settings import *
from text import Text
from pygame.math import Vector2 as Vec
import math
from bullet import Bullet

def CollideHitRect(one, two):
	
	return one.hitRect.colliderect(two.rect)

class Player(Object):

	def __init__(self, ID, name, size, position, game) -> None:

		super().__init__(position, size, {}, (game.players, game.allSprites))
		
		self.ID = ID
		self.name = name
		self.state = "menu"
		self.HP = 100
		self.game = game
		self.room = None
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
		self.weight = (self.rect.width/TILE_WIDTH * self.rect.height/TILE_HEIGHT) * self.density # m = d*v

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
