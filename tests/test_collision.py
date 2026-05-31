"""Unit tests for gameplay.collision.collide.

Pins the wall-resolution behaviour: push to the correct side (decided from
hit_rect, never the sprite rect), zero the blocked velocity component, and clear
every overlapping wall.
"""

import pygame

from gameplay.collision import collide


class _Body:
    def __init__(self, center, size=(30, 30)):
        self.hit_rect = pygame.Rect(0, 0, *size)
        self.hit_rect.center = center
        self.velocity = pygame.math.Vector2(0, 0)
        # Deliberately huge/misleading sprite rect: the old code read this for the
        # side decision and would snap to the wrong side. collide must ignore it.
        self.rect = pygame.Rect(0, 0, 200, 200)
        self.rect.center = center


class _Wall:
    def __init__(self, rect):
        self.rect = rect


def test_blocked_moving_right_snaps_to_left_face():
    obj = _Body(center=(95, 120))  # hit_rect 80..110 overlaps wall 100..140
    wall = _Wall(pygame.Rect(100, 100, 40, 40))

    collide(obj, "x", [wall])

    assert obj.hit_rect.right == wall.rect.left
    assert obj.velocity.x == 0


def test_blocked_moving_left_snaps_to_right_face():
    # Sprite rect (200 wide, centre 145) would mislead the old test into pushing
    # the wrong way; the fix uses hit_rect.centerx (145 > wall centre 120).
    obj = _Body(center=(145, 120))  # hit_rect 130..160 overlaps wall 100..140
    wall = _Wall(pygame.Rect(100, 100, 40, 40))

    collide(obj, "x", [wall])

    assert obj.hit_rect.left == wall.rect.right
    assert obj.velocity.x == 0


def test_vertical_resolution():
    obj = _Body(center=(120, 95))
    wall = _Wall(pygame.Rect(100, 100, 40, 40))

    collide(obj, "y", [wall])

    assert obj.hit_rect.bottom == wall.rect.top
    assert obj.velocity.y == 0


def test_no_overlap_is_a_noop():
    obj = _Body(center=(0, 0))
    before = obj.hit_rect.copy()
    collide(obj, "x", [_Wall(pygame.Rect(500, 500, 40, 40))])
    assert obj.hit_rect == before


def test_corner_clears_both_walls():
    obj = _Body(center=(95, 95))
    wall = _Wall(pygame.Rect(100, 100, 40, 40))

    collide(obj, "x", [wall])
    collide(obj, "y", [wall])

    assert not obj.hit_rect.colliderect(wall.rect)
