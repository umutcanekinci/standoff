import pygame

from gameplay.muzzle_flash import MuzzleFlash
from util.constants import FLASH_DURATOION


class FakeWorld:
    def __init__(self, assets):
        self.gun_flashes = [assets.image_path("muzzle_1")]
        self.effects = []


def test_construction_registers_itself_with_the_worlds_effects(assets):
    world = FakeWorld(assets)

    flash = MuzzleFlash(world, (50, 50), angle=0)

    assert world.effects == [flash]
    assert flash.alive is True


def test_update_kills_itself_once_the_flash_duration_elapses(assets, monkeypatch):
    world = FakeWorld(assets)
    flash = MuzzleFlash(world, (50, 50), angle=0)
    now = flash.spawn_time

    monkeypatch.setattr(pygame.time, "get_ticks", lambda: now + FLASH_DURATOION - 1)
    flash.update()
    assert flash.alive is True

    monkeypatch.setattr(pygame.time, "get_ticks", lambda: now + FLASH_DURATOION + 1)
    flash.update()
    assert flash.alive is False
