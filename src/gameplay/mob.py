from util.constants import *
from random import choice
from gameplay.entity import Entity

def collide_hit_rect(one, two):
	
	return one.hit_rect.colliderect(two.rect)

class Mob(Entity):
	
	def __init__(self, id, name, position, size, target_base, character, game) -> None:

		super().__init__(id, name, Red, position, size, game.assets.image_path(f"char_{character}_idle"), (), MOB_MAX_HP, MOB_MAX_HP)

		self.target_base, self.character, self.game = target_base, character, game
		self.map, self.camera = game.map, game.camera
		self.damage = 10
		self.range = RANGE_RADIUS

		# Hit rect for collisions
		self.rect.center = position
		self.hit_rect = MOB_HIT_RECT.copy()
		self.hit_rect.center = self.rect.center

		#region Physical Variables

		# Velocity / Speed (piksel/s*2)
		self.velocity = Vec()
		self.acceleration = Vec()
		self.angle = 0
		self.speed = choice(MOB_SPEEDS)

		#endregion
		
		self.add(game.all_sprites, game.mobs)

	def check_range(self):

		if self.game.players:
		
			self.target = min([player.rect.center for player in self.game.players], key=lambda x: (Vec(x) - Vec(self.rect.center)).length())
			self.target = self.target if (Vec(self.target) - Vec(self.rect.center)).length() < self.range else self.target_base

		else:

			self.target = self.target_base

	def rotate_to_target(self):
		
		"""

		# Also this works to calculate angel
		
		distanceX = self.target[0] - self.rect[0]
		distanceY = self.target[1] - self.rect[1]

		self.angle = math.atan2(-distanceY, distanceX)
		self.angle = math.degrees(self.angle)  # Convert radians to degrees
		
		"""

		self.angle = (Vec(self.target) - Vec(self.rect.center)).angle_to(Vec(1,0)) # sthis calculating angle between difference vector and x apsis
		self.rotate(self.angle)

	def avoid_mobs(self):

		for mob in self.game.mobs:

			if mob != self:

				distance = Vec(self.rect.center) - Vec(mob.rect.center)

				if 0 < distance.length() < AVOID_RADIUS:

					self.acceleration += distance.normalize()

	def move(self):
		
		self.acceleration = Vec(1, 0).rotate(-self.angle)
		self.avoid_mobs()
		self.acceleration *= self.speed
		self.acceleration += self.velocity * -1
		self.velocity += self.acceleration * self.game.delta_time
		self.delta = self.velocity * self.game.delta_time + .5 * self.acceleration * self.game.delta_time ** 2
		super().move(self.delta)

	def update(self):
		
		self.check_range()
		self.rotate_to_target()
		self.move()

		now = pygame.time.get_ticks()

		if not hasattr(self, "last_attack"):

			self.last_attack = -1000

		if now - self.last_attack > 1000:
		
			hits = pygame.sprite.spritecollide(self, self.game.players, False, collide_hit_rect)

			for player in hits:

				player.lose_hp(self.damage)
				player.velocity = Vec()
				player.update_position(Vec(player.rect.center) + Vec(MOB_KNOCKBACK, 0).rotate(-self.angle))
				self.last_attack = now
				break

class Mobs(pygame.sprite.Group):

	def __init__(self, game) -> None:
		
		super().__init__()
		self.game = game

	def add_mob(self, mob_info, character='zombie'):
		
		Mob(mob_info.id, 'Mob ' + str(mob_info.id), mob_info.position, mob_info.size, mob_info.target_base, character, self.game)
		
	def get_mob_from_id(self, id: int) -> Mob:

		for mob in self.sprites():

			if mob.id == id:

				return mob
