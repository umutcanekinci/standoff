import pygame
from util.constants import EFFECT_LAYER, FLASH_DURATOION
from gameplay.game_sprite import GameSprite
from random import randint, choice


class MuzzleFlash(GameSprite):
    def __init__(self, game, position, angle):
        self.game = game
        self.spawn_time = pygame.time.get_ticks()
        size = randint(20, 50)
        size = size, size

        super().__init__(
            position, size=size, image_path=choice(game.gun_flashes), layer=EFFECT_LAYER
        )
        self.set_position(position)
        self.rotate(angle)

        game.effects.append(self)

    def update(self):
        if pygame.time.get_ticks() - self.spawn_time > FLASH_DURATOION:
            self.kill()
