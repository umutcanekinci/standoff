"""End-to-end tests: a real GameServer with real BaseClients over loopback.

These are the slow, few tests at the top of the pyramid. They prove the whole
stack agrees (framing, pickle codec on both ends, lobby logic, broadcast fan-out)
for the handful of flows that matter most. Everything finer-grained is covered
cheaply by the unit/integration layers.
"""

import queue
import time

import pytest

from net.game_server import GameServer
from net.protocol import PickleCodec, Protocol
from net.transport import BaseClient
from _util import wait_until, start_in_thread

# Full-stack, slowest tier — CI only; the pre-commit hook skips via `-m "not e2e"`.
pytestmark = pytest.mark.e2e


def _serve(port) -> GameServer:
    gs = GameServer()
    start_in_thread(gs.serve, ("127.0.0.1", port))
    assert wait_until(lambda: gs.is_running), "GameServer never started"
    return gs


def _client(port) -> tuple[BaseClient, queue.Queue]:
    inbox: queue.Queue = queue.Queue()
    # Must match GameServer's codec (pickle) — this is the bug the suite guards.
    client = BaseClient(on_message=inbox.put, protocol=Protocol(PickleCodec()))
    assert client.connect(("127.0.0.1", port))
    return client, inbox


def _get_until(inbox: queue.Queue, command: str, timeout: float = 2.0):
    """Drain messages until one with `command` arrives; fail if it never does."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            message = inbox.get(timeout=deadline - time.monotonic())
        except queue.Empty:
            break
        if message.get("command") == command:
            return message
    raise AssertionError(f"never received {command}")


def test_connect_receives_player_count_and_room_update(free_port):
    gs = _serve(free_port)
    client, inbox = _client(free_port)

    try:
        assert _get_until(inbox, "!SET_PLAYER_COUNT")["value"] == 1
        assert _get_until(inbox, "!UPDATE_ROOM") is not None
        assert wait_until(lambda: len(gs.players) == 1)
    finally:
        client.disconnect()
        gs.close()


def test_two_clients_create_and_join_a_room(free_port):
    gs = _serve(free_port)
    host, host_inbox = _client(free_port)
    joiner, joiner_inbox = _client(free_port)

    try:
        host.send("!SET_PLAYER", ["Host", "knight"])
        host.send("!CREATE_ROOM", ("forest", {0: (0, 0), 1: (10, 10)}))
        # Host is placed into the new room.
        created = _get_until(host_inbox, "!UPDATE_ROOM")
        assert created["value"] is not False
        assert wait_until(lambda: 1 in gs.room_list)

        joiner.send("!SET_PLAYER", ["Joiner", "mage"])
        joiner.send("!JOIN_ROOM", 1)

        # The join fans out an !UPDATE_ROOM to both room mates, and the server
        # state shows two players in the room.
        assert _get_until(joiner_inbox, "!UPDATE_ROOM")["value"] is not False
        assert wait_until(lambda: len(gs.room_list[1]) == 2)
    finally:
        host.disconnect()
        joiner.disconnect()
        gs.close()


def test_disconnect_decrements_server_player_count(free_port):
    gs = _serve(free_port)
    a, _ = _client(free_port)
    b, _ = _client(free_port)

    assert wait_until(lambda: len(gs.players) == 2)
    a.disconnect()
    assert wait_until(lambda: len(gs.players) == 1), "server did not drop the player"

    b.disconnect()
    gs.close()
