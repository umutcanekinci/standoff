from __future__ import annotations

import pygame

from pygamine.tilemap import TiledMap
from util.constants import TILE_WIDTH, TILE_HEIGHT, Gray
from gameplay.tiles import Obstacle


class Map(TiledMap):
    """A Tiled .tmx for Standoff: parses base/spawn points + wall obstacles,
    and renders the tile layers (with a grid overlay) into a surface the custom
    Camera blits. Generic tmx loading / pre-render comes from pygamine.TiledMap."""

    camera: object = None  # set by Camera.__init__
    image: pygame.Surface  # built by render()
    rect: pygame.Rect  # built by render()

    def __init__(self, world, tmx_path, border_width):
        super().__init__(tmx_path)
        self.world = world
        self.border_width = border_width
        self.base_points, self.spawn_points = {}, {}
        self.get_objects()

    def get_objects(self) -> None:
        for obj in self.tmx.objects:
            name = obj.name or ""  # Tiled objects may be unnamed
            if "base" in name:
                self.base_points[int(name[-1:])] = (
                    obj.x + TILE_WIDTH / 2,
                    obj.y + TILE_HEIGHT / 2,
                )
            if "spawnPoint" in name:  # matches the Tiled object names (spawnPoint1..N)
                self.spawn_points[int(name[-1:])] = (
                    obj.x + TILE_WIDTH / 2,
                    obj.y + TILE_HEIGHT / 2,
                )
            if "wall" in name:
                Obstacle(self.world, (obj.x, obj.y), (obj.width, obj.height))

    def render(self):
        image = self.pre_render(alpha=True)
        # The custom Camera blits this whole surface as the full-screen background
        # every frame. convert() (opaque) makes that a plain copy; convert_alpha()
        # would keep the per-pixel alpha channel and force a full-screen *blend*
        # each frame — ~50ms at 1920x1080 on a phone software backbuffer, which
        # was the whole in-game frame budget. The map always fills the viewport
        # (the Camera clamps to map bounds) and there's no per-frame screen clear,
        # so it must be opaque anyway; any untiled cell reads as black (same as
        # the uncleared buffer did before, just stable).
        if pygame.display.get_surface() is not None:
            image = image.convert()
        self.image = image
        self.rect = self.image.get_rect()
        self.draw_grid()

    def draw_grid(self):
        for column in range(self.cols + 1):
            x = column * self.tile_size
            pygame.draw.line(
                self.image, Gray, (x, 0), (x, self.rect.height), self.border_width
            )
        for row in range(self.rows + 1):
            y = row * self.tile_size
            pygame.draw.line(
                self.image, Gray, (0, y), (self.rect.width, y), self.border_width
            )
