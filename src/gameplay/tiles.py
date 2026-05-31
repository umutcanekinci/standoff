import pygame

from util.constants import WALL_LAYER, Yellow
from gameplay.game_sprite import GameSprite


class Obstacle(GameSprite):
    def __init__(self, game, position, size) -> None:
        self.game = game
        # Map passes a top-left position; GameSprite is centred, so offset by half-size.
        center = (position[0] + size[0] / 2, position[1] + size[1] / 2)
        super().__init__(center, size=size, layer=WALL_LAYER)
        game.walls.append(self)

    def draw_rect(self, surface):
        pygame.draw.rect(surface, Yellow, self.game.camera.apply(self.rect), 2)
