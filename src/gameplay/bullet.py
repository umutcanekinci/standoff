import pygame
from pygame.math import Vector2 as Vec

from util.constants import BULLET_SPEED, BULLET_DAMAGE, BULLET_LAYER, Blue
from gameplay.game_sprite import GameSprite


class Bullet(GameSprite):
    def __init__(self, source, position, angle) -> None:
        self.game, self.source = source.game, source
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

        self.game.bullets.append(self)

    def move(self):
        self.set_position(self.position + self.velocity * self.game.delta_time)

    def update(self) -> None:
        self.move()

        if any(self.rect.colliderect(wall.rect) for wall in self.game.walls):
            self.kill()
            return

        for mob in list(self.game.mobs):
            if mob is not self.source and self.rect.colliderect(mob.rect):
                mob.velocity = Vec(0, 0)
                mob.lose_hp(self.damage)
                self.kill()
                return

        for player in list(self.game.players):
            if player is not self.source and self.rect.colliderect(player.rect):
                player.velocity = Vec(0, 0)
                player.lose_hp(self.damage)
                self.kill()
                return
