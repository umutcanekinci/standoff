"""Entity is the shared base for Player/Mob -- exercised directly here with
a real AssetManager (real image loading, cheap) and a bare Rect for
hit_rect/world, matching the FakeWorld-with-just-a-.rect style test_bullet.py
already established for its own collision partners."""

import pygame
from pygame.math import Vector2 as Vec

from gameplay.entity import Entity
from util.constants import Red, White, Green, Yellow


class FakeWorld:
    def __init__(self):
        self.walls = []
        self.wall_grid = None


def make_entity(assets, *, hp=100, max_hp=100):
    entity = Entity(
        1, "Bob", White, (100, 100), 1.0,
        assets.image_path("char_zombie_idle"), hp, max_hp,
    )
    entity.world = FakeWorld()
    entity.hit_rect = pygame.Rect(0, 0, 30, 30)
    entity.hit_rect.center = entity.rect.center
    return entity


def test_construction_sets_name_and_hp(assets):
    entity = make_entity(assets, hp=80, max_hp=100)

    assert entity.name == "Bob"
    assert entity.hp == 80
    assert entity.max_hp == 100
    assert entity.name_text.text == "Bob"


def test_set_hp_to_zero_or_below_kills_the_entity(assets):
    entity = make_entity(assets)

    entity.set_hp(0)

    assert entity.alive is False


def test_lose_hp_decrements_and_can_kill(assets):
    entity = make_entity(assets, hp=10, max_hp=100)

    entity.lose_hp(4)
    assert entity.hp == 6
    assert entity.alive is True

    entity.lose_hp(100)
    assert entity.hp == -94
    assert entity.alive is False


def test_health_bar_color_tiers(assets):
    healthy = make_entity(assets, hp=100, max_hp=100)
    assert healthy.health_bar.image.get_at((5, 5))[:3] == Green

    hurt = make_entity(assets, hp=50, max_hp=100)  # > 35%, <= 70%
    assert hurt.health_bar.image.get_at((5, 5))[:3] == Yellow

    critical = make_entity(assets, hp=10, max_hp=100)  # <= 35%
    assert critical.health_bar.image.get_at((5, 5))[:3] == Red


def test_move_updates_hit_rect_and_position_without_a_wall_grid(assets):
    entity = make_entity(assets)
    start = Vec(entity.hit_rect.center)

    entity.move(Vec(10, 5))

    assert entity.hit_rect.centerx == start.x + 10
    assert entity.hit_rect.centery == start.y + 5
    assert entity.position == Vec(entity.hit_rect.center)


def test_move_stops_against_a_wall(assets):
    entity = make_entity(assets)
    entity.velocity = Vec()  # collide() zeroes this on a hit -- only Player/Mob normally set it
    wall = pygame.Rect(0, 0, 20, 200)
    wall.midleft = (entity.hit_rect.right + 5, entity.hit_rect.centery)
    entity.world.walls = [type("W", (), {"rect": wall})()]

    # A small step that actually lands inside the thin wall -- collision here
    # is a discrete post-move overlap check, not swept, so a big enough delta
    # would tunnel straight through a 20px-wide wall instead of hitting it.
    entity.move(Vec(10, 0))

    assert entity.hit_rect.right == wall.left
    assert entity.velocity == Vec(0, 0)


def test_update_position_anchors_name_text_and_health_bar_above_the_hit_rect(assets):
    entity = make_entity(assets, hp=100, max_hp=100)

    entity.update_position((300, 300))

    assert entity.hit_rect.center == (300, 300)
    top = entity.hit_rect.top  # 285 -- hit_rect is 30px tall, centered at 300
    assert entity.health_bar.rect.center == (300, top - 20)
    # Full health -- the name sits closer to the sprite (no health bar gap needed).
    assert entity.name_text.rect.center == (300, top - 30)

    entity.set_hp(50)  # damaged -- name shifts up to make room for the visible bar
    entity.update_position((300, 300))
    assert entity.name_text.rect.center == (300, top - 40)


def test_draw_health_bar_only_when_damaged(assets):
    entity = make_entity(assets, hp=100, max_hp=100)
    calls = []
    camera = type("Cam", (), {"draw": lambda self, surface, obj: calls.append(obj)})()

    entity.draw_health_bar(None, camera)
    assert calls == []

    entity.set_hp(50)
    entity.draw_health_bar(None, camera)
    assert calls == [entity.health_bar]
