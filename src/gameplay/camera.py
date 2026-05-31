import pygame

from gameplay.map import Map
from pygame_core.ecs.components.sprite_renderer2d import SpriteRenderer2D


class Camera:
    def __init__(self, size: tuple, map: Map):
        self.rect = pygame.Rect((0, 0), size)
        self.map = map
        self.map.camera = self

    def follow(self, target_rect):
        self.rect.x, self.rect.y = (
            -target_rect.centerx + (self.rect.width / 2),
            -target_rect.centery + (self.rect.height / 2),
        )

        self.rect.x = max(self.rect.width - self.map.rect.width, min(0, self.rect.x))
        self.rect.y = max(self.rect.height - self.map.rect.height, min(0, self.rect.y))

    def apply(self, rect: pygame.Rect):
        return pygame.Rect((self.rect.x + rect.x, self.rect.y + rect.y), rect.size)

    def draw(self, image, objects):
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
                image.blit(surface, screen_rect)

    @staticmethod
    def _surface_of(obj):
        # GameSprite exposes `.image` (a property); the old gui.Object set it as an
        # attribute; engine TextObject/GameObjects keep their surface on a
        # SpriteRenderer2D component. Support all three so the camera can draw any.
        image = getattr(obj, "image", None)

        if image is not None:
            return image

        renderer = (
            obj.get_component(SpriteRenderer2D)
            if hasattr(obj, "get_component")
            else None
        )

        return renderer.image if renderer else None
