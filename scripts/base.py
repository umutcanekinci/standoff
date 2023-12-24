from pygame import Rect
from object import Object, GetImage
from path import ImagePath
from settings import *
from text import Text

class Base(Object):

	def __init__(self, ID, game, position: tuple, size: tuple, imagePath: ImagePath = None, spriteGroups = (), parentRect: Rect = WINDOW_RECT):
		
		super().__init__(position, size, imagePath, spriteGroups, parentRect)

		self.ID, self.name, self.game = ID, "Base " + ID, game

		super().__init__(position, size, imagePath, (game.allSprites))
		
		self.maxHp = PLAYER_MAX_HP
		self.SetHP(self.maxHp)

		self.nameText = Text((0, 0), self.name, 25, color=Yellow)

		# Hit rect for collisions
		self.hitRect = PLAYER_HIT_RECT.copy()
		self.hitRect.center = self.rect.center = self.spawnPoint


	def SetHP(self, value):

		self.hp = value
		self.healthBar = Object((0, 0), (HEALTH_BAR_SIZE))
		self.healthBar.image.fill(White)

		if self.hp > self.maxHp * 70 * .01:

			color = Green

		elif self.hp > self.maxHp * 35 * .01:

			color = Yellow

		else:

			color = Red

		pygame.draw.rect(self.healthBar.image, color, pygame.Rect(0, 0, self.healthBar.rect.width*self.hp/self.maxHp, self.healthBar.rect.height), 0)
		pygame.draw.rect(self.healthBar.image, color, pygame.Rect((0, 0), self.healthBar.rect.size), 2)
			
		if self.hp <= 0:

			self.kill()

	def LoseHP(self, value):

		self.SetHP(self.hp - value)


	def DrawName(self, surface):

		self.game.camera.Draw(surface, [self.nameText])

	def DrawRects(self, surface):

		pygame.draw.rect(surface, Red, self.game.camera.Apply(self.rect), 2)
		pygame.draw.rect(surface, Blue, self.game.camera.Apply(self.hitRect), 2)

	def DrawHealthBar(self, surface):

		if self.hp != self.maxHp:

			self.game.camera.Draw(surface, [self.healthBar])
