import pygame
import pytest
from pygame.math import Vector2 as Vec

from gameplay.player import Player, Players
from util.constants import (
    GUN_SPREAD, KICKBACK, KNOCKBACK_DECAY, PLAYER_FRICTION,
    REMOTE_SNAP_DISTANCE, SHOOT_RATE,
)


class FakeWorld:
    def __init__(self, assets):
        self.assets = assets
        self.map = type("Map", (), {"spawn_points": [(100, 100), (200, 200)]})()
        self.camera = None
        self.delta_time = 1 / 60
        self.walls = []
        self.wall_grid = None
        self.bullets = []
        self.effects = []
        self.gun_flashes = [assets.image_path("muzzle_1")]


def make_player(assets, *, position=(500, 500)):
    world = FakeWorld(assets)
    player = Player(1, "Alice", (255, 255, 255), "survivor", position, 1.0, world)
    return player, world


# ── construction ─────────────────────────────────────────────────────────────

def test_construction_sets_up_hit_rect_and_local_flag(assets):
    player, world = make_player(assets)

    assert player.hit_rect.center == player.rect.center
    assert player.is_local is False
    assert player.target_position == Vec(500, 500)
    assert player.alive is True
    assert player.weight > 0


# ── alive / appearance ───────────────────────────────────────────────────────

def test_set_alive_false_swaps_to_a_greyscale_image_and_back(assets):
    player, world = make_player(assets)
    color_image = player.image

    player.set_alive(False)
    assert player.alive is False
    grey_image = player.image
    assert grey_image is not color_image

    player.set_alive(True)
    assert player.alive is True
    assert player.image is color_image


def test_set_alive_same_value_is_a_no_op(assets):
    player, world = make_player(assets)
    image_before = player.image

    player.set_alive(True)  # already alive

    assert player.image is image_before


# ── aim / input ──────────────────────────────────────────────────────────────

def test_aim_reads_the_angle_from_controls_when_present(assets):
    player, world = make_player(assets)
    player.controls = type("C", (), {"aim_angle": lambda self, p, cam: 42.0})()

    player.aim()

    assert player.angle == 42.0


def test_aim_leaves_angle_unchanged_without_controls(assets):
    player, world = make_player(assets)
    player.controls = None
    player.angle = 7.0

    player.aim()

    assert player.angle == 7.0


def test_update_force_rotation_reads_from_controls(assets):
    player, world = make_player(assets)
    player.controls = type("C", (), {"movement": lambda self: Vec(1, 0)})()

    player._update_force_rotation()

    assert player.force_rotation == Vec(1, 0)


# ── friction / knockback ─────────────────────────────────────────────────────

def test_apply_friction_only_damps_undriven_axes(assets):
    player, world = make_player(assets)
    world.delta_time = 1.0
    player.velocity = Vec(10, 10)
    player.force_rotation = Vec(1, 0)  # driving x -- y is undriven

    player._apply_friction()

    assert player.velocity.x == 10  # untouched
    assert player.velocity.y == pytest.approx(10 * PLAYER_FRICTION)


def test_decay_knockback_adds_to_delta_and_decays():
    from gameplay.player import Player as P  # only exercising the pure method
    player = object.__new__(P)
    player.delta = Vec(0, 0)
    player.knockback = Vec(10, 0)

    player._decay_knockback()

    assert player.delta == Vec(10, 0)
    assert player.knockback == Vec(10 * KNOCKBACK_DECAY, 0)


def test_decay_knockback_snaps_to_zero_once_small():
    from gameplay.player import Player as P
    player = object.__new__(P)
    player.delta = Vec(0, 0)
    player.knockback = Vec(0.05, 0)

    player._decay_knockback()

    assert player.knockback == Vec(0, 0)


def test_apply_knockback_zero_direction_is_a_no_op(assets):
    player, world = make_player(assets)
    player.knockback = Vec(5, 5)

    player.apply_knockback(Vec(0, 0), 100)

    assert player.knockback == Vec(5, 5)


def test_apply_knockback_scales_with_the_decay_series(assets):
    player, world = make_player(assets)

    player.apply_knockback(Vec(1, 0), 100)

    assert player.knockback.x == pytest.approx(100 * (1 - KNOCKBACK_DECAY))


# ── movement ─────────────────────────────────────────────────────────────────

def test_update_movement_caps_speed_and_computes_delta(assets):
    player, world = make_player(assets)
    world.delta_time = 1.0
    player.controls = type("C", (), {"movement": lambda self: Vec(1, 0)})()

    player.update_movement()

    assert player.velocity.length() <= player.max_speed + 1e-6
    assert player.delta == player.velocity * world.delta_time


def test_update_movement_zeroes_out_tiny_residual_velocity(assets):
    player, world = make_player(assets)
    player.velocity = Vec(0.005, 0.005)
    player.controls = None  # no drive, just friction bringing it toward zero

    player.update_movement()

    assert player.velocity.x == 0
    assert player.velocity.y == 0


# ── shooting ─────────────────────────────────────────────────────────────────

def test_shoot_spawns_a_bullet_and_muzzle_flash_and_applies_kickback(assets, monkeypatch):
    player, world = make_player(assets)
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 100_000)
    monkeypatch.setattr("gameplay.player.uniform", lambda a, b: 0.0)  # no random spread

    player.shoot()

    assert len(world.bullets) == 1
    assert len(world.effects) == 1
    assert player.last_shoot_time == 100_000
    assert player.velocity.length() == pytest.approx(KICKBACK)


def test_shoot_respects_its_cooldown(assets, monkeypatch):
    player, world = make_player(assets)
    monkeypatch.setattr("gameplay.player.uniform", lambda a, b: 0.0)

    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 1000)
    player.shoot()
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 1000 + SHOOT_RATE - 1)
    player.shoot()

    assert len(world.bullets) == 1  # the second shot was too soon


# ── update / follow remote ───────────────────────────────────────────────────

def test_update_moves_locally_when_is_local(assets):
    player, world = make_player(assets)
    player.is_local = True
    player.delta = Vec(10, 0)
    player.velocity = Vec()  # collide() may zero this on a wall hit
    start_x = player.hit_rect.centerx

    player.update()

    assert player.hit_rect.centerx == start_x + 10


def test_update_follows_remote_position_when_not_local(assets):
    player, world = make_player(assets)
    player.is_local = False
    player.target_position = Vec(player.position.x + 5, player.position.y)

    player.update()

    assert player.position.x > (player.target_position.x - 5)


def test_follow_remote_snaps_on_a_large_gap(assets):
    player, world = make_player(assets)
    player.target_position = Vec(player.position.x + REMOTE_SNAP_DISTANCE * 10, player.position.y)

    player._follow_remote()

    assert player.position == player.target_position


# ── Players container ────────────────────────────────────────────────────────

def test_players_add_player_uses_the_spawn_point_for_its_base(assets):
    world = FakeWorld(assets)
    players = Players(world)
    info = type("Info", (), {
        "id": 3, "name": "Bob", "character_name": "survivor",
        "base_number": 1, "size": 1.0,
    })()

    player = players.add_player(info, name_color=(255, 255, 255))

    assert player in players
    assert player.position == Vec(200, 200)  # spawn_points[1]
    assert players.get_player_with_id(3) is player
    assert players.get_player_with_id(999) is None
