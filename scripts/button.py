from settings import *
from object import Object
from path import ImagePath
from text import Text
from path import *

class Button(Object):

	def __init__(self, position: tuple=("CENTER", "CENTER"), size: tuple=(0, 0), color: tuple = Blue, mouseOverColor: tuple = Red, imagePath: ImagePath=None, spriteGroups: list=[], parentRect: pygame.Rect=None, text: str="", textSize: int=20, textColor: tuple=White, textFontPath: pygame.font.Font=None, isActive=True):

		super().__init__(position, size, imagePath, spriteGroups, parentRect)
		self._layer = GUI_LAYER

		self.normalColor, self.mouseOverColor = color, mouseOverColor
		self.color = self.normalColor

		if text:

			self.SetText(text, textSize, True, textColor, None, textFontPath)

		if isActive:

			self.Enable()

		else:
			
			self.Disable()

	def Enable(self):

		self.active = True
		self.Rerender()

	def Disable(self):

		self.active = False
		self.color = Gray
		self.Rerender()

	def SetText(self, text: str, textSize: int, antialias: bool, color: tuple, backgroundColor, fontPath: pygame.font.Font = None) -> None:

		self.text = Text(("CENTER", "CENTER"), text, textSize, antialias, color, backgroundColor, fontPath, (), self.screenRect)

	def HandleEvents(self, event, mousePosition, keys):

		super().HandleEvents(event, mousePosition, keys)

		self.UpdateColor(mousePosition)
		
		self.Rerender()

	def UpdateColor(self, mousePosition):

		if self.active:

			self.color = self.mouseOverColor if self.isMouseOver(mousePosition) else self.normalColor
		
		else:
			
			self.color = Gray

	def Rerender(self):

		super().Rerender()
		
		self.image.fill(self.color)
		pygame.draw.rect(self.image, Black, ((0, 0), self.rect.size), 2)

		if hasattr(self, "text"):
			
			self.text.Draw(self.image)

	def isMouseClick(self, event: pygame.event.Event, mousePosition: tuple) -> bool:

		return super().isMouseClick(event, mousePosition) and self.active

class EllipseButton(Button):

	def __init__(self, position: tuple = ("CENTER", "CENTER"), size: tuple = (0, 0), color: tuple = Blue, mouseOverColor: tuple = Red, imagePath: ImagePath = None, spriteGroups: list = [], parentRect: pygame.Rect = None, text: str = "", textSize: int = 20, textColor: tuple = White, textFontPath: pygame.font.Font = None, isActive=True):
		
		self.stayDown = False
		super().__init__(position, size, color, mouseOverColor, imagePath, spriteGroups, parentRect, text, textSize, textColor, textFontPath, isActive)

	def SetText(self, text: str, textSize: int, antialias: bool, color: tuple, backgroundColor, fontPath: pygame.font.Font = None) -> None:
		
		super().SetText(text, textSize, antialias, color, backgroundColor, fontPath)
	
		self.textUpRect = pygame.Rect((self.text.rect.x, self.text.rect.y - 5), self.text.rect.size)
		self.textDownRect = pygame.Rect((self.text.rect.x, self.text.rect.y + 5), self.text.rect.size)

	def Rerender(self):

		polygonUpRect = pygame.Rect(0, 0, self.rect.width, self.rect.height-5)
		polygonDownRect = pygame.Rect(0, 5, self.rect.width, self.rect.height-5)

		Object.Rerender(self)

		pygame.draw.rect(self.image, Black, polygonDownRect, 0, 25)

		if self.stayDown:

			pygame.draw.rect(self.image, self.color, polygonDownRect, 0, 25)
			pygame.draw.rect(self.image, Black, polygonDownRect, 1, 25)

			if hasattr(self, "text"):

				self.text.rect = self.textDownRect

		else:

			pygame.draw.rect(self.image, self.color, polygonUpRect, 0, 25)
			pygame.draw.rect(self.image, Black, polygonUpRect, 2, 25)

			if hasattr(self, "text"):

				self.text.rect = self.textUpRect

		if hasattr(self, "text"):
			
			self.text.Draw(self.image)

	def UpdateColor(self, mousePosition):

		if self.active:

			self.color = self.mouseOverColor if self.isMouseOver(mousePosition) or self.stayDown else self.normalColor
		
		else:

			self.color = Gray

	def HandleEvents(self, event, mousePosition, keys):

		Object.HandleEvents(self, event, mousePosition, keys)

		if event.type == pygame.MOUSEBUTTONDOWN and self.isMouseOver(mousePosition):

			self.stayDown = True

		if event.type == pygame.MOUSEBUTTONUP:

			self.stayDown = False

		
		self.UpdateColor(mousePosition)

		self.Rerender()

