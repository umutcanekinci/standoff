import pygame
from pygame.math import Vector2 as Vec

from gameplay.mob import Mob, Mobs
from util.constants import AVOID_RADIUS, MOB_KNOCKBACK, REMOTE_SNAP_DISTANCE


class FakeGrid:
    def __init__(self, mobs=None):
        self._mobs = mobs or []

    def query_radius(self, center, radius):
        return self._mobs


class FakeWorld:
    def __init__(self, assets):
        self.assets = assets
        self.map = None
        self.camera = None
        self.players = []
        self.mob_grid = FakeGrid()
        self.delta_time = 1 / 60
        self.wall_grid = None
        self.walls = []


class FakePlayer:
    def __init__(self, center, alive=True):
        self.rect = pygame.Rect(0, 0, 20, 20)
        self.rect.center = center
        self.alive = alive
        self.hp_losses = []
        self.knockbacks = []

    def lose_hp(self, amount):
        self.hp_losses.append(amount)

    def apply_knockback(self, direction, distance):
        self.knockbacks.append((direction, distance))


def make_mob(assets, world, entity_id=1, position=(500, 500)):
    return Mob(entity_id, "Mob 1", position, 1.0, (0, 0), "zombie", world)


# ── targeting ────────────────────────────────────────────────────────────────

def test_check_range_falls_back_to_the_base_with_no_players(assets):
    world = FakeWorld(assets)
    mob = make_mob(assets, world)

    mob.check_range()

    assert mob.target == mob.target_base


def test_check_range_targets_the_nearest_player_within_range(assets):
    world = FakeWorld(assets)
    mob = make_mob(assets, world, position=(0, 0))
    close = FakePlayer((10, 0))
    far = FakePlayer((10_000, 0))
    world.players = [far, close]

    mob.check_range()

    assert mob.target == close.rect.center


def test_check_range_ignores_a_player_outside_the_aggro_radius(assets):
    world = FakeWorld(assets)
    mob = make_mob(assets, world, position=(0, 0))
    world.players = [FakePlayer((mob.range * 10, 0))]

    mob.check_range()

    assert mob.target == mob.target_base


def test_rotate_to_target_faces_the_current_target(assets):
    world = FakeWorld(assets)
    mob = make_mob(assets, world, position=(0, 0))
    mob.target = (100, 0)

    mob.rotate_to_target()

    assert mob.angle == 0
    assert mob.is_rotated is True


# ── movement ─────────────────────────────────────────────────────────────────

def test_avoid_mobs_pushes_away_from_a_nearby_mob(assets):
    world = FakeWorld(assets)
    mob = make_mob(assets, world, position=(0, 0))
    other = make_mob(assets, world, entity_id=2, position=(10, 0))
    world.mob_grid = FakeGrid([mob, other])  # includes self, must be skipped

    mob.avoid_mobs()

    # `other` sits to the right -- push direction is away from it, i.e. -x.
    assert mob.acceleration.x < 0


def test_avoid_mobs_ignores_mobs_outside_the_avoid_radius(assets):
    world = FakeWorld(assets)
    mob = make_mob(assets, world, position=(0, 0))
    far = make_mob(assets, world, entity_id=2, position=(AVOID_RADIUS * 10, 0))
    world.mob_grid = FakeGrid([mob, far])

    mob.avoid_mobs()

    assert mob.acceleration == Vec(0, 0)


def test_update_movement_advances_velocity_and_delta(assets):
    world = FakeWorld(assets)
    world.delta_time = 1.0
    mob = make_mob(assets, world, position=(0, 0))
    mob.angle = 0  # accelerate along +x

    mob.update_movement()

    assert mob.velocity.length() > 0
    assert mob.delta == mob.velocity * world.delta_time


def test_follow_remote_snaps_on_a_large_gap(assets):
    world = FakeWorld(assets)
    mob = make_mob(assets, world, position=(0, 0))
    mob.target_position = Vec(REMOTE_SNAP_DISTANCE * 10, 0)

    mob._follow_remote()

    assert mob.position == mob.target_position


def test_follow_remote_eases_toward_a_small_gap(assets):
    world = FakeWorld(assets)
    world.delta_time = 1 / 60
    mob = make_mob(assets, world, position=(0, 0))
    mob.target_position = Vec(10, 0)

    mob._follow_remote()

    assert 0 < mob.position.x < 10


# ── attack ───────────────────────────────────────────────────────────────────

def test_try_attack_damages_an_overlapping_alive_player(assets, monkeypatch):
    world = FakeWorld(assets)
    mob = make_mob(assets, world, position=(0, 0))
    player = FakePlayer(mob.hit_rect.center)  # fully overlapping
    world.players = [player]
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 100_000)

    mob._try_attack()

    assert player.hp_losses == [mob.damage]
    assert len(player.knockbacks) == 1
    assert player.knockbacks[0][1] == MOB_KNOCKBACK


def test_try_attack_ignores_a_dead_player(assets, monkeypatch):
    world = FakeWorld(assets)
    mob = make_mob(assets, world, position=(0, 0))
    player = FakePlayer(mob.hit_rect.center, alive=False)
    world.players = [player]
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 100_000)

    mob._try_attack()

    assert player.hp_losses == []


def test_try_attack_respects_the_one_second_cooldown(assets, monkeypatch):
    world = FakeWorld(assets)
    mob = make_mob(assets, world, position=(0, 0))
    player = FakePlayer(mob.hit_rect.center)
    world.players = [player]

    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 1000)
    mob._try_attack()
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 1500)  # < 1000ms later
    mob._try_attack()

    assert player.hp_losses == [mob.damage]  # only the first landed


# ── update dispatch ──────────────────────────────────────────────────────────

def test_update_runs_local_ai_when_not_networked(assets, monkeypatch):
    world = FakeWorld(assets)
    mob = make_mob(assets, world, position=(0, 0))
    mob.is_network = False
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 0)

    mob.update()  # must not raise, exercises check_range/rotate/update_movement/_try_attack


def test_update_follows_the_network_position_when_networked(assets, monkeypatch):
    world = FakeWorld(assets)
    mob = make_mob(assets, world, position=(0, 0))
    mob.is_network = True
    mob.target_position = Vec(50, 0)
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 0)

    mob.update()

    assert mob.position.x > 0  # eased toward target_position, not local AI


# ── Mobs container ───────────────────────────────────────────────────────────

def test_mobs_add_mob_and_lookup_by_id(assets):
    world = FakeWorld(assets)
    mobs = Mobs(world)
    info = type("Info", (), {"id": 7, "position": (0, 0), "size": 1.0, "target_base": (0, 0)})()

    mob = mobs.add_mob(info)

    assert mob in mobs
    assert mobs.get_mob_from_id(7) is mob
    assert mobs.get_mob_from_id(999) is None
