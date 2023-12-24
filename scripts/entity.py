from settings import *
from object import Object, GetImage
from text import Text
from map import Collide

class Entity(Object):

	def __init__(self, ID, name, nameColor, position, size, imagePath, spriteGroups, HP, maxHP):
		
		super().__init__((0, 0), (0, 0), imagePath, spriteGroups)

		self._layer = ENTITY_LAYER
		self.ID = ID

		self.SetName(name, nameColor)
		self.SetMaxHP(maxHP)
		self.SetHP(HP)
		self.SetImage(imagePath, position, size)

	def SetImage(self, imagePath, position, size):

		self.imagePath = imagePath
		
		self.originalImage = GetImage(imagePath, (self.rect.width * size, self.rect.height * size))
		self.image =self.originalImage.copy()
		self.rect = self.image.get_rect(center=position)

	def SetName(self, value: str, color):

		self.name = value
		self.nameText = Text((0, 0), self.name, 25, color=color)

	def __RenderHealthBar(self):

		self.healthBar = Object((0, 0), (HEALTH_BAR_SIZE))
		self.healthBar.image.fill(White)

		if self.HP > self.maxHP * 70 * .01:

			color = Green

		elif self.HP > self.maxHP * 35 * .01:

			color = Yellow

		else:

			color = Red

		pygame.draw.rect(self.healthBar.image, color, pygame.Rect(0, 0, self.healthBar.rect.width*self.HP/self.maxHP, self.healthBar.rect.height), 0)
		pygame.draw.rect(self.healthBar.image, color, pygame.Rect((0, 0), self.healthBar.rect.size), 2)

	def SetMaxHP(self, value):

		self.maxHP = value

		if hasattr(self, "HP"):
			
			self.__RenderHealthBar()

	def SetHP(self, value):

		self.HP = value

		if self.HP <= 0:

			self.kill()

		if hasattr(self, "maxHP"):

			self.__RenderHealthBar()

	def LoseHP(self, value):

		self.SetHP(self.HP - value)

	def Rotate(self, angle: float):

		self.image = pygame.transform.rotate(self.originalImage, angle)
		self.rect = self.image.get_rect(center=self.rect.center)

	def Move(self, delta):

		self.hitRect.centerx += delta.x
		Collide(self, 'x', self.game.walls)
		self.hitRect.centery += delta.y
		Collide(self, 'y', self.game.walls)
				
		self.UpdatePosition(self.hitRect.center)

	def UpdatePosition(self, position):

		self.hitRect.center = self.rect.center = position

		if self.HP != self.maxHP:

			self.nameText.rect.center = (self.hitRect.centerx, self.hitRect.top - 40)

		else:

			self.nameText.rect.center = (self.hitRect.centerx, self.hitRect.top - 30)


		self.healthBar.rect.center = (self.hitRect.centerx, self.hitRect.top - 20)

	def DrawName(self, surface, camera):

		camera.Draw(surface, self.nameText)

	def DrawRects(self, surface, camera):

		pygame.draw.rect(surface, Red, camera.Apply(self.rect), 2)
		pygame.draw.rect(surface, Blue, camera.Apply(self.hitRect), 2)

	def DrawHealthBar(self, surface, camera):

		if self.HP != self.maxHP:

			camera.Draw(surface, self.healthBar)
