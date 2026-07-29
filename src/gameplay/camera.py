"""standoff's camera: pygamine.Camera plus a follow() that recenters the
viewport on a target rect, and a batch draw() (accepts one object or an
iterable, with viewport culling) -- neither of which the base Camera
provides on its own. See pygamine.camera for the shared world<->screen
transform, edge-scroll, and zoom machinery this builds on.
"""

from __future__ import annotations

import pygame

from gameplay.map import Map
from pygamine.camera import Camera as _Camera
from pygamine.ecs.components.sprite_renderer2d import SpriteRenderer2D


class Camera(_Camera):
    def __init__(self, size: tuple, map: Map) -> None:
        super().__init__(pygame.Rect((0, 0), size), map_width=map.rect.width, map_height=map.rect.height)
        self.map = map
        self.map.camera = self

    def follow(self, target_rect: pygame.Rect) -> None:
        self._offset.x = self.rect.width / 2 - target_rect.centerx
        self._offset.y = self.rect.height / 2 - target_rect.centery
        self._clamp_offset()

    def apply(self, rect: pygame.Rect) -> pygame.Rect:
        screen_pos = self.world_to_screen(rect.topleft)
        return pygame.Rect(screen_pos, rect.size)

    def draw(self, image, objects) -> None:
        if not hasattr(objects, "__iter__"):
            objects = [objects]

        view = image.get_rect()

        for object in objects:
            screen_rect = self.apply(object.rect)

            # Cull: skip anything outside the view before touching its surface.
            if not screen_rect.colliderect(view):
                continue

            surface = self._surface_of(object)

            if surface is not None:
                image.blit(self.scale_image(surface), screen_rect)

    @staticmethod
    def _surface_of(obj):
        # GameSprite exposes `.image` (a property, already satisfying
        # pygamine's Drawable protocol directly); the old gui.Object set it
        # as a plain attribute; engine TextObject/GameObjects resolve
        # `.image` to their SpriteRenderer2D automatically (see
        # GameObject.image). Kept as an explicit fallback chain for
        # anything that predates that default -- harmless if every caller
        # already satisfies it via `.image` alone.
        image = getattr(obj, "image", None)

        if image is not None:
            return image

        renderer = (
            obj.get_component(SpriteRenderer2D)
            if hasattr(obj, "get_component")
            else None
        )

        return renderer.image if renderer else None
