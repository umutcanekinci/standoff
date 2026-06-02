"""Unit tests for gameplay.Bullet.update collision dispatch.

Pins what a bullet does on its first stepped frame: stop on a wall, report a mob
hit to the world (which owns mob HP), damage a player, ignore its own shooter,
and otherwise keep flying. Driven with fake walls/mobs/players carrying just a
.rect, so no scene or display is needed.
"""

import pygame
from pygame.math import Vector2 as Vec

from gameplay.bullet import Bullet
from util.constants import BULLET_DAMAGE


def _rect_at(center, size=(10, 10)):
    rect = pygame.Rect(0, 0, *size)
    rect.center = center
    return rect


class _Rectish:
    """A wall/mob with only the .rect the bullet collides against."""

    def __init__(self, center):
        self.rect = _rect_at(center)


class _Player:
    def __init__(self, center):
        self.rect = _rect_at(center)
        self.velocity = Vec(3, 4)
        self.hp_losses = []

    def lose_hp(self, damage):
        self.hp_losses.append(damage)


class _World:
    def __init__(self, delta_time=0.0):
        self.bullets = []
        self.walls = []
        self.mobs = []
        self.players = []
        self.delta_time = delta_time
        self.hits = []

    def hit_mob(self, mob, damage):
        self.hits.append((mob, damage))


class _Shooter:
    """The source sprite: the bullet reads source.world and ignores hits on it."""

    def __init__(self, world):
        self.world = world
        self.rect = _rect_at((0, 0))


def _bullet(world, position=(0, 0), angle=0.0):
    # dt defaults to 0 so move() leaves the bullet on its spawn point and the
    # collision geometry is deterministic.
    return Bullet(_Shooter(world), position, angle)


def test_bullet_registers_itself_with_the_world():
    world = _World()
    bullet = _bullet(world)
    assert world.bullets == [bullet]
    assert bullet.alive is True


def test_bullet_stops_on_a_wall():
    world = _World()
    world.walls.append(_Rectish((0, 0)))  # overlaps the spawn point
    bullet = _bullet(world)

    bullet.update()

    assert bullet.alive is False
    assert world.hits == []  # a wall is not a mob hit


def test_bullet_reports_mob_hit_to_world_then_dies():
    world = _World()
    mob = _Rectish((0, 0))
    world.mobs.append(mob)
    bullet = _bullet(world)

    bullet.update()

    assert world.hits == [(mob, BULLET_DAMAGE)]
    assert bullet.alive is False


def test_bullet_ignores_its_own_shooter():
    world = _World()
    bullet = _bullet(world)
    world.mobs.append(bullet.source)  # the source overlaps the spawn point

    bullet.update()

    assert world.hits == []
    assert bullet.alive is True


def test_bullet_damages_a_player_and_halts_them():
    world = _World()
    player = _Player((0, 0))
    world.players.append(player)
    bullet = _bullet(world)

    bullet.update()

    assert player.hp_losses == [BULLET_DAMAGE]
    assert player.velocity == Vec(0, 0)
    assert bullet.alive is False


def test_bullet_flies_on_when_it_hits_nothing():
    world = _World(delta_time=1.0)
    bullet = _bullet(world, angle=0.0)  # velocity points along +x
    start_x = bullet.position.x

    bullet.update()

    assert bullet.alive is True
    assert bullet.position.x > start_x
    assert bullet.position.y == 0
