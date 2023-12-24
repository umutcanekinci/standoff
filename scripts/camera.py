from settings import *
from map import Map

class Camera():

	def __init__(self, size: tuple, map: Map):
		
		self.rect = pygame.Rect((0, 0), size)
		self.map = map
		self.map.camera = self
		
	def Follow(self, targetRect):
		
		self.rect.x, self.rect.y = -targetRect.centerx + (self.rect.width / 2), -targetRect.centery + (self.rect.height / 2)
		
		self.rect.x = max(self.rect.width - self.map.rect.width, min(0, self.rect.x))
		self.rect.y = max(self.rect.height - self.map.rect.height, min(0, self.rect.y))

	def Apply(self, rect: pygame.Rect):
		
		return pygame.Rect((self.rect.x + rect.x, self.rect.y + rect.y), rect.size)

	def Draw(self, image, objects):

		if not hasattr(objects, '__iter__'):

			objects = [objects]

		for object in objects:
			
			image.blit(object.image, self.Apply(object.rect))
