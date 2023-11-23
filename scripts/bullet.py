import pygame
from object import Object
from settings import White
from pygame.math import Vector2 as Vec

class Bullets(pygame.sprite.Group):

	def __init__(self, game):

		super().__init__()
		self.game = game
		self.camera = self.game.camera

	def Draw(self, image):

		for bullet in self:

			for wall in self.game.walls:

				if bullet.rect.colliderect(wall.rect):

					if bullet in self:
						
						self.remove(bullet)

			bullet.Move()
			self.camera.Draw(image, bullet.image, bullet.rect)

class Bullet(Object):

	def __init__(self, position, screenPosition, targetPosition, game) -> None:

		super().__init__(position, (10, 5), spriteGroups=[game.bullets, game.allSprites])

		self.rect = self.image.get_rect(center=position)
		self.image.fill(White)
		self.velocity = (Vec(targetPosition) - Vec(screenPosition.center)).normalize()

	def Rotate(self, angle):

		self.image = pygame.transform.rotate(self.image, angle)
		self.rect = self.image.get_rect(center=self.rect.center)

	def Move(self):

		self.rect.topleft += self.velocity

	def update(self) -> None:
		
		self.Move()
