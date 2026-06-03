"""Unit tests for net.game_server.GameServer.

GameServer is socket-free, so we drive it directly through the same callbacks
the transport would call (_on_connect / _on_message / _on_disconnect) and assert
on what it sends back via a FakeConnection. Fast, deterministic, no threads.
"""

from net.game_server import GameServer
from net.player_info import MobInfo
from util.constants import RANGE_RADIUS
from _util import FakeConnection


def _connect(gs: GameServer) -> FakeConnection:
    """Register a fresh fake client and return its connection."""
    conn = FakeConnection()
    gs._on_connect(conn)
    return conn


def _host_in_room(gs: GameServer, base_points=None) -> FakeConnection:
    """Connect a client and have it create (and join, as ruler) a room."""
    conn = _connect(gs)
    base_points = base_points or {0: (0, 0), 1: (10, 10)}
    gs._on_message(conn, {"command": "!CREATE_ROOM", "value": ("map", base_points)})
    return conn


def test_connect_registers_player_and_announces_count():
    gs = GameServer()
    conn = _connect(gs)

    assert len(gs.players) == 1
    # New client is told the player count and given an initial room update.
    assert "!SET_PLAYER_COUNT" in conn.commands()
    assert "!UPDATE_ROOM" in conn.commands()


def test_set_player_updates_name():
    gs = GameServer()
    conn = _connect(gs)

    gs._on_message(conn, {"command": "!SET_PLAYER", "value": ["Alice", "knight"]})

    player = gs._players_by_connection[conn]
    assert player.name == "Alice"
    assert player.character_name == "knight"


def test_create_then_join_room_succeeds():
    gs = GameServer()
    host = _connect(gs)
    gs._on_message(
        host, {"command": "!CREATE_ROOM", "value": ("map", {0: (0, 0), 1: (10, 10)})}
    )

    joiner = _connect(gs)
    gs._on_message(joiner, {"command": "!JOIN_ROOM", "value": 1})

    room = gs.room_list[1]
    assert len(room) == 2
    # The joiner was sent a populated room (not the rejection sentinel False).
    update = joiner.last_with("!UPDATE_ROOM")
    assert update is not None and update["value"] is not False


def test_join_full_room_is_rejected():
    gs = GameServer()
    host = _connect(gs)
    # One base point -> room size 1, so it's full once the host is in it.
    gs._on_message(host, {"command": "!CREATE_ROOM", "value": ("map", {0: (0, 0)})})

    joiner = _connect(gs)
    gs._on_message(joiner, {"command": "!JOIN_ROOM", "value": 1})

    assert len(gs.room_list[1]) == 1
    # Rejection is signalled by !UPDATE_ROOM with value False.
    assert joiner.last_with("!UPDATE_ROOM")["value"] is False


def test_list_rooms_returns_public_room_summaries():
    gs = GameServer()
    host = _connect(gs)
    gs._on_message(
        host, {"command": "!CREATE_ROOM", "value": ("map", {0: (0, 0), 1: (10, 10)})}
    )

    asker = _connect(gs)
    gs._on_message(asker, {"command": "!LIST_ROOMS"})

    rooms = asker.last_with("!LIST_ROOMS")["value"]
    assert len(rooms) == 1
    summary = rooms[0]
    assert summary["id"] == 1
    assert summary["map_name"] == "map"
    assert summary["players"] == 1  # the host
    assert summary["size"] == 2
    assert summary["started"] is False


def test_list_rooms_excludes_private_rooms():
    gs = GameServer()
    host = _connect(gs)
    # A private room (is_public=False) must not surface in the browser.
    gs._on_message(
        host,
        {"command": "!CREATE_ROOM", "value": ("map", {0: (0, 0), 1: (10, 10)}, False)},
    )

    asker = _connect(gs)
    gs._on_message(asker, {"command": "!LIST_ROOMS"})

    assert asker.last_with("!LIST_ROOMS")["value"] == []
    # ...but it's still joinable by id (room 1 was created).
    gs._on_message(asker, {"command": "!JOIN_ROOM", "value": 1})
    assert len(gs.room_list[1]) == 2


def test_leaving_last_player_deletes_room():
    gs = GameServer()
    host = _connect(gs)
    gs._on_message(host, {"command": "!CREATE_ROOM", "value": ("map", {0: (0, 0)})})
    assert 1 in gs.room_list

    gs._on_message(host, {"command": "!LEAVE_ROOM"})

    assert 1 not in gs.room_list
    assert host.last_with("!LEAVE_ROOM") is not None


def test_disconnect_cleans_up_all_maps():
    gs = GameServer()
    conn = _connect(gs)
    player_id = gs._players_by_connection[conn].id

    gs._on_disconnect(conn)

    assert gs.players == {}
    assert conn not in gs._players_by_connection
    assert player_id not in gs._connection_by_player_id


