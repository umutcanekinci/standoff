"""Unit tests for net.game_server.GameServer.

GameServer is socket-free, so we drive it directly through the same callbacks
the transport would call (_on_connect / _on_message / _on_disconnect) and assert
on what it sends back via a FakeConnection. Fast, deterministic, no threads.
"""

from net.game_server import GameServer
from _util import FakeConnection


def _connect(gs: GameServer) -> FakeConnection:
    """Register a fresh fake client and return its connection."""
    conn = FakeConnection()
    gs._on_connect(conn)
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
