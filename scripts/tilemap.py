from object import Object
from settings import *
from path import ImagePath
import pytmx
import pygame

class Tile(Object):
	
	def __init__(self, tileType, rowNumber, columnNumber, spriteGroups) -> None:
		
		super().__init__((TILE_SIZE*columnNumber, TILE_SIZE*rowNumber), (TILE_SIZE, TILE_SIZE), ImagePath("tile_" + str(tileType), "tiles"), spriteGroups)

class Wall(Tile):

	def __init__(self, tileType, rowNumber, columnNumber, spriteGroups) -> None:
		
		super().__init__(tileType, rowNumber, columnNumber, spriteGroups)

class Tree(Tile):

	def __init__(self, rowNumber, columnNumber, spriteGroups) -> None:
		
		super().__init__(rowNumber, columnNumber, spriteGroups)
		self.HP = 100

	def LoseHP(self, value):

		self.HP -= value

		if self.HP <= 0:

			self.kill()


class TileMap(Object):

	def __init__(self, game, fileName, borderWidth):

		self.spawnPoints = {0 : (120, 120), 1 : (220, 220)}
		self.game = game
		self.borderWidth = borderWidth
		self.tilemap =  pytmx.load_pygame(fileName, pixelalpha=True)
		self.tileWidth, self.tileHeight = self.tilemap.tilewidth, self.tilemap.tileheight
		self.columnCount, self.rowCount = self.tilemap.width, self.tilemap.height

		super().__init__((0, 0), (self.columnCount * self.tileWidth + self.borderWidth / 2, self.rowCount * self.tileHeight + self.borderWidth / 2), spriteGroups=self.game.allSprites)
		self.Render()

	def Render(self):

		self.image = pygame.Surface((self.columnCount * self.tileWidth + self.borderWidth / 2, self.rowCount * self.tileHeight + self.borderWidth / 2), pygame.SRCALPHA)
		
		tileImage = self.tilemap.get_tile_image_by_gid

		for layer in self.tilemap.visible_layers:

			if isinstance(layer, pytmx.TiledTileLayer):

				for x, y, gid in layer:

					tile = tileImage(gid)

					if tile:

						self.image.blit(tile, (x * self.tileWidth, y * self.tileHeight))

		self.DrawGrid()

	def DrawGrid(self):

		# Draw column lines
		for columnNumber in range(self.columnCount+1):

			pygame.draw.line(self.image, Gray, (columnNumber*self.tileWidth, 0), (columnNumber*self.tileWidth, self.rect.height), self.borderWidth)

		# Draw row lines
		for rowNumber in range(self.rowCount+1):

			pygame.draw.line(self.image, Gray, (0, rowNumber*self.tileHeight), (self.rect.width, rowNumber*self.tileHeight), self.borderWidth)
