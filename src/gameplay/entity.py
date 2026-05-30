import pygame
from typing import Any, cast

from util.constants import *
from gameplay.game_sprite import GameSprite
from gameplay.collision import collide
from pygame_core.image import load_image
from pygame_core.ui_widgets.text_object import TextObject
from pygame_core.ecs.components.transform import Transform

_NAME_FONT = None


def _name_font():
    # Lazy: this module is imported before pygame.init() runs in Game.__init__.
    global _NAME_FONT
    if _NAME_FONT is None:
        _NAME_FONT = pygame.font.Font(None, 25)
    return _NAME_FONT


class Entity(GameSprite):

    game: Any              # set by Player/Mob subclasses
    hit_rect: pygame.Rect  # set by Player/Mob subclasses

    def __init__(self, id, name, name_color, position, size, image_path, hp, max_hp):
        super().__init__(position=position, layer=ENTITY_LAYER)
        self.id = id

        self.set_name(name, name_color)
        self.set_max_hp(max_hp)
        self.set_hp(hp)
        self.set_entity_image(image_path, position, size)

    def set_entity_image(self, image_path, position, size):
        native = cast(pygame.Surface, load_image(image_path))
        w, h = native.get_size()
        self.set_image(pygame.transform.scale(native, (int(w * size), int(h * size))))
        self.set_position(position)

    def set_name(self, value: str, color):
        self.name = value
        self.name_text = TextObject(Transform((0, 0), (0, 0)), (0, 0), self.name, _name_font(), color)

    def __render_health_bar(self):
        if not hasattr(self, "health_bar"):
            self.health_bar = GameSprite((0, 0), size=HEALTH_BAR_SIZE, layer=GUI_LAYER)

        w, h = HEALTH_BAR_SIZE
        surface = pygame.Surface(HEALTH_BAR_SIZE, pygame.SRCALPHA)
        surface.fill(White)

        if self.hp > self.max_hp * 70 * .01:
            color = Green
        elif self.hp > self.max_hp * 35 * .01:
            color = Yellow
        else:
            color = Red

        pygame.draw.rect(surface, color, pygame.Rect(0, 0, w * self.hp / self.max_hp, h), 0)
        pygame.draw.rect(surface, color, pygame.Rect((0, 0), HEALTH_BAR_SIZE), 2)
        self.health_bar.set_image(surface)

    def set_max_hp(self, value):
        self.max_hp = value
        if hasattr(self, "hp"):
            self.__render_health_bar()

    def set_hp(self, value):
        self.hp = value
        if self.hp <= 0:
            self.kill()
        if hasattr(self, "max_hp"):
            self.__render_health_bar()

    def lose_hp(self, value):
        self.set_hp(self.hp - value)

    # rotate() is inherited from GameSprite.

    def move(self, delta):
        self.hit_rect.centerx += delta.x
        collide(self, 'x', self.game.walls)
        self.hit_rect.centery += delta.y
        collide(self, 'y', self.game.walls)
        self.update_position(self.hit_rect.center)

    def update_position(self, position):
        self.set_position(position)
        self.hit_rect.center = position

        if self.hp != self.max_hp:
            self.name_text.rect.center = (self.hit_rect.centerx, self.hit_rect.top - 40)
        else:
            self.name_text.rect.center = (self.hit_rect.centerx, self.hit_rect.top - 30)

        self.health_bar.rect.center = (self.hit_rect.centerx, self.hit_rect.top - 20)

    def draw_name(self, surface, camera):
        camera.draw(surface, self.name_text)

    def draw_rects(self, surface, camera):
        pygame.draw.rect(surface, Red, camera.apply(self.rect), 2)
        pygame.draw.rect(surface, Blue, camera.apply(self.hit_rect), 2)

    def draw_health_bar(self, surface, camera):
        if self.hp != self.max_hp:
            camera.draw(surface, self.health_bar)
