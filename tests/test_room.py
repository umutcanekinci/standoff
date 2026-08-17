import pygame
import pytest

from net.player_info import PlayerInfo
from net.room import Room
from util.constants import SPAWN_RATE

BASE_POINTS = {1: (100, 100), 2: (200, 200), 3: (300, 300), 4: (400, 400)}


def make_room(**overrides):
    kwargs = dict(room_id="r1", map_name="level1", base_points=dict(BASE_POINTS))
    kwargs.update(overrides)
    return Room(**kwargs)


def make_player(player_id=1):
    return PlayerInfo(player_id, name=f"P{player_id}")


# ── roster ───────────────────────────────────────────────────────────────────

def test_add_player_assigns_the_first_free_base_slot():
    room = make_room()
    p1, p2 = make_player(1), make_player(2)

    room.add_player(p1, is_ruler=True)
    room.add_player(p2, is_ruler=False)

    assert p1.base_number == 1
    assert p2.base_number == 2
    assert p1.base_point == BASE_POINTS[1]
    assert p1.position == BASE_POINTS[1]
    assert p1.is_ruler is True
    assert p2.is_ruler is False
    assert p2.is_ready is False


def test_add_player_reuses_a_slot_freed_by_a_departed_player():
    room = make_room()
    p1, p2, p3 = make_player(1), make_player(2), make_player(3)
    room.add_player(p1, is_ruler=True)
    room.add_player(p2, is_ruler=False)

    room.remove_player(p1)
    room.add_player(p3, is_ruler=False)

    assert p3.base_number == 1  # slot 1 was freed, not slot 3
    assert p1.room is None
    assert p1 not in room


# ── mob spawner ──────────────────────────────────────────────────────────────

def test_handle_spawner_does_nothing_before_the_spawn_interval_elapses(monkeypatch):
    room = make_room()
    room.add_player(make_player(1), is_ruler=False)
    room.last_spawn = 1000
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 1000 + SPAWN_RATE - 1)
    spawned = []

    room.handle_spawner(lambda room_, mob: spawned.append(mob))

    assert spawned == []
    assert room.last_spawn == 1000  # unchanged -- gate never opened


def test_handle_spawner_spawns_one_mob_per_alive_player_online(monkeypatch):
    room = make_room(is_online=True)
    alive = make_player(1)
    dead = make_player(2)
    dead.alive = False
    room.add_player(alive, is_ruler=False)
    room.add_player(dead, is_ruler=False)
    room.last_spawn = 0
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: SPAWN_RATE)
    spawned = []

    room.handle_spawner(lambda room_, mob: spawned.append((room_, mob)))

    assert len(spawned) == 1  # only the alive player attracted a mob
    got_room, mob_info = spawned[0]
    assert got_room is room
    assert mob_info.target_base == alive.base_point
    assert room.last_spawn == SPAWN_RATE


def test_handle_spawner_offline_calls_spawn_func_with_just_the_mob(monkeypatch):
    room = make_room(is_online=False)
    room.add_player(make_player(1), is_ruler=False)
    room.last_spawn = 0
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: SPAWN_RATE)
    spawned = []

    room.handle_spawner(lambda mob: spawned.append(mob))

    assert len(spawned) == 1


def test_update_delegates_to_handle_spawner(monkeypatch):
    room = make_room()
    room.add_player(make_player(1), is_ruler=False)
    room.last_spawn = 0
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: SPAWN_RATE)
    calls = []

    room.update(lambda room_, mob: calls.append(mob))

    assert len(calls) == 1


# ── wire form ────────────────────────────────────────────────────────────────

def test_to_dict_from_dict_round_trips_roster_and_base_points():
    room = make_room()
    room.add_player(make_player(1), is_ruler=True)
    room.add_player(make_player(2), is_ruler=False)

    data = room.to_dict()
    # Simulate the wire: players are decoded independently first (object_hook
    # order), then nested back into the room dict, matching how TypedJSONCodec
    # actually reconstructs a Room from real JSON.
    data["players"] = [PlayerInfo.from_dict(p) for p in data["players"]]
    restored = Room.from_dict(data)

    assert restored.id == room.id
    assert restored.map_name == room.map_name
    assert restored.base_points == room.base_points
    assert len(restored) == 2
    assert restored[0].room is restored


def test_from_dict_rejects_a_malformed_base_points_entry():
    with pytest.raises(ValueError):
        Room.from_dict({"id": "r1", "map_name": "level1", "base_points": [["not-a-pair"]]})


def test_from_dict_rejects_players_that_are_not_already_decoded():
    data = {
        "id": "r1", "map_name": "level1", "base_points": [],
        "players": [{"__type__": "PlayerInfo", "id": 1}],  # never ran through object_hook
    }

    with pytest.raises(ValueError):
        Room.from_dict(data)