def test_shoot_is_relayed_to_room_mates():
    gs = GameServer()
    host = _connect(gs)
    gs._on_message(
        host, {"command": "!CREATE_ROOM", "value": ("map", {0: (0, 0), 1: (10, 10)})}
    )
    joiner = _connect(gs)
    gs._on_message(joiner, {"command": "!JOIN_ROOM", "value": 1})

    gs._on_message(joiner, {"command": "!SHOOT", "value": 42})

    # !SHOOT goes to everyone in the room (including the shooter, per current rules).
    assert host.last_with("!SHOOT")["value"] == 42
    assert joiner.last_with("!SHOOT")["value"] == 42


# ── Server-authoritative mobs ───────────────────────────────────────────────────


def test_update_player_records_position_and_alive_then_relays():
    gs = GameServer()
    host = _host_in_room(gs)
    joiner = _connect(gs)
    gs._on_message(joiner, {"command": "!JOIN_ROOM", "value": 1})
    player = gs._players_by_connection[host]

    gs._on_message(
        host, {"command": "!UPDATE_PLAYER", "value": [player.id, (123, 456), 90, True]}
    )

    assert player.position == (123, 456)
    assert player.alive is True
    # Relayed verbatim to room mates so they can interpolate the remote player.
    assert joiner.last_with("!UPDATE_PLAYER")["value"][1] == (123, 456)

    # Death is reported the same way; the server records it for mob targeting.
    gs._on_message(
        host, {"command": "!UPDATE_PLAYER", "value": [player.id, (1, 2), 0, False]}
    )
    assert player.alive is False


def test_spawn_mob_assigns_unique_ids_across_rooms():
    gs = GameServer()
    _host_in_room(gs)  # room 1 (host connection not needed here)
    h2 = _connect(gs)
    gs._on_message(
        h2, {"command": "!CREATE_ROOM", "value": ("map", {0: (0, 0)})}
    )  # room 2
    room1, room2 = gs.room_list[1], gs.room_list[2]

    # Both rooms number their own mob 1; the server must keep them distinct.
    mob1 = MobInfo(1, room1, (0, 0), (0, 0))
    mob2 = MobInfo(1, room2, (0, 0), (0, 0))
    gs.spawn_mob(room1, mob1)
    gs.spawn_mob(room2, mob2)

    assert mob1.id != mob2.id
    assert gs.mobs[mob1.id] is mob1
    assert gs.mobs[mob2.id] is mob2

    # Killing room 2's mob must not touch room 1's.
    gs._on_message(h2, {"command": "!HIT_MOB", "value": (mob2.id, mob2.hp)})
    assert mob1.id in gs.mobs
    assert mob2.id not in gs.mobs


def test_hit_mob_applies_damage_without_killing():
    gs = GameServer()
    host = _host_in_room(gs)
    room = gs.room_list[1]
    mob = MobInfo(1, room, (0, 0), (0, 0))
    gs.spawn_mob(room, mob)
    full = mob.hp

    gs._on_message(host, {"command": "!HIT_MOB", "value": (mob.id, 10)})

    assert gs.mobs[mob.id].hp == full - 10
    assert host.last_with("!KILL_MOB") is None  # still alive


def test_hit_mob_lethal_removes_and_broadcasts_kill():
    gs = GameServer()
    host = _host_in_room(gs)
    room = gs.room_list[1]
    mob = MobInfo(1, room, (0, 0), (0, 0))
    gs.spawn_mob(room, mob)

    gs._on_message(host, {"command": "!HIT_MOB", "value": (mob.id, mob.hp)})

    assert mob.id not in gs.mobs
    kill = host.last_with("!KILL_MOB")
    assert kill is not None and kill["value"] == mob.id


def test_hit_on_unknown_mob_is_ignored():
    gs = GameServer()
    host = _host_in_room(gs)

    # A stale/duplicate hit on a mob that's already gone must be a safe no-op.
    gs._on_message(host, {"command": "!HIT_MOB", "value": (999, 10)})

    assert 999 not in gs.mobs


