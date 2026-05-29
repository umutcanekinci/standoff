from util.constants import *
from gui.object import Object
from pygame_core.asset_path import ImagePath
from gui.text import Text

class Button(Object):

	def __init__(self, position: tuple=("CENTER", "CENTER"), size: tuple=(0, 0), color: tuple = Blue, mouse_over_color: tuple = Red, image_path: ImagePath=None, sprite_groups: list=[], parent_rect: pygame.Rect=None, text: str="", text_size: int=20, text_color: tuple=White, text_font_path: pygame.font.Font=None, is_active=True):

		super().__init__(position, size, image_path, sprite_groups, parent_rect)
		self._layer = GUI_LAYER

		self.normal_color, self.mouse_over_color = color, mouse_over_color
		self.color = self.normal_color

		if text:

			self.set_text(text, text_size, True, text_color, None, text_font_path)

		if is_active:

			self.enable()

		else:
			
			self.disable()

	def enable(self):

		self.active = True
		self.rerender()

	def disable(self):

		self.active = False
		self.color = Gray
		self.rerender()

	def set_text(self, text: str, text_size: int, antialias: bool, color: tuple, background_color, font_path: pygame.font.Font = None) -> None:

		self.text = Text(("CENTER", "CENTER"), text, text_size, antialias, color, background_color, font_path, (), self.screen_rect)

	def handle_events(self, event, mouse_position, keys):

		super().handle_events(event, mouse_position, keys)

		self.update_color(mouse_position)
		
		self.rerender()

	def update_color(self, mouse_position):

		if self.active:

			self.color = self.mouse_over_color if self.is_mouse_over(mouse_position) else self.normal_color
		
		else:
			
			self.color = Gray

	def rerender(self):

		super().rerender()
		
		self.image.fill(self.color)
		pygame.draw.rect(self.image, Black, ((0, 0), self.rect.size), 2)

		if hasattr(self, "text"):
			
			self.text.draw(self.image)

	def is_mouse_click(self, event: pygame.event.Event, mouse_position: tuple) -> bool:

		return super().is_mouse_click(event, mouse_position) and self.active

class EllipseButton(Button):

	def __init__(self, position: tuple = ("CENTER", "CENTER"), size: tuple = (0, 0), color: tuple = Blue, mouse_over_color: tuple = Red, image_path: ImagePath = None, sprite_groups: list = [], parent_rect: pygame.Rect = None, text: str = "", text_size: int = 20, text_color: tuple = White, text_font_path: pygame.font.Font = None, is_active=True):
		
		self.stay_down = False
		super().__init__(position, size, color, mouse_over_color, image_path, sprite_groups, parent_rect, text, text_size, text_color, text_font_path, is_active)

	def set_text(self, text: str, text_size: int, antialias: bool, color: tuple, background_color, font_path: pygame.font.Font = None) -> None:
		
		super().set_text(text, text_size, antialias, color, background_color, font_path)
	
		self.text_up_rect = pygame.Rect((self.text.rect.x, self.text.rect.y - 5), self.text.rect.size)
		self.text_down_rect = pygame.Rect((self.text.rect.x, self.text.rect.y + 5), self.text.rect.size)

	def rerender(self):

		polygon_up_rect = pygame.Rect(0, 0, self.rect.width, self.rect.height-5)
		polygon_down_rect = pygame.Rect(0, 5, self.rect.width, self.rect.height-5)

		Object.rerender(self)

		pygame.draw.rect(self.image, Black, polygon_down_rect, 0, 25)

		if self.stay_down:

			pygame.draw.rect(self.image, self.color, polygon_down_rect, 0, 25)
			pygame.draw.rect(self.image, Black, polygon_down_rect, 1, 25)

			if hasattr(self, "text"):

				self.text.rect = self.text_down_rect

		else:

			pygame.draw.rect(self.image, self.color, polygon_up_rect, 0, 25)
			pygame.draw.rect(self.image, Black, polygon_up_rect, 2, 25)

			if hasattr(self, "text"):

				self.text.rect = self.text_up_rect

		if hasattr(self, "text"):
			
			self.text.draw(self.image)

	def update_color(self, mouse_position):

		if self.active:

			self.color = self.mouse_over_color if self.is_mouse_over(mouse_position) or self.stay_down else self.normal_color
		
		else:

			self.color = Gray

	def handle_events(self, event, mouse_position, keys):

		Object.handle_events(self, event, mouse_position, keys)

		if event.type == pygame.MOUSEBUTTONDOWN and self.is_mouse_over(mouse_position):

			self.stay_down = True

		if event.type == pygame.MOUSEBUTTONUP:

			self.stay_down = False

		
		self.update_color(mouse_position)

		self.rerender()

class TriangleButton(Button):

	def __init__(self, position: tuple = ("CENTER", "CENTER"), size: tuple = (0, 0), color: tuple = Blue, mouse_over_color: tuple = Red, image_path: ImagePath = None, sprite_groups: list = [], parent_rect: pygame.Rect = None, text: str = "", text_size: int = 20, text_color: tuple = White, text_font_path: pygame.font.Font = None, is_active=True, rotation="RIGHT"):
		
		self.stay_down, self.rotation = False, rotation
		super().__init__(position, size, color, mouse_over_color, image_path, sprite_groups, parent_rect, text, text_size, text_color, text_font_path, is_active)

	def set_text(self, text: str, text_size: int, antialias: bool, color: tuple, background_color, font_path: pygame.font.Font = None) -> None:
		
		super().set_text(text, text_size, antialias, color, background_color, font_path)
	
		self.text_up_rect = pygame.Rect((self.text.rect.x, self.text.rect.y - 5), self.text.rect.size)
		self.text_down_rect = pygame.Rect((self.text.rect.x, self.text.rect.y + 5), self.text.rect.size)

	def rerender(self):

		if self.rotation == "RIGHT":

			polygon_up_points = [(0, 0), (self.rect.width, self.rect.height/2-5), (0, self.rect.height-10)]
			polygon_down_points = [(0, 10), (self.rect.width, self.rect.height/2+5), (0, self.rect.height)]
		
		elif self.rotation == "LEFT":

			polygon_up_points = [(self.rect.width, 0), (0, self.rect.height/2-5), (self.rect.width, self.rect.height-10)]
			polygon_down_points = [(self.rect.width, 10), (0, self.rect.height/2+5), (self.rect.width, self.rect.height)]

		Object.rerender(self)

		pygame.draw.polygon(self.image, Black, polygon_down_points)
		
		if self.stay_down:

			pygame.draw.polygon(self.image, self.color, polygon_down_points)
			pygame.draw.polygon(self.image, Black, polygon_down_points, 1)

			if hasattr(self, "text"):

				self.text.rect = self.text_down_rect

		else:

			pygame.draw.polygon(self.image, self.color, polygon_up_points, 0)
			pygame.draw.polygon(self.image, Black, polygon_up_points, 2)

			if hasattr(self, "text"):

				self.text.rect = self.text_up_rect

		if hasattr(self, "text"):
			
			self.text.draw(self.image)

	def update_color(self, mouse_position):
		
		if self.active:

			self.color = self.mouse_over_color if self.is_mouse_over(mouse_position) or self.stay_down else self.normal_color

		else:
			
			self.color = Gray

	def handle_events(self, event, mouse_position, keys):

		Object.handle_events(self, event, mouse_position, keys)

		if event.type == pygame.MOUSEBUTTONDOWN and self.is_mouse_over(mouse_position):

			self.stay_down = True

		if event.type == pygame.MOUSEBUTTONUP:

			self.stay_down = False

		self.update_color(mouse_position)

		self.rerender()