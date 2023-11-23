from object import Object
from text import Text
from settings import *
from path import *

class Button(Object):

	def __init__(self, position: tuple=("CENTER", "CENTER"), size: tuple=(0, 0), imagePath: ImagePath=None, spriteGroups: list=[], parentRect: pygame.Rect=None, text: str="", textSize: int=20, textColor: tuple=White, textFontPath: pygame.font.Font=None):

		super().__init__(position, size, imagePath, spriteGroups, parentRect)

		if text:

			self.SetText(text, textSize, True, textColor, None, textFontPath)

	def SetText(self, text: str, textSize: int, antialias: bool, color: tuple, backgroundColor, fontPath: pygame.font.Font = None) -> None:

		self.text = Text(("CENTER", "CENTER"), text, textSize, antialias, color, backgroundColor, fontPath, (), self.screenRect)
		self.text.Draw(self.image)

	def SetColor(self, color: tuple):

		self.image.fill(color)

		if hasattr(self, "text"):
			
			self.text.Draw(self.image)
