from util.constants import *
from gui.object import Object, get_image
from gui.text import Text
from gameplay.collision import collide

class Entity(Object):

	def __init__(self, id, name, name_color, position, size, image_path, sprite_groups, hp, max_hp):
		
		super().__init__((0, 0), (0, 0), image_path, sprite_groups)

		self._layer = ENTITY_LAYER
		self.id = id

		self.set_name(name, name_color)
		self.set_max_hp(max_hp)
		self.set_hp(hp)
		self.set_image(image_path, position, size)

	def set_image(self, image_path, position, size):

		self.image_path = image_path
		
		self.original_image = get_image(image_path, (self.rect.width * size, self.rect.height * size))
		self.image =self.original_image.copy()
		self.rect = self.image.get_rect(center=position)

	def set_name(self, value: str, color):

		self.name = value
		self.name_text = Text((0, 0), self.name, 25, color=color)

	def __render_health_bar(self):

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

	def set_max_hp(self, value):

		self.max_hp = value

		if hasattr(self, "hp"):
			
			self.__render_health_bar()

	def set_hp(self, value):

		self.hp = value

		if self.hp <= 0:

			self.kill()

		if hasattr(self, "max_hp"):

			self.__render_health_bar()

	def lose_hp(self, value):

		self.set_hp(self.hp - value)

	def rotate(self, angle: float):

		self.image = pygame.transform.rotate(self.original_image, angle)
		self.rect = self.image.get_rect(center=self.rect.center)

	def move(self, delta):

		self.hit_rect.centerx += delta.x
		collide(self, 'x', self.game.walls)
		self.hit_rect.centery += delta.y
		collide(self, 'y', self.game.walls)
				
		self.update_position(self.hit_rect.center)

	def update_position(self, position):

		self.hit_rect.center = self.rect.center = position

		if self.hp != self.max_hp:

			self.name_text.rect.center = (self.hit_rect.centerx, self.hit_rect.top - 40)

		else:

			self.name_text.rect.center = (self.hit_rect.centerx, self.hit_rect.top - 30)


		self.health_bar.rect.center = (self.hit_rect.centerx, self.hit_rect.top - 20)

	def draw_name(self, surface, camera):

		camera.draw(surface, self.name_text)

	def draw_rects(self, surface, camera):

		pygame.draw.rect(surface, Red, camera.apply(self.rect), 2)
		pygame.draw.rect(surface, Blue, camera.apply(self.hit_rect), 2)

	def draw_health_bar(self, surface, camera):

		if self.hp != self.max_hp:

			camera.draw(surface, self.health_bar)
