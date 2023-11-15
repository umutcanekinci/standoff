#-# Import Packages #-#
import pygame
from default.object import Object

#-# Input Box Class #-#
class InputBox(Object):

	def __init__(self, position, size, surfaceRect, text=''):

		super().__init__(position, size, surfaceRect=surfaceRect)
		
		self.color = pygame.Color('dodgerblue2') # ('lightskyblue3')
		self.text = text
		self.txt_surface = pygame.font.Font(None, 32).render(text, True, self.color)
		self.active = True # False

	def HandleEvents(self, event, mousePosition, keys):

		if event.type == pygame.MOUSEBUTTONDOWN:

			# If the user clicked on the input_box rect.
			if self.screenRect.collidepoint(mousePosition):

				# Toggle the active variable.
				self.active = True #not self.active

			else:

				self.active = False

			# Change the current color of the input box.
			self.color = pygame.Color('dodgerblue2') if self.active else pygame.Color('lightskyblue3')

		if event.type == pygame.KEYDOWN:

			if self.active:

				if event.key == pygame.K_BACKSPACE:

					self.text = self.text[:-1]

				else:

					self.text += event.unicode

				# Re-render the text.
				self.txt_surface = pygame.font.Font(None, 32).render(self.text, True, self.color)

	def update(self):
		# Resize the box if the text is too long.
		width = max(200, self.txt_surface.get_width()+10)
		if self.rect.w < width:        
			self.rect.w = width

	def Draw(self, surface):

		# Blit the text.
		
		surface.blit(self.txt_surface, (self.rect.x+5, self.rect.y+5))
		# Blit the rect.
		pygame.draw.rect(surface, self.color, self.rect, 2)
		self.AddSurface("Normal", self.txt_surface)
		print(self.rect)
		super().Draw(surface)