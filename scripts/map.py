from settings import *
from object import Object
from path import ImagePath
from pytmx import TiledTileLayer, load_pygame

def isCollide(one, two):

	return one.hitRect.colliderect(two.rect)

def Collide(object: Object, direction: str, spriteGroup: pygame.sprite.Group) -> None:

	hits = pygame.sprite.spritecollide(object, spriteGroup, False, isCollide)

	if hits and hits[0] != object:
			
		if direction == 'x':

			if object.rect.x < hits[0].rect.x: #object.delta.x > 0:

				object.hitRect.right = hits[0].rect.left - .001

			else:

				object.hitRect.left = hits[0].rect.right + .001

			object.velocity.x = 0

		if direction == 'y':

			if object.rect.y < hits[0].rect.y: #object.delta.y > 0:
				
				object.hitRect.bottom = hits[0].rect.top - .001
			
			else:
				
				object.hitRect.top = hits[0].rect.bottom + .001
			
			object.velocity.y = 0
			
			""" 

			# Also this works with colliderect intead of spritecollide

			for wall in self.game.walls:
				
				if wall.rect.colliderect(self.hitRect):

					if self.delta.x > 0 :

						self.hitRect.right = wall.rect.left - .001

					else:

						self.hitRect.left = wall.rect.right + .001

					self.velocity.x = 0

					break

		if dir == 'y':

			for wall in self.game.walls:
				
				if wall.rect.colliderect(self.hitRect):

					if self.delta.y > 0:
						
						self.hitRect.bottom = wall.rect.top - .001
					
					else:
						
						self.hitRect.top = wall.rect.bottom + .001
					
					self.velocity.y = 0

					break
		"""
			

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

class Obstacle(Object):

	def __init__(self, game, position, size) -> None:
		
		self.game = game
		super().__init__(position, size, None, spriteGroups=game.walls)

	def DrawRect(self, surface):
		
		pygame.draw.rect(surface, Yellow, self.game.camera.Apply(self.rect), 2)

class Map(Object):

	def __init__(self, game, fileName, borderWidth):

		self.basePoints, self.spawnPoints = {}, {}
		self.game = game
		self.borderWidth = borderWidth
		self.Load(fileName)

	def Load(self, fileName):

		self.tiledMap = load_pygame(fileName, pixelalpha=True)
		self.tileWidth, self.tileHeight = self.tiledMap.tilewidth, self.tiledMap.tileheight
		self.columnCount, self.rowCount = self.tiledMap.width, self.tiledMap.height

		self.GetObjects()

	def GetObjects(self) -> None:

		for object in self.tiledMap.objects:

			if "base" in object.name:

				self.basePoints[int(object.name[-1:])] = object.x + TILE_WIDTH / 2, object.y + TILE_HEIGHT / 2

			if "spawnPoint" in object.name:

				self.spawnPoints[int(object.name[-1:])] = object.x + TILE_WIDTH / 2, object.y + TILE_HEIGHT / 2

			if "wall" in object.name:

				Obstacle(self.game, (object.x, object.y), (object.width, object.height))

	def Render(self):

		super().__init__((0, 0), (self.columnCount * self.tileWidth + self.borderWidth / 2, self.rowCount * self.tileHeight + self.borderWidth / 2))

		self.image = pygame.Surface((self.columnCount * self.tileWidth + self.borderWidth / 2, self.rowCount * self.tileHeight + self.borderWidth / 2), pygame.SRCALPHA)
		
		tileImage = self.tiledMap.get_tile_image_by_gid

		for layer in self.tiledMap.visible_layers:

			if isinstance(layer, TiledTileLayer):

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