from util.constants import *
from gameplay.map import Map

class Camera():

	def __init__(self, size: tuple, map: Map):
		
		self.rect = pygame.Rect((0, 0), size)
		self.map = map
		self.map.camera = self
		
	def follow(self, target_rect):
		
		self.rect.x, self.rect.y = -target_rect.centerx + (self.rect.width / 2), -target_rect.centery + (self.rect.height / 2)
		
		self.rect.x = max(self.rect.width - self.map.rect.width, min(0, self.rect.x))
		self.rect.y = max(self.rect.height - self.map.rect.height, min(0, self.rect.y))

	def apply(self, rect: pygame.Rect):
		
		return pygame.Rect((self.rect.x + rect.x, self.rect.y + rect.y), rect.size)

	def draw(self, image, objects):

		if not hasattr(objects, '__iter__'):

			objects = [objects]

		for object in objects:
			
			image.blit(object.image, self.apply(object.rect))
