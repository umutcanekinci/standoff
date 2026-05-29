from util.constants import *
from gui.object import Object

class Text(Object):

	def __init__(self, position, text='', text_size=25, antialias=True, color=White, background_color=None, font_path = None, sprite_groups: list=[], parent_rect: pygame.Rect=WINDOW_RECT) -> None:

		super().__init__(position, (0, 0), None, sprite_groups, parent_rect)
		self._layer = GUI_LAYER
		
		self.position = position
		
		self.text, self.text_size, self.antialias, self.text_color, self.background_color, self.font_path = text, text_size, antialias, color, background_color, font_path
		self.render()
		
	def render(self):

		self.image = pygame.font.Font(self.font_path, self.text_size).render(self.text, self.antialias, self.text_color, self.background_color)
		self.rect = self.image.get_rect()
		self.set_position(self.position)
 
	def update_text(self, text: str) -> None:

		self.text = text
		self.render()

	def rerender(self):

		self.render()

	def set_color(self, color: tuple):

		self.text_color = color
		self.render()