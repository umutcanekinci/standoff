
from object import Object
from settings import *

class Bullets(pygame.sprite.Group):

	def __init__(self):

		super().__init__()

class Bullet(Object):

	def __init__(self, source, position, angle) -> None:

		self.game, self.source = source.game, source
		self.movementSpeed = BULLET_SPEED
		self.damage = BULLET_DAMAGE

		self.angle = angle

		super().__init__((0, 0), (10, 10), spriteGroups=[self.game.bullets, self.game.allSprites])
		self._layer = BULLET_LAYER

		pygame.draw.circle(self.image, Blue, (5, 5), 5)
		
		self.rect = self.image.get_rect(center=position)
	
		self.velocity = Vec(1, 0).rotate(-self.angle) * self.movementSpeed
		self.Rotate(self.angle)
		
	def Rotate(self, angle):

		self.image = pygame.transform.rotate(self.image, angle)
		self.rect = self.image.get_rect(center=self.rect.center)

	def Move(self):

		self.rect.topleft += self.velocity * self.game.deltaTime

	def update(self) -> None:
		
		self.Move()

		if pygame.sprite.spritecollideany(self, self.game.walls):

			self.kill()
			return
		
		hits = pygame.sprite.spritecollide(self, self.game.mobs, False)

		for mob in hits:

			if mob != self.source:

				if hasattr(mob, 'LoseHP'):

					mob.velocity = Vec(0, 0)
					mob.LoseHP(self.damage)

				self.kill()
				break

		hits = pygame.sprite.spritecollide(self, self.game.players, False)

		for player in hits:

			if player != self.source:

				if hasattr(player, 'LoseHP'):

					player.velocity = Vec(0, 0)
					player.LoseHP(self.damage)

				self.kill()
				break
