from pygame import Rect
from gui.object import Object, get_image
from pygame_core.asset_path import ImagePath
from util.constants import *
from gui.text import Text

class Base(Object):

	def __init__(self, id, game, position: tuple, size: tuple, image_path: ImagePath = None, sprite_groups = (), parent_rect: Rect = WINDOW_RECT):
		
		super().__init__(position, size, image_path, sprite_groups, parent_rect)

		self.id, self.name, self.game = id, "Base " + id, game

		super().__init__(position, size, image_path, (game.all_sprites))
		
		self.max_hp = PLAYER_MAX_HP
		self.set_hp(self.max_hp)

		self.name_text = Text((0, 0), self.name, 25, color=Yellow)

		# Hit rect for collisions
		self.hit_rect = PLAYER_HIT_RECT.copy()
		self.hit_rect.center = self.rect.center = self.spawn_point


	def set_hp(self, value):

		self.hp = value
		self.health_bar = Object((0, 0), (HEALTH_BAR_SIZE))
		self.health_bar.image.fill(White)

		if self.hp > self.max_hp * 70 * .01:

			color = Green

		elif self.hp > self.max_hp * 35 * .01:

			color = Yellow

		else:

			color = Red

		pygame.draw.rect(self.health_bar.image, color, pygame.Rect(0, 0, self.health_bar.rect.width*self.hp/self.max_hp, self.health_bar.rect.height), 0)
		pygame.draw.rect(self.health_bar.image, color, pygame.Rect((0, 0), self.health_bar.rect.size), 2)
			
		if self.hp <= 0:

			self.kill()

	def lose_hp(self, value):

		self.set_hp(self.hp - value)


	def draw_name(self, surface):

		self.game.camera.draw(surface, [self.name_text])

	def draw_rects(self, surface):

		pygame.draw.rect(surface, Red, self.game.camera.apply(self.rect), 2)
		pygame.draw.rect(surface, Blue, self.game.camera.apply(self.hit_rect), 2)

	def draw_health_bar(self, surface):

		if self.hp != self.max_hp:

			self.game.camera.draw(surface, [self.health_bar])
