from object import Object
from text import Text
from settings import *
from path import *

class Button(Object):

	def __init__(self, position: tuple=("CENTER", "CENTER"), size: tuple=(0, 0), color: tuple = Blue, mouseOverColor: tuple = Red, imagePath: ImagePath=None, spriteGroups: list=[], parentRect: pygame.Rect=None, text: str="", textSize: int=20, textColor: tuple=White, textFontPath: pygame.font.Font=None):

		super().__init__(position, size, imagePath, spriteGroups, parentRect)
		self.stayDown = False
		self.normalColor, self.mouseOverColor = color, mouseOverColor
		
		self.polygonUpRect = pygame.Rect(0, 0, self.rect.width, self.rect.height-10)
		self.polygonDownRect = pygame.Rect(0, 0, self.rect.width, self.rect.height-20)

		if text:

			self.SetText(text, textSize, True, textColor, None, textFontPath)

	def SetText(self, text: str, textSize: int, antialias: bool, color: tuple, backgroundColor, fontPath: pygame.font.Font = None) -> None:

		self.text = Text(("CENTER", "CENTER"), text, textSize, antialias, color, backgroundColor, fontPath, (), self.screenRect)
		self.text.Draw(self.image)

	def HandleEvents(self, event, mousePosition):

		if event.type == pygame.MOUSEBUTTONDOWN:

			if self.rect.collidepoint(mousePosition):

				self.stayDown = True

		elif event.type == pygame.MOUSEBUTTONUP:

			self.stayDown = False

		self.color = self.normalColor if self.isMouseOver(mousePosition) else self.mouseOverColor
		pygame.draw.rect(self.image, Black, (0, 0, self.rect.width, self.rect.height), 0, 25)
		
		if self.stayDown:

			pygame.draw.rect(self.image, self.color, self.polygonDownRect, 0, 25)
			
		else:

			pygame.draw.rect(self.image, self.color, self.polygonDownRect, 0, 25)

		if hasattr(self, "text"):
			
			self.text.Draw(self.image)




			
