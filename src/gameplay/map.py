import pygame

from pygame_core.tilemap import TiledMap
from util.constants import *
from gameplay.tiles import Obstacle


class Map(TiledMap):
    """A Tiled .tmx for choose-your-way: parses base/spawn points + wall obstacles,
    and renders the tile layers (with a grid overlay) into a surface the custom
    Camera blits. Generic tmx loading / pre-render comes from pygame_core.TiledMap."""

    def __init__(self, game, tmx_path, border_width):
        super().__init__(tmx_path)
        self.game = game
        self.border_width = border_width
        self.base_points, self.spawn_points = {}, {}
        self.get_objects()

    def get_objects(self) -> None:
        for obj in self.tmx.objects:
            if "base" in obj.name:
                self.base_points[int(obj.name[-1:])] = obj.x + TILE_WIDTH / 2, obj.y + TILE_HEIGHT / 2
            if "spawn_point" in obj.name:
                self.spawn_points[int(obj.name[-1:])] = obj.x + TILE_WIDTH / 2, obj.y + TILE_HEIGHT / 2
            if "wall" in obj.name:
                Obstacle(self.game, (obj.x, obj.y), (obj.width, obj.height))

    def render(self):
        self.image = self.pre_render(alpha=True)
        self.rect = self.image.get_rect()
        self.draw_grid()

    def draw_grid(self):
        for column in range(self.cols + 1):
            x = column * self.tile_size
            pygame.draw.line(self.image, Gray, (x, 0), (x, self.rect.height), self.border_width)
        for row in range(self.rows + 1):
            y = row * self.tile_size
            pygame.draw.line(self.image, Gray, (0, y), (self.rect.width, y), self.border_width)
