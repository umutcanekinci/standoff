from settings import *
from path import ImagePath

def GetImage(path: ImagePath, size=(0, 0)):

	image = pygame.image.load(path).convert_alpha()

	if size[0] and size[1] and size != image.get_size():

		return pygame.transform.scale(image, size)

	return image

class Object(pygame.sprite.Sprite):

	def __init__(self, position: tuple=("CENTER", "CENTER"), size: tuple=(0, 0), imagePath: ImagePath=None, spriteGroups=[], parentRect: pygame.Rect = WINDOW_RECT):

		super().__init__(spriteGroups)

		self.image = pygame.Surface(size, pygame.SRCALPHA)
		self.rect = self.image.get_rect()
		self.screenRect = self.rect.copy()
		self.isMouseHolding = False
		
		self.LoadImage(imagePath)
		self.SetparentRect(parentRect)
		self.SetPosition(position)
		self.SetVisible(True)
		
	def SetVisible(self, value):
		
		self.isVisible = value
		
		if self.isVisible:

			if hasattr(self, '_image'):

				self.image = self._image

		else:

			if hasattr(self, 'image'):

				self._image = self.image
				self.image = None

	def Rerender(self):

		self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA)
		self.LoadImage(self.imagePath)

	def LoadImage(self, imagePath):
		
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
		
			self.rect.centerx = self.parentRect.width / 2
			
		elif x == "LEFT":

			self.rect.x = 0

		elif x == "RIGHT":

			self.rect.x = self.parentRect.width - self.rect.width

		else:

			self.rect.x = x

		self.screenRect.x = self.parentRect.x + self.rect.x # image rect is the screen rect of the parent

	def SetY(self, y: int) -> None:

		if y == "CENTER":
		
			self.rect.centery = self.parentRect.height / 2
			
		elif y == "TOP":

			self.rect.y = 0

		elif y == "BOTTOM":

			self.rect.y = self.parentRect.height - self.rect.height

		else:

			self.rect.y = y

		self.screenRect.y = self.parentRect.y + self.rect.y # image rect is the screen rect of the parent

	def HandleEvents(self, event, mousePosition, keys):

		if event.type == pygame.MOUSEBUTTONUP:

			if not self.isMouseButtonUp(event, mousePosition):

				self.isMouseHolding = False

		if self.isMouseButtonDown(event, mousePosition):

			self.isMouseHolding = True

	def isMouseOver(self, mousePosition: tuple) -> bool:
		
		return mousePosition != None and self.screenRect.collidepoint(mousePosition)

	def isMouseButtonDown(self, event: pygame.event.Event, mousePosition: tuple) -> bool:

		return self.isMouseOver(mousePosition) and event.type == pygame.MOUSEBUTTONDOWN

	def isMouseButtonUp(self, event: pygame.event.Event, mousePosition: tuple) -> bool:

		return self.isMouseOver(mousePosition) and event.type == pygame.MOUSEBUTTONUP

	def isMouseClick(self, event: pygame.event.Event, mousePosition: tuple) -> bool:
		
		if self.isMouseButtonUp(event, mousePosition) and self.isMouseHolding:
			
			self.isMouseHolding = False
			return True
		
		return False

	def Draw(self, image: pygame.Surface):

		if self.isVisible:
			
			image.blit(self.image, self.rect)
