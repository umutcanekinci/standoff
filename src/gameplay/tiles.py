import pygame
from gui.object import Object
from pygame_core.asset_path import ImagePath
from util.constants import *


class Tile(Object):

    def __init__(self, tile_type, row_number, column_number, sprite_groups) -> None:
        super().__init__((TILE_SIZE * column_number, TILE_SIZE * row_number), (TILE_SIZE, TILE_SIZE), ImagePath("tile_" + str(tile_type), "tiles"), sprite_groups)


class Wall(Tile):

    def __init__(self, tile_type, row_number, column_number, sprite_groups) -> None:
        super().__init__(tile_type, row_number, column_number, sprite_groups)


class Tree(Tile):

    def __init__(self, row_number, column_number, sprite_groups) -> None:
        super().__init__(row_number, column_number, sprite_groups)
        self.hp = 100

    def lose_hp(self, value):
        self.hp -= value
        if self.hp <= 0:
            self.kill()


class Obstacle(Object):

    def __init__(self, game, position, size) -> None:
        self.game = game
        super().__init__(position, size, None, sprite_groups=game.walls)

    def draw_rect(self, surface):
        pygame.draw.rect(surface, Yellow, self.game.camera.apply(self.rect), 2)
