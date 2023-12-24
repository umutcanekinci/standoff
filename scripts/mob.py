from settings import *
from path import ImagePath
from random import choice
from entity import Entity

def CollideHitRect(one, two):
	
	return one.hitRect.colliderect(two.rect)

class Mob(Entity):
	
	def __init__(self, ID, name, position, size, targetBase, character, game) -> None:

		super().__init__(ID, name, Red, position, size, ImagePath("idle", "characters/"+character), (), MOB_MAX_HP, MOB_MAX_HP)

		self.targetBase, self.character, self.game = targetBase, character, game
		self.map, self.camera = game.map, game.camera
		self.damage = 10
		self.range = RANGE_RADIUS

		# Hit rect for collisions
		self.rect.center = position
		self.hitRect = MOB_HIT_RECT.copy()
		self.hitRect.center = self.rect.center

		#region Physical Variables

		# Velocity / Speed (piksel/s*2)
		self.velocity = Vec()
		self.acceleration = Vec()
		self.angle = 0
		self.speed = choice(MOB_SPEEDS)

		#endregion
		
		self.add(game.allSprites, game.mobs)

	def CheckRange(self):

		if self.game.players:
		
			self.target = min([player.rect.center for player in self.game.players], key=lambda x: (Vec(x) - Vec(self.rect.center)).length())
			self.target = self.target if (Vec(self.target) - Vec(self.rect.center)).length() < self.range else self.targetBase

		else:

			self.target = self.targetBase

	def RotateToTarget(self):
		
		"""

		# Also this works to calculate angel
		
		distanceX = self.target[0] - self.rect[0]
		distanceY = self.target[1] - self.rect[1]

		self.angle = math.atan2(-distanceY, distanceX)
		self.angle = math.degrees(self.angle)  # Convert radians to degrees
		
		"""

		self.angle = (Vec(self.target) - Vec(self.rect.center)).angle_to(Vec(1,0)) # sthis calculating angle between difference vector and x apsis
		self.Rotate(self.angle)

	def AvoidMobs(self):

		for mob in self.game.mobs:

			if mob != self:

				distance = Vec(self.rect.center) - Vec(mob.rect.center)

				if 0 < distance.length() < AVOID_RADIUS:

					self.acceleration += distance.normalize()

	def Move(self):
		
		self.acceleration = Vec(1, 0).rotate(-self.angle)
		self.AvoidMobs()
		self.acceleration *= self.speed
		self.acceleration += self.velocity * -1
		self.velocity += self.acceleration * self.game.deltaTime
		self.delta = self.velocity * self.game.deltaTime + .5 * self.acceleration * self.game.deltaTime ** 2
		super().Move(self.delta)

	def update(self):
		
		self.CheckRange()
		self.RotateToTarget()
		self.Move()

		now = pygame.time.get_ticks()

		if not hasattr(self, "lastAttack"):

			self.lastAttack = -1000

		if now - self.lastAttack > 1000:
		
			hits = pygame.sprite.spritecollide(self, self.game.players, False, CollideHitRect)

			for player in hits:

				player.LoseHP(self.damage)
				player.velocity = Vec()
				player.UpdatePosition(Vec(player.rect.center) + Vec(MOB_KNOCKBACK, 0).rotate(-self.angle))
				self.lastAttack = now
				break

class Mobs(pygame.sprite.Group):

	def __init__(self, game) -> None:
		
		super().__init__()
		self.game = game

	def Add(self, mobInfo, character='zombie'):
		
		Mob(mobInfo.ID, 'Mob ' + str(mobInfo.ID), mobInfo.position, mobInfo.size, mobInfo.targetBase, character, self.game)
		
	def GetMobFromID(self, ID: int) -> Mob:

		for mob in self.sprites():

			if mob.ID == ID:

				return mob
