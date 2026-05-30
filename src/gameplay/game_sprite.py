"""ECS base for in-world entities — replaces the old pygame.sprite-based gui.Object.

A GameObject with a SpriteRenderer2D that stays duck-compatible with the custom
Camera: it exposes `.image` (current surface, rotated or not) and `.rect` (a
Transform, i.e. a pygame.Rect subclass) so `camera.draw(surface, sprite)` blits
it unchanged. Adds world-space `position`, cheap `rotate`, a draw `layer`, and an
`alive` flag (replacing pygame Sprite.kill()).
"""
import pygame
from pygame.math import Vector2

from pygame_core.ecs.game_object import GameObject
from pygame_core.ecs.components.sprite_renderer2d import SpriteRenderer2D
from pygame_core.image import load_image


class GameSprite(GameObject):

    def __init__(self, position=(0, 0), size=(0, 0), image_path=None, layer=0):
        super().__init__()
        self._renderer = self.add_component(SpriteRenderer2D)
        self.layer = layer
        self.alive = True
        self.position = Vector2(position)
        self.original_image = None
        self.rotated_image = None
        self.is_rotated = False

        if image_path is not None:
            self.set_image(load_image(image_path, size))
        else:
            self.set_image(pygame.Surface(size, pygame.SRCALPHA))

    def _int_pos(self):
        return (int(self.position.x), int(self.position.y))

    def set_image(self, surface: pygame.Surface) -> None:
        self.original_image = surface
        self.rotated_image = None
        self.is_rotated = False
        self._renderer.set_image(surface)
        self.rect.size = surface.get_size()
        self.rect.center = self._int_pos()

    @property
    def image(self) -> pygame.Surface | None:
        return self.rotated_image if self.is_rotated else self.original_image

    def set_position(self, position) -> None:
        self.position = Vector2(position)
        self.rect.center = self._int_pos()

    def rotate(self, angle: float) -> None:
        self.rotated_image = pygame.transform.rotate(self.original_image, angle)
        self.is_rotated = True
        self.rect.size = self.rotated_image.get_size()
        self.rect.center = self._int_pos()

    def kill(self) -> None:
        self.alive = False
