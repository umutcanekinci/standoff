from settings import *
from object import Object


class InputBox(Object):

	def __init__(self, position, size, text='', inactiveText = '', spriteGroups: list=[], parentRect: pygame.Rect=None):

		super().__init__(position, size, spriteGroups=spriteGroups, parentRect=parentRect)
		self._layer = GUI_LAYER

		self.color = pygame.Color('dodgerblue2') # ('lightskyblue3')
		self.text = text
		self.inactiveText = inactiveText
		self.active = True
		
		self.Rerender()

	def HandleEvents(self, event, mousePosition, keys):

		if event.type == pygame.MOUSEBUTTONDOWN:

			# If the user clicked on the input_box rect.
			if self.screenRect.collidepoint(mousePosition):

				# Toggle the active variable.
				self.active = True #not self.active

			else:

				self.active = False

			# Change the current color of the input box.
			self.color = pygame.Color('dodgerblue2') if self.active else Gray
			self.Rerender()

		if event.type == pygame.KEYDOWN:

			if self.active:

				if event.key == pygame.K_BACKSPACE:

					self.text = self.text[:-1]

				elif self.textSurface.get_width() < self.rect.width - 25:

					self.text += event.unicode

				self.Rerender()

	def Rerender(self):

		self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA)

		if self.active or self.text:
			
			self.textSurface = pygame.font.Font(None, 32).render(self.text, True, self.color)
		
		else:

			self.textSurface = pygame.font.Font(None, 20).render(self.inactiveText, True, self.color)
	
		pygame.draw.rect(self.image, self.color, pygame.Rect((0, 0), self.rect.size), 2)
		self.image.blit(self.textSurface, (self.rect.width/2-self.textSurface.get_width()/2, self.rect.height/2-self.textSurface.get_height()/2))
