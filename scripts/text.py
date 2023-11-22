from settings import *
from object import Object

class Text(Object):

	def __init__(self, position, text='', textSize=25, antialias=True, color=White, backgroundColor=None, fontPath = None, spriteGroups: list=[], parentRect: pygame.Rect=WINDOW_RECT) -> None:

		super().__init__(position, (0, 0), None, spriteGroups, parentRect)

		self.position = position
		self.AddText(text, textSize, antialias, color, backgroundColor, fontPath)

	def AddText(self, text, textSize, antialias=True, color=White, backgroundColor=None, fontPath=None):

		self.text, self.textSize, self.antialias, self.color, self.backgroundColor, self.fontPath = text, textSize, antialias, color, backgroundColor, fontPath
		self.image = pygame.font.Font(fontPath, textSize).render(text, antialias, color, backgroundColor)
		self.rect = self.image.get_rect()
		self.SetPosition(self.position)
 
	def UpdateText(self, text: str) -> None:

		self.AddText(text, self.textSize, self.antialias, self.color, self.backgroundColor, self.fontPath)

	def UpdateColor(self, color: tuple):

		self.AddText(self.text, self.textSize, self.antialias, color, self.backgroundColor, self.fontPath)
