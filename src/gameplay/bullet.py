
from gui.object import Object
from util.constants import *

class Bullets(pygame.sprite.Group):

	def __init__(self):

		super().__init__()

class Bullet(Object):

	def __init__(self, source, position, angle) -> None:

		self.game, self.source = source.game, source
		self.movement_speed = BULLET_SPEED
		self.damage = BULLET_DAMAGE

		self.angle = angle

		super().__init__((0, 0), (10, 10), sprite_groups=[self.game.bullets, self.game.all_sprites])
		self._layer = BULLET_LAYER

		pygame.draw.circle(self.image, Blue, (5, 5), 5)
		
		self.rect = self.image.get_rect(center=position)
	
		self.velocity = Vec(1, 0).rotate(-self.angle) * self.movement_speed
		self.rotate(self.angle)
		
	def rotate(self, angle):

		self.image = pygame.transform.rotate(self.image, angle)
		self.rect = self.image.get_rect(center=self.rect.center)

	def move(self):

		self.rect.topleft += self.velocity * self.game.delta_time

	def update(self) -> None:
		
		self.move()

		if pygame.sprite.spritecollideany(self, self.game.walls):

			self.kill()
			return
		
		hits = pygame.sprite.spritecollide(self, self.game.mobs, False)

		for mob in hits:

			if mob != self.source:

				if hasattr(mob, 'lose_hp'):

					mob.velocity = Vec(0, 0)
					mob.lose_hp(self.damage)

				self.kill()
				break

		hits = pygame.sprite.spritecollide(self, self.game.players, False)

		for player in hits:

			if player != self.source:

				if hasattr(player, 'lose_hp'):

					player.velocity = Vec(0, 0)
					player.lose_hp(self.damage)

				self.kill()
				break
