#-# Importing Packages #-#
import pygame
from default.path import *
from default.image import *
from default.color import *

#-# Object Class #-#
class Object(dict[str : pygame.Surface]):

	def __init__(self, position: tuple = ("CENTER", "CENTER"), surfaceRect: pygame.Rect = pygame.Rect(0, 0, 0, 0), size: tuple = (0, 0), imagePaths = {}, visible = True):
		
		super().__init__()
		self.SetStatus(None)
		
		self.imagePaths = imagePaths

		self.SetVisible(visible)
		self.SetSize(size)
		self.SetPosition(position, surfaceRect)

	def AddText(self, status, text, textSize, antialias=True, color=White, backgroundColor=None, fontPath = None):

		self.AddSurface(status, pygame.font.Font(fontPath, textSize).render(text, antialias, color, backgroundColor))

	def AddImages(self, imagePaths):

		for status, path in imagePaths.items():
			
			self.AddImage(status, path)

	def AddImage(self, status, imagePath):

		self.AddSurface(status, GetImage(imagePath, self.size))

	def AddSurface(self, status: str, surface: pygame.Surface):
		
		self[status] = surface

		if not self.status:

			if status == "Normal":
			
				self.SetStatus("Normal")

	def Resize(self, size: tuple):

		self = Object(self.position, size, self.imagePaths, self.surfaceRect, self.show)

	def SetSize(self, size):
		
		if size and size[0] and size[1]:

			self.size = self.width, self.height = size

			self.AddImages(self.imagePaths)

		else:

			self.size = [0, 0]

			self.AddImages(self.imagePaths)

			if len(self) > 0:

				if "Normal" in self:

					size = self["Normal"].get_rect().size
				
				else:

					size = list(self.values())[0].get_rect().size

				self.size = self.width, self.height = size
			
	def SetPosition(self, position: tuple, surfaceRect: tuple) -> None:

		self.position = position
		self.surfaceRect = surfaceRect

		self.SetX(position[0], surfaceRect)
		self.SetY(position[1], surfaceRect)

	def SetX(self, x: int, surfaceRect) -> None:

		if not hasattr(self, 'rect'):

			self.rect = pygame.Rect((0, 0), self.size)
			self.screenRect = pygame.Rect((0, 0), self.size)

		if x == "CENTER":
		
			self.rect.x = (surfaceRect.w - self.rect.w)/2
			self.screenRect.x = surfaceRect.x + self.rect.x

		else:

			self.rect.x = x
			self.screenRect.x = x + surfaceRect.x # surface rect is the screen rect of the parent

	def SetY(self, y: int, surfaceRect) -> None:
		
		if not hasattr(self, 'rect'):

			self.rect = pygame.Rect((0, 0), self.size)

		if y == "CENTER":
		
			self.rect.y = (surfaceRect.h - self.rect.h)/2
			self.screenRect.y = surfaceRect.y + self.rect.y

		else:

			self.rect.y = y
			self.screenRect.y = y + surfaceRect.y

	def isMouseOver(self, mousePosition: tuple) -> bool:
		
		if mousePosition != None and self.screenRect.collidepoint(mousePosition) and self.visible:

			return True
		
		return False

	def isMouseClick(self, event: pygame.event.Event, mousePosition: tuple) -> bool:

		if self.isMouseOver(mousePosition) and event.type == pygame.MOUSEBUTTONUP:

			return True
		
		return False

	def SetVisible(self, value):
		
		self.visible = value

	def HandleEvents(self, event, mousePosition, keys):
		
		if "Mouse Click" in self and self.isMouseClick(event, mousePosition):
			
			self.SetStatus("Mouse Click")

		elif "Mouse Over" in self and self.isMouseOver(mousePosition):

			self.SetStatus("Mouse Over")

		elif "Normal" in self:

			self.SetStatus("Normal")

	def SetStatus(self, status: str):

		self.status = status

	def SetVelocity(self, velocity: tuple):
		
		self.velocity = velocity

	def Move(self, velocity: tuple):
		
		self.SetPosition((self.rect.topleft + pygame.math.Vector2(velocity)), self.surfaceRect)

	def __Move(self):

		if hasattr(self, "velocity"):

			self.Move(self.velocity)

	def Draw(self, surface) -> None:

		self.__Move()

		if self.visible and self.status in self:
				
			surface.blit(self[self.status], self.rect)

		