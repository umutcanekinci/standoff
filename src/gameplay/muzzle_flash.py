from util.constants import *
from gui.object import Object
from random import randint, choice

class MuzzleFlash(Object):

	def __init__(self, game, position: tuple, angle):

		self.spawn_time = pygame.time.get_ticks()
		size = randint(20, 50)
		size = size, size

		super().__init__(position, size, choice(game.gun_flashes), (game.all_sprites))
		self._layer = EFFECT_LAYER
		self.rect.center = position
		
		self.rotate(angle)

	def rotate(self, angle):

		self.image = pygame.transform.rotate(self.image, angle)
		self.rect = self.image.get_rect(center=self.rect.center)

	def update(self):

		now = pygame.time.get_ticks()

		if now - self.spawn_time > FLASH_DURATOION:

			self.kill()