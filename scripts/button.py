from settings import *
from object import Object
from path import ImagePath
from text import Text
from path import *

class Button(Object):

	def __init__(self, position: tuple=("CENTER", "CENTER"), size: tuple=(0, 0), color: tuple = Blue, mouseOverColor: tuple = Red, imagePath: ImagePath=None, spriteGroups: list=[], parentRect: pygame.Rect=None, text: str="", textSize: int=20, textColor: tuple=White, textFontPath: pygame.font.Font=None):

		super().__init__(position, size, imagePath, spriteGroups, parentRect)

		self.stayDown = False
		self.normalColor, self.mouseOverColor = color, mouseOverColor
		self.color = self.normalColor

		self.polygonUpRect = pygame.Rect(0, 0, self.rect.width, self.rect.height-10)
		self.polygonDownRect = pygame.Rect(0, 10, self.rect.width, self.rect.height-10)

		if text:

			self.SetText(text, textSize, True, textColor, None, textFontPath)

		self.Rerender()

	def SetText(self, text: str, textSize: int, antialias: bool, color: tuple, backgroundColor, fontPath: pygame.font.Font = None) -> None:

		self.text = Text(("CENTER", "CENTER"), text, textSize, antialias, color, backgroundColor, fontPath, (), self.screenRect)

	def HandleEvents(self, event, mousePosition, keys):

		super().HandleEvents(event, mousePosition, keys)

		self.color = self.mouseOverColor if self.isMouseOver(mousePosition) else self.normalColor
		self.Rerender()

	def Rerender(self):

		super().Rerender()
	
		self.image.fill(self.color)
		pygame.draw.rect(self.image, Black, ((0, 0), self.rect.size), 2)

		if hasattr(self, "text"):
			
			self.text.Draw(self.image)

class EllipseButton(Button):

	def __init__(self, position: tuple = ("CENTER", "CENTER"), size: tuple = (0, 0), color: tuple = Blue, mouseOverColor: tuple = Red, imagePath: ImagePath = None, spriteGroups: list = [], parentRect: pygame.Rect = None, text: str = "", textSize: int = 20, textColor: tuple = White, textFontPath: pygame.font.Font = None):
		
		super().__init__(position, size, color, mouseOverColor, imagePath, spriteGroups, parentRect, text, textSize, textColor, textFontPath)

	def SetText(self, text: str, textSize: int, antialias: bool, color: tuple, backgroundColor, fontPath: pygame.font.Font = None) -> None:
		
		super().SetText(text, textSize, antialias, color, backgroundColor, fontPath)
	
		self.textUpRect = pygame.Rect((self.text.rect.x, self.text.rect.y - 5), self.text.rect.size)
		self.textDownRect = pygame.Rect((self.text.rect.x, self.text.rect.y + 5), self.text.rect.size)

	def Rerender(self):

		Object.Rerender(self)

		pygame.draw.rect(self.image, Black, (0, 10, self.rect.width, self.rect.height-10), 0, 25)

		if self.stayDown:

			pygame.draw.rect(self.image, self.color, self.polygonDownRect, 0, 25)
			pygame.draw.rect(self.image, Black, self.polygonDownRect, 1, 25)

			if hasattr(self, "text"):

				self.text.rect = self.textDownRect

		else:

			pygame.draw.rect(self.image, self.color, self.polygonUpRect, 0, 25)
			pygame.draw.rect(self.image, Black, self.polygonUpRect, 2, 25)

			if hasattr(self, "text"):

				self.text.rect = self.textUpRect

		if hasattr(self, "text"):
			
			self.text.Draw(self.image)

	def HandleEvents(self, event, mousePosition, keys):

		Object.HandleEvents(self, event, mousePosition, keys)

		if event.type == pygame.MOUSEBUTTONDOWN and self.isMouseOver(mousePosition):

			self.stayDown = True

		if event.type == pygame.MOUSEBUTTONUP:

			self.stayDown = False

		self.color = self.mouseOverColor if self.isMouseOver(mousePosition) or self.stayDown else self.normalColor

		self.Rerender()
