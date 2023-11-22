from settings import *
from path import ImagePath

#-# Image Function #-#
def GetImage(path: ImagePath, size=(0, 0)):

	if not (size[0] or size[1]):

		return pygame.image.load(path).convert_alpha()
	
	return pygame.transform.scale(pygame.image.load(path).convert_alpha(), size)

class Object(pygame.sprite.Sprite):

	def __init__(self, position: tuple=("CENTER", "CENTER"), size: tuple=(0, 0), imagePath: ImagePath=None, spriteGroups=[], parentRect: pygame.Rect = WINDOW_RECT):

		super().__init__(spriteGroups)

		self.image = pygame.Surface(size, pygame.SRCALPHA)
		self.rect = self.image.get_rect()
		self.screenRect = self.rect.copy()

		self.SetImage(imagePath)
		self.SetparentRect(parentRect)
		self.SetPosition(position)

	def Rerender(self):

		self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA)
		self.SetImage(self.imagePath)

	def SetImage(self, imagePath):
		
		self.imagePath = imagePath

		if imagePath:	
			
			image = GetImage(imagePath, self.rect.size)

			if not self.rect.size == image.get_rect().size:

				self.screenRect.size = self.rect.size = image.get_rect().size

			self.image.blit(image, (0, 0))

	def SetparentRect(self, rect: pygame.Rect):

		self.parentRect = rect

	def SetPosition(self, position: tuple) -> None:

		self.SetX(position[0])
		self.SetY(position[1])

	def SetX(self, x: int) -> None:

		if x == "CENTER":
		
			self.rect.x = (self.parentRect.width - self.rect.width) / 2
			
		elif x == "LEFT":

			self.rect.x = 0

		elif x == "RIGHT":

			self.rect.x = self.parentRect.width - self.rect.width

		else:

			self.rect.x = x

		self.screenRect.x = self.parentRect.x + self.rect.x # image rect is the screen rect of the parent

	def SetY(self, y: int) -> None:

		if y == "CENTER":
		
			self.rect.y = (self.parentRect.height - self.rect.height) / 2
			
		elif y == "TOP":

			self.rect.y = 0

		elif y == "BOTTOM":

			self.rect.y = self.parentRect.height - self.rect.height

		else:

			self.rect.y = y

		self.screenRect.y = self.parentRect.y + self.rect.y # image rect is the screen rect of the parent

	def isMouseOver(self, mousePosition: tuple) -> bool:
		
		if mousePosition != None and self.screenRect.collidepoint(mousePosition):

			return True
		
		return False

	def isMouseClick(self, event: pygame.event.Event, mousePosition: tuple) -> bool:

		if self.isMouseOver(mousePosition) and event.type == pygame.MOUSEBUTTONUP:

			return True
		
		return False

	def Draw(self, image: pygame.Surface):

		image.blit(self.image, self.rect)
