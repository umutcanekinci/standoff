from object import Object, GetImage
from path import ImagePath
from settings import *
from text import Text
from pygame.math import Vector2 as Vec
import math
from bullet import Bullet

def CollideHitRect(one, two):
	
	return one.hitRect.colliderect(two.rect)

class Zombie(Object):
	
	def __init__(self, ID, target, name, character, size, position, game) -> None:

		super().__init__(position, size, {}, (game.allSprites, game.zombies))

		self.ID, self.target, self.name, self.character, self.game = ID, target, name, character, game
		self.map, self.camera = game.map, game.camera
		self.HP = 100
		self.nameText = Text((0, 0), self.name, 25, color=Yellow)
 
		# Player graphic
		self.originalImage = GetImage(ImagePath("idle", "characters/"+character))
		self.image = self.originalImage.copy()
		self.rect = self.image.get_rect()

		# Hit rect for collisions
		self.rect.center = position
		self.hitRect = PLAYER_HIT_RECT.copy()
		self.hitRect.center = self.rect.center

		#region Physical Variables

		# Velocity / Speed (piksel/s*2)
		self.velocity = Vec()
		self.movSpeed = 1

		#endregion

	def LoseHP(self, value):

		self.HP -= value

		if self.HP <= 0:

			self.kill()

	def Rotate(self):

		distanceX = self.target.rect.x - self.game.camera.Apply(self.rect)[0]
		distanceY = self.target.rect.y - self.game.camera.Apply(self.rect)[1]

		self.angle = math.atan2(-distanceY, distanceX)
		self.angle = math.degrees(self.angle)  # Convert radians to degrees

		self.image = pygame.transform.rotate(self.originalImage, self.angle)

		self.rect = self.image.get_rect(center=self.rect.center)

	def Move(self):
		
		self.movRotation = Vec(Vec(self.target.rect.center) - Vec(self.rect.center))

		if self.movRotation.length():

			self.movRotation = self.movRotation.normalize()

		self.velocity = self.movRotation * self.movSpeed

		self.delta = (self.velocity * self.game.deltaTime)
		self.hitRect.centerx += self.delta.x
		self.CollideWithWalls('x')
		self.hitRect.centery += self.delta.y
		self.CollideWithWalls('y')

		self.UpdatePosition(self.hitRect.center)

	def CollideWithWalls(self, dir):
		return
		if dir == 'x':

			hits = pygame.sprite.spritecollide(self, self.game.walls, False, CollideHitRect)
			
			if hits:

				if self.velocity.x > 0:

					self.hitRect.x = hits[0].rect.left - self.hitRect.width / 2.0

				if self.velocity.x < 0:

					self.hitRect.x = hits[0].rect.right + self.hitRect.width / 2.0

				self.velocity.x = 0

				self.hitRect.centerx = self.hitRect.x

		if dir == 'y':

			hits = pygame.sprite.spritecollide(self, self.game.walls, False, CollideHitRect)

			if hits:

				if self.velocity.y > 0:

					self.hitRect.y = hits[0].rect.top - self.hitRect.height / 2.0

				if self.velocity.y < 0:

					self.hitRect.y = hits[0].rect.bottom + self.hitRect.height / 2.0

				self.velocity.y = 0
				self.hitRect.centery = self.hitRect.y

	def UpdatePosition(self, position):

		self.hitRect.center = self.rect.center = position
		self.nameText.rect.center = (self.hitRect.centerx, self.hitRect.top - 30)
	
	def update(self):
		
		self.Rotate()
		self.Move()


class Zombies(pygame.sprite.Group):

	def __init__(self, game) -> None:
		
		super().__init__()
		self.game = game

	def Add(self, ID, target, character='zombie', size=TILE_SIZE, position=(0, 0)):
		
		Zombie(ID, target, 'Zombie ' + str(ID), character, size, position, self.game)
		
	def GetZombieWithID(self, ID: int) -> Zombie:

		for zombie in self.sprites():

			if zombie.ID == ID:

				return zombie
