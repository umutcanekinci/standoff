from settings import *
from object import Object

class Text(Object):

	def __init__(self, position, text='', textSize=25, antialias=True, color=White, backgroundColor=None, fontPath = None, spriteGroups: list=[], parentRect: pygame.Rect=WINDOW_RECT) -> None:

		super().__init__(position, (0, 0), None, spriteGroups, parentRect)
		self._layer = GUI_LAYER
		
		self.position = position
		
		self.text, self.textSize, self.antialias, self.textColor, self.backgroundColor, self.fontPath = text, textSize, antialias, color, backgroundColor, fontPath
		self.Render()
		
	def Render(self):

		self.image = pygame.font.Font(self.fontPath, self.textSize).render(self.text, self.antialias, self.textColor, self.backgroundColor)
		self.rect = self.image.get_rect()
		self.SetPosition(self.position)
 
	def UpdateText(self, text: str) -> None:

		self.text = text
		self.Render()

	def Rerender(self):

		self.Render()

	def SetColor(self, color: tuple):

		self.textColor = color
		self.Render()