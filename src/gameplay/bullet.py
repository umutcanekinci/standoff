from __future__ import annotations

import pygame
from pygame.math import Vector2 as Vec

from util.constants import BULLET_SPEED, BULLET_DAMAGE, BULLET_LAYER, Blue
from gameplay.game_sprite import GameSprite


class Bullet(GameSprite):
    def __init__(self, source, position, angle) -> None:
        self.world, self.source = source.world, source
        self.movement_speed = BULLET_SPEED
        self.damage = BULLET_DAMAGE
        self.angle = angle

        super().__init__(position, size=(10, 10), layer=BULLET_LAYER)

        surface = pygame.Surface((10, 10), pygame.SRCALPHA)
        pygame.draw.circle(surface, Blue, (5, 5), 5)
        self.set_image(surface)
        self.set_position(position)

        self.velocity = Vec(1, 0).rotate(-self.angle) * self.movement_speed
        self.rotate(self.angle)

        self.world.bullets.append(self)

    def move(self):
        self.set_position(self.position + self.velocity * self.world.delta_time)

    def update(self) -> None:
        self.move()

        if any(self.rect.colliderect(wall.rect) for wall in self.world.walls):
            self.kill()
            return

        for mob in list(self.world.mobs):
            if mob is not self.source and self.rect.colliderect(mob.rect):
                # The world decides what a hit means: report it to the server
                # online (it owns mob HP), or apply it locally offline.
                self.world.hit_mob(mob, self.damage)
                self.kill()
                return

        for player in list(self.world.players):
            if player is not self.source and self.rect.colliderect(player.rect):
                player.velocity = Vec(0, 0)
                player.lose_hp(self.damage)
                self.kill()
                return
