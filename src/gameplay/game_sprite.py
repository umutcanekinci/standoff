"""ECS base for in-world entities — replaces the old pygame.sprite-based gui.Object.

A GameObject with a SpriteRenderer2D that stays duck-compatible with the custom
Camera: it exposes `.image` (current surface, rotated or not) and `.rect` (a
Transform, i.e. a pygame.Rect subclass) so `camera.draw(surface, sprite)` blits
it unchanged. Adds world-space `position`, cheap `rotate`, a draw `layer`, and an
`alive` flag (replacing pygame Sprite.kill()).
"""

import pygame
from typing import cast
from pygame.math import Vector2

from pygame_core.ecs.game_object import GameObject
from pygame_core.ecs.components.sprite_renderer2d import SpriteRenderer2D
from pygame_core.image import load_image

# Rotating a surface every frame is expensive. Quantize the angle and cache the
# result, keyed by (source-surface identity, angle bucket). Shared across all
# sprites — combined with the scaled-image sharing in Entity, every zombie facing
# the same way reuses one rotated Surface, so we rotate ~(360/step) times total
# instead of once per mob per frame.
ROTATION_STEP_DEG = 5
_ROTATION_CACHE: dict[tuple[int, int], pygame.Surface] = {}


class GameSprite(GameObject):
    def __init__(
        self,
        position: tuple | Vector2 = (0, 0),
        size: tuple = (0, 0),
        image_path=None,
        layer=0,
    ):
        super().__init__()
        self._renderer = self.add_component(SpriteRenderer2D)
        self.layer = layer
        self.alive = True
        self.position = Vector2(position)
        self.original_image: pygame.Surface
        self.rotated_image: pygame.Surface | None = None
        self.is_rotated = False

        if image_path is not None:
            self.set_image(cast(pygame.Surface, load_image(image_path, size)))
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

    def set_position(self, position: tuple | Vector2) -> None:
        self.position = Vector2(position)
        self.rect.center = self._int_pos()

    def rotate(self, angle: float) -> None:
        bucket = int(round(angle / ROTATION_STEP_DEG)) * ROTATION_STEP_DEG
        key = (id(self.original_image), bucket)
        cached = _ROTATION_CACHE.get(key)
        if cached is None:
            cached = pygame.transform.rotate(self.original_image, bucket)
            _ROTATION_CACHE[key] = cached
        self.rotated_image = cached
        self.is_rotated = True
        self.rect.size = cached.get_size()
        self.rect.center = self._int_pos()

    def kill(self) -> None:
        self.alive = False
