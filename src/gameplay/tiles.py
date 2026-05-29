import pygame
from gui.object import Object
from pygame_core.asset_path import ImagePath
from util.constants import *


class Tile(Object):

    def __init__(self, tileType, rowNumber, columnNumber, spriteGroups) -> None:
        super().__init__((TILE_SIZE * columnNumber, TILE_SIZE * rowNumber), (TILE_SIZE, TILE_SIZE), ImagePath("tile_" + str(tileType), "tiles"), spriteGroups)


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
