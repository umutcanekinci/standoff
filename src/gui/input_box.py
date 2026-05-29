from util.constants import *
from gui.object import Object


class InputBox(Object):

	def __init__(self, position, size, text='', inactive_text = '', sprite_groups: list=[], parent_rect: pygame.Rect=None):

		super().__init__(position, size, sprite_groups=sprite_groups, parent_rect=parent_rect)
		self._layer = GUI_LAYER

		self.color = pygame.Color('dodgerblue2') # ('lightskyblue3')
		self.text = text
		self.inactive_text = inactive_text
		self.active = True
		
		self.rerender()

	def handle_events(self, event, mouse_position, keys):

		if event.type == pygame.MOUSEBUTTONDOWN:

			# If the user clicked on the input_box rect.
			if self.screen_rect.collidepoint(mouse_position):

				# Toggle the active variable.
				self.active = True #not self.active

			else:

				self.active = False

			# Change the current color of the input box.
			self.color = pygame.Color('dodgerblue2') if self.active else Gray
			self.rerender()

		if event.type == pygame.KEYDOWN:

			if self.active:

				if event.key == pygame.K_BACKSPACE:

					self.text = self.text[:-1]

				elif self.text_surface.get_width() < self.rect.width - 25:

					self.text += event.unicode

				self.rerender()

	def rerender(self):

		self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA)

		if self.active or self.text:
			
			self.text_surface = pygame.font.Font(None, 32).render(self.text, True, self.color)
		
		else:

			self.text_surface = pygame.font.Font(None, 20).render(self.inactive_text, True, self.color)
	
		pygame.draw.rect(self.image, self.color, pygame.Rect((0, 0), self.rect.size), 2)
		self.image.blit(self.text_surface, (self.rect.width/2-self.text_surface.get_width()/2, self.rect.height/2-self.text_surface.get_height()/2))