class TriangleButton(Button):

	def __init__(self, position: tuple = ("CENTER", "CENTER"), size: tuple = (0, 0), color: tuple = Blue, mouseOverColor: tuple = Red, imagePath: ImagePath = None, spriteGroups: list = [], parentRect: pygame.Rect = None, text: str = "", textSize: int = 20, textColor: tuple = White, textFontPath: pygame.font.Font = None, isActive=True, rotation="RIGHT"):
		
		self.stayDown, self.rotation = False, rotation
		super().__init__(position, size, color, mouseOverColor, imagePath, spriteGroups, parentRect, text, textSize, textColor, textFontPath, isActive)

	def SetText(self, text: str, textSize: int, antialias: bool, color: tuple, backgroundColor, fontPath: pygame.font.Font = None) -> None:
		
		super().SetText(text, textSize, antialias, color, backgroundColor, fontPath)
	
		self.textUpRect = pygame.Rect((self.text.rect.x, self.text.rect.y - 5), self.text.rect.size)
		self.textDownRect = pygame.Rect((self.text.rect.x, self.text.rect.y + 5), self.text.rect.size)

	def Rerender(self):

		if self.rotation == "RIGHT":

			polygonUpPoints = [(0, 0), (self.rect.width, self.rect.height/2-5), (0, self.rect.height-10)]
			polygonDownPoints = [(0, 10), (self.rect.width, self.rect.height/2+5), (0, self.rect.height)]
		
		elif self.rotation == "LEFT":

			polygonUpPoints = [(self.rect.width, 0), (0, self.rect.height/2-5), (self.rect.width, self.rect.height-10)]
			polygonDownPoints = [(self.rect.width, 10), (0, self.rect.height/2+5), (self.rect.width, self.rect.height)]

		Object.Rerender(self)

		pygame.draw.polygon(self.image, Black, polygonDownPoints)
		
		if self.stayDown:

			pygame.draw.polygon(self.image, self.color, polygonDownPoints)
			pygame.draw.polygon(self.image, Black, polygonDownPoints, 1)

			if hasattr(self, "text"):

				self.text.rect = self.textDownRect

		else:

			pygame.draw.polygon(self.image, self.color, polygonUpPoints, 0)
			pygame.draw.polygon(self.image, Black, polygonUpPoints, 2)

			if hasattr(self, "text"):

				self.text.rect = self.textUpRect

		if hasattr(self, "text"):
			
			self.text.Draw(self.image)

	def UpdateColor(self, mousePosition):
		
		if self.active:

			self.color = self.mouseOverColor if self.isMouseOver(mousePosition) or self.stayDown else self.normalColor

		else:
			
			self.color = Gray

	def HandleEvents(self, event, mousePosition, keys):

		Object.HandleEvents(self, event, mousePosition, keys)

		if event.type == pygame.MOUSEBUTTONDOWN and self.isMouseOver(mousePosition):

			self.stayDown = True

		if event.type == pygame.MOUSEBUTTONUP:

			self.stayDown = False

		self.UpdateColor(mousePosition)

		self.Rerender()