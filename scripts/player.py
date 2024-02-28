from settings import *
from path import ImagePath
from bullet import Bullet
from entity import Entity
from muzzle_flash import MuzzleFlash
from random import uniform

class Player(Entity):

	def __init__(self, ID, name, nameColor, character, position, size, game) -> None:

		super().__init__(ID, name, nameColor, position, size, ImagePath("gun", "characters/"+character), (game.players, game.allSprites), PLAYER_MAX_HP, PLAYER_MAX_HP)
		
		# Shooting
		self.isShooting = False
		self.shootRate = SHOOT_RATE
		self.lastShootTime = -1000

		self.character, self.game = character, game
		self.map, self.camera = game.map, game.camera

		# Hit rect for collisions
		self.hitRect = PLAYER_HIT_RECT.copy()
		self.hitRect.center = self.rect.center
		self.autoShoot = True,

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
		self.maxspeed = 5

		# Rotation
		self.forceRotation = Vec()
		self.delta = Vec()
		self.angle = 0
		
		# Weight (Kilogram)
		self.density = 25 # d (kg/piksel**2)
		self.weight = (self.rect.width/TILE_WIDTH * self.rect.height/TILE_HEIGHT) * self.density # m = d*v

		#endregion

	def RotateToMouse(self):

		"""
		
		# Also this works to calculate angel

		distanceX = self.game.mousePosition[0] - self.game.camera.Apply(self.rect)[0]
		distanceY = self.game.mousePosition[1] - self.game.camera.Apply(self.rect)[1]

		self.angle = math.atan2(-distanceY, distanceX)
		self.angle = math.degrees(self.angle)  # Convert radians to degrees

		"""

		self.angle = (Vec(self.game.mousePosition) - Vec(self.game.camera.Apply(self.rect).center)).angle_to(Vec(1,0)) # sthis calculating angle between difference vector and x apsis
		#self.Rotate(self.angle)

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
		if self.velocity.length() > self.maxspeed:

			self.velocity.scale_to_length(self.maxspeed)

		if abs(self.velocity.x) < 0.01:

			self.velocity.x = 0

		if abs(self.velocity.y) < 0.01:
			
			self.velocity.y = 0
		
		self.delta = (self.velocity * self.game.deltaTime) + (0.5 * self.acceleration * self.game.deltaTime * self.game.deltaTime)

		#super().Move(self.delta)

	def Shoot(self):

		now = pygame.time.get_ticks()

		if now - self.lastShootTime > self.shootRate:

			spread = uniform(-GUN_SPREAD, GUN_SPREAD)
			angle = self.angle + spread
			position = Vec(self.rect.center) + BARREL_OFFSET.rotate(-angle)

			Bullet(self, position, angle)
			MuzzleFlash(self.game, position, self.angle)

			self.velocity = Vec(-KICKBACK, 0).rotate(-self.angle)

			self.lastShootTime = now
						
	def HandleEvents(self, event, mousePosition, keys):
		
		if self.alive():
			
			if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
			
				if self.autoShoot:

					self.isShooting = True

				else:

					self.game.Shoot()

			if event.type == pygame.MOUSEBUTTONUP and event.button == 1:

				self.isShooting = False

	def update(self):
		
		self.Rotate(self.angle)
		super().Move(self.delta)

class Players(pygame.sprite.Group):

	def __init__(self, game) -> None:
		
		super().__init__()
		self.game = game

	def Add(self, playerInfo, nameColor):
		
		return Player(playerInfo.ID, playerInfo.name, nameColor, playerInfo.characterName, self.game.map.spawnPoints[playerInfo.baseNumber], playerInfo.size, self.game)

	def GetPlayerWithID(self, ID: int) -> Player:

		for player in self.sprites():

			if player.ID == ID:

				return player
