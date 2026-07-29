"""Unit tests for gameplay.camera.Camera: pygamine.Camera plus follow() and
a batch draw() -- this used to be a from-scratch class duplicating the base
Camera's coordinate math; these tests pin down the behavior that migration
had to preserve exactly (follow-and-clamp, apply(), single-object and
list-of-objects draw with viewport culling).
"""
from __future__ import annotations

import pygame
import pytest

from gameplay.camera import Camera


class _FakeMap:
    def __init__(self, width: int, height: int) -> None:
        self.rect = pygame.Rect(0, 0, width, height)


class _FakeDrawable:
    def __init__(self, rect: pygame.Rect, image: pygame.Surface | None) -> None:
        self.rect = rect
        self.image = image


@pytest.fixture
def big_map() -> _FakeMap:
    # Bigger than the 800x600 viewport on both axes, so follow() has room
    # to actually pan instead of being clamped flush against an edge.
    return _FakeMap(2000, 1500)


def test_construction_sets_viewport_and_map_backreference(big_map):
    camera = Camera((800, 600), big_map)
    assert camera.rect.size == (800, 600)
    assert camera.rect.topleft == (0, 0)
    assert big_map.camera is camera


def test_follow_centers_the_target_in_the_viewport(big_map):
    camera = Camera((800, 600), big_map)
    target = pygame.Rect(0, 0, 10, 10)
    target.center = (500, 500)

    camera.follow(target)

    screen_center = camera.apply(target).center
    assert screen_center == (400, 300)  # dead center of an 800x600 viewport


def test_follow_clamps_at_the_top_left_map_edge(big_map):
    camera = Camera((800, 600), big_map)
    target = pygame.Rect(0, 0, 10, 10)
    target.center = (5, 5)  # near the map's top-left corner

    camera.follow(target)

    # Clamped: the viewport never scrolls past (0, 0) of the map.
    assert camera._offset.x == 0
    assert camera._offset.y == 0


def test_follow_clamps_at_the_bottom_right_map_edge(big_map):
    camera = Camera((800, 600), big_map)
    target = pygame.Rect(0, 0, 10, 10)
    target.center = (1995, 1495)  # near the map's bottom-right corner

    camera.follow(target)

    assert camera._offset.x == 800 - 2000  # -1200
    assert camera._offset.y == 600 - 1500  # -900


def test_apply_offsets_a_rect_by_the_current_pan(big_map):
    camera = Camera((800, 600), big_map)
    camera._offset.update(-50, -20)

    result = camera.apply(pygame.Rect(100, 100, 32, 32))

    assert result.topleft == (50, 80)
    assert result.size == (32, 32)


def test_apply_is_identity_before_any_follow_call(big_map):
    """Regression check for gameplay/controls.py's aim_angle(), which calls
    camera.apply(rect) expecting a plain rect-like result with .center --
    with no pan applied yet (offset starts at (0, 0)), apply() must be a
    no-op, matching test_controls.py's `_Camera().apply(r) -> r` fake."""
    camera = Camera((800, 600), big_map)
    rect = pygame.Rect(0, 0, 10, 10)
    rect.center = (100, 100)

    assert camera.apply(rect).center == rect.center


def test_draw_accepts_a_single_object_not_just_an_iterable(big_map):
    """entity.py calls camera.draw(surface, self.name_text) with one object,
    not a list -- must not raise."""
    camera = Camera((800, 600), big_map)
    surface = pygame.Surface((800, 600))
    obj = _FakeDrawable(pygame.Rect(10, 10, 5, 5), pygame.Surface((5, 5)))

    camera.draw(surface, obj)  # must not raise


def test_draw_blits_every_object_in_view():
    camera = Camera((100, 100), _FakeMap(100, 100))
    surface = pygame.Surface((100, 100))
    surface.fill((0, 0, 0))
    image = pygame.Surface((10, 10))
    image.fill((255, 0, 0))

    objects = [_FakeDrawable(pygame.Rect(x, 10, 10, 10), image) for x in (0, 20, 40)]
    camera.draw(surface, objects)

    for x in (0, 20, 40):
        assert surface.get_at((x + 5, 15)) == (255, 0, 0, 255)


def test_draw_culls_objects_outside_the_viewport():
    camera = Camera((100, 100), _FakeMap(1000, 1000))
    surface = pygame.Surface((100, 100))
    surface.fill((0, 0, 0))
    image = pygame.Surface((10, 10))
    image.fill((255, 0, 0))

    far_away = _FakeDrawable(pygame.Rect(5000, 5000, 10, 10), image)
    camera.draw(surface, [far_away])  # must not raise, and must not blit anything visible

    assert surface.get_at((50, 50)) == (0, 0, 0, 255)


def test_draw_skips_objects_with_no_image():
    camera = Camera((100, 100), _FakeMap(100, 100))
    surface = pygame.Surface((100, 100))
    obj = _FakeDrawable(pygame.Rect(10, 10, 5, 5), None)

    camera.draw(surface, [obj])  # must not raise despite image being None
