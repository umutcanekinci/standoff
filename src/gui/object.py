from util.constants import *
from pygame_core.asset_path import ImagePath

def get_image(path: ImagePath, size=(0, 0)):

	image = pygame.image.load(path).convert_alpha()

	if size[0] and size[1] and size != image.get_size():

		return pygame.transform.scale(image, size)

	return image

class Object(pygame.sprite.Sprite):

	def __init__(self, position: tuple=("CENTER", "CENTER"), size: tuple=(0, 0), image_path: ImagePath=None, sprite_groups=[], parent_rect: pygame.Rect = WINDOW_RECT):

		super().__init__(sprite_groups)

		self.image = pygame.Surface(size, pygame.SRCALPHA)
		self.rect = self.image.get_rect()
		self.screen_rect = self.rect.copy()
		self.is_mouse_holding = False
		
		self.load_image(image_path)
		self.set_parent_rect(parent_rect)
		self.set_position(position)
		self.set_visible(True)
		
	def set_visible(self, value):
		
		self.is_visible = value
		
		if self.is_visible:

			if hasattr(self, '_image'):

				self.image = self._image

		else:

			if hasattr(self, 'image'):

				self._image = self.image
				self.image = None

	def rerender(self):

		self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA)
		self.load_image(self.image_path)

	def load_image(self, image_path):
		
		self.image_path = image_path

		if image_path:	
			
			image = get_image(image_path, self.rect.size)

			if not self.rect.size == image.get_rect().size:

				self.screen_rect.size = self.rect.size = image.get_rect().size

			self.image.blit(image, (0, 0))

	def set_parent_rect(self, rect: pygame.Rect):

		self.parent_rect = rect

	def set_position(self, position: tuple) -> None:

		self.set_x(position[0])
		self.set_y(position[1])
		
	def set_x(self, x: int) -> None:

		if x == "CENTER":
		
			self.rect.centerx = self.parent_rect.width / 2
			
		elif x == "LEFT":

			self.rect.x = 0

		elif x == "RIGHT":

			self.rect.x = self.parent_rect.width - self.rect.width

		else:

			self.rect.x = x

		self.screen_rect.x = self.parent_rect.x + self.rect.x # image rect is the screen rect of the parent

	def set_y(self, y: int) -> None:

		if y == "CENTER":
		
			self.rect.centery = self.parent_rect.height / 2
			
		elif y == "TOP":

			self.rect.y = 0

		elif y == "BOTTOM":

			self.rect.y = self.parent_rect.height - self.rect.height

		else:

			self.rect.y = y

		self.screen_rect.y = self.parent_rect.y + self.rect.y # image rect is the screen rect of the parent

	def handle_events(self, event, mouse_position, keys):

		if event.type == pygame.MOUSEBUTTONUP:

			if not self.is_mouse_button_up(event, mouse_position):

				self.is_mouse_holding = False

		if self.is_mouse_button_down(event, mouse_position):

			self.is_mouse_holding = True

	def is_mouse_over(self, mouse_position: tuple) -> bool:
		
		return mouse_position != None and self.screen_rect.collidepoint(mouse_position)

	def is_mouse_button_down(self, event: pygame.event.Event, mouse_position: tuple) -> bool:

		return self.is_mouse_over(mouse_position) and event.type == pygame.MOUSEBUTTONDOWN

	def is_mouse_button_up(self, event: pygame.event.Event, mouse_position: tuple) -> bool:

		return self.is_mouse_over(mouse_position) and event.type == pygame.MOUSEBUTTONUP

	def is_mouse_click(self, event: pygame.event.Event, mouse_position: tuple) -> bool:
		
		if self.is_mouse_button_up(event, mouse_position) and self.is_mouse_holding:
			
			self.is_mouse_holding = False
			return True
		
		return False

	def draw(self, image: pygame.Surface):

		if self.is_visible:
			
			image.blit(self.image, self.rect)