def test_simulate_mobs_chases_in_range_living_player():
    gs = GameServer()
    host = _host_in_room(gs)
    gs._players_by_connection[host].position = (RANGE_RADIUS // 2, 0)  # in range
    room = gs.room_list[1]
    mob = MobInfo(1, room, (0, -100), (0, 0))  # base is up; player is to the right
    gs.spawn_mob(room, mob)

    gs._simulate_mobs(room, 0.1)

    assert gs.mobs[mob.id].position[0] > 0  # stepped toward the player (+x)


def test_simulate_mobs_ignores_dead_players():
    gs = GameServer()
    host = _host_in_room(gs)
    player = gs._players_by_connection[host]
    player.position = (RANGE_RADIUS // 2, 0)  # in range, but...
    player.alive = False  # ...dead, so it must not attract the mob
    room = gs.room_list[1]
    mob = MobInfo(1, room, (0, -100), (0, 0))  # base is up (-y)
    gs.spawn_mob(room, mob)

    gs._simulate_mobs(room, 0.1)

    pos = gs.mobs[mob.id].position
    assert pos[1] < 0 and pos[0] == 0  # went to base, not the corpse


def test_simulate_mobs_out_of_range_returns_to_base():
    gs = GameServer()
    host = _host_in_room(gs)
    gs._players_by_connection[host].position = (RANGE_RADIUS * 10, 0)  # far away
    room = gs.room_list[1]
    mob = MobInfo(1, room, (0, -100), (0, 0))  # base is up (-y)
    gs.spawn_mob(room, mob)

    gs._simulate_mobs(room, 0.1)

    assert gs.mobs[mob.id].position[1] < 0  # headed to base, not the distant player


def test_simulate_mobs_redirects_from_dead_players_base():
    gs = GameServer()
    host = _host_in_room(gs, base_points={0: (0, 0), 1: (100, 0)})
    joiner = _connect(gs)
    gs._on_message(joiner, {"command": "!JOIN_ROOM", "value": 1})

    host_player = gs._players_by_connection[host]
    joiner_player = gs._players_by_connection[joiner]
    host_player.alive = False  # base (0, 0) owner is down
    joiner_player.position = (100, RANGE_RADIUS * 10)  # alive but far out of range

    room = gs.room_list[1]
    mob = MobInfo(1, room, host_player.base_point, (50, 50))  # targeting the dead base
    gs.spawn_mob(room, mob)

    gs._simulate_mobs(room, 0.1)

    # Peeled off the dead (0, 0) base toward the only living base at (100, 0): +x.
    assert gs.mobs[mob.id].position[0] > 50


def test_broadcast_mobs_sends_id_position_and_hp():
    gs = GameServer()
    host = _host_in_room(gs)
    room = gs.room_list[1]
    mob = MobInfo(1, room, (0, 0), (5, 6))
    gs.spawn_mob(room, mob)

    gs._broadcast_mobs(room)

    entries = host.last_with("!UPDATE_MOBS")["value"]
    assert entries == [(mob.id, (5, 6), mob.hp)]


# ── Join in progress ────────────────────────────────────────────────────────


def test_start_game_marks_room_started(monkeypatch):
    gs = GameServer()
    host = _host_in_room(gs)
    # Don't spin up the real mob-sim thread; we only care about the flag + message.
    monkeypatch.setattr(gs, "handle_room", lambda room: None)

    gs._on_message(host, {"command": "!START_GAME"})

    assert gs.room_list[1].started is True
    assert host.last_with("!START_GAME") is not None


def test_join_game_in_progress_sends_start_and_live_mobs():
    gs = GameServer()
    _host_in_room(gs)
    room = gs.room_list[1]
    room.started = True  # match already running
    # Mobs spawn while only the host is in the room, so the late joiner never saw
    # these SPAWNs — exactly the case that left them in an empty world.
    gs.spawn_mob(room, MobInfo(1, room, (0, 0), (5, 6)))
    gs.spawn_mob(room, MobInfo(2, room, (0, 0), (7, 8)))

    joiner = _connect(gs)
    gs._on_message(joiner, {"command": "!JOIN_ROOM", "value": 1})
    gs._on_message(joiner, {"command": "!JOIN_GAME"})

    assert joiner.last_with("!START_GAME") is not None  # builds their scene
    spawns = [m for m in joiner.sent if m["command"] == "!SPAWN"]
    assert len(spawns) == 2  # seeded with both live mobs they'd missed


def test_join_game_before_start_just_readies_player():
    gs = GameServer()
    _host_in_room(gs)
    joiner = _connect(gs)
    gs._on_message(joiner, {"command": "!JOIN_ROOM", "value": 1})
    joiner_player = gs._players_by_connection[joiner]
    assert joiner_player.is_ready is False

    gs._on_message(joiner, {"command": "!JOIN_GAME"})

    assert joiner_player.is_ready is True
    assert joiner.last_with("!START_GAME") is None  # not started -> no drop-in


def test_simulate_mobs_separates_stacked_mobs():
    gs = GameServer()
    _host_in_room(gs)
    room = gs.room_list[1]
    a = MobInfo(1, room, (0, 0), (100, 100))
    b = MobInfo(1, room, (0, 0), (105, 100))  # 5px away, within AVOID_RADIUS
    gs.spawn_mob(room, a)
    gs.spawn_mob(room, b)

    def gap():
        pa, pb = gs.mobs[a.id].position, gs.mobs[b.id].position
        return ((pa[0] - pb[0]) ** 2 + (pa[1] - pb[1]) ** 2) ** 0.5

    before = gap()
    gs._simulate_mobs(room, 0.1)
    assert gap() > before  # separation pushed them apart
