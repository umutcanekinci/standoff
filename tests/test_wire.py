"""Unit tests for net.wire: the JSON wire form of the game's own types.

test_protocol.py proves TypedJSONCodec works for a toy type; this pins the
*real* round-trips that the comments in player_info.py / room.py call out as
fragile, and that otherwise only e2e exercises:

  - Room.base_points survives as dict[int, tuple] (JSON stringifies keys and
    flattens tuples to lists, so both must be coerced back),
  - the PlayerInfo <-> Room reference cycle is broken on the way out and rebuilt
    on the way in (no infinite recursion, players re-pointed at their room),
  - MobInfo drops its server-only fields and restores tuples.

Building the Protocol from net.wire.make_protocol() (not a hand-rolled codec)
means these also guard that WIRE_TYPES stays in sync with the classes.
"""

from net.wire import make_protocol, WIRE_TYPES
from net.player_info import PlayerInfo, MobInfo
from net.room import Room
from _util import FakeSocket


def _round_trip(value):
    """Send {value: <obj>} through the real protocol and read it back."""
    proto = make_protocol()
    writer = FakeSocket()
    proto.send(writer, {"command": "!X", "value": value})
    return proto.recv(FakeSocket(writer.sent))["value"]


def _populated_room() -> tuple[Room, PlayerInfo, PlayerInfo]:
    room = Room(7, "dust", {0: (10, 20), 1: (30, 40)})
    ruler = PlayerInfo(1, ("1.2.3.4", 5000), name="alice", character_name="red")
    guest = PlayerInfo(2, ("5.6.7.8", 6000), name="bob", character_name="blue")
    ruler.join_room(room, is_ruler=True)
    guest.join_room(room, is_ruler=False)
    return room, ruler, guest


def test_wire_types_registered():
    """The codec must know every type the two ends send, by tag."""
    assert WIRE_TYPES == {
        "PlayerInfo": PlayerInfo,
        "Room": Room,
        "MobInfo": MobInfo,
    }


def test_player_without_room_round_trips():
    """A bare PlayerInfo (no room) comes back as a PlayerInfo with room None and
    its tuples (position) restored — base_point None stays None, not ()."""
    player = PlayerInfo(3, name="carol", character_name="green")
    player.position = (12, 34)

    out = _round_trip(player)

    assert isinstance(out, PlayerInfo)
    assert (out.id, out.name, out.character_name) == (3, "carol", "green")
    assert out.position == (12, 34) and isinstance(out.position, tuple)
    assert out.base_point is None
    assert out.room is None


# A Room only ever crosses the wire *embedded in a PlayerInfo* (the server always
# sends the player for UPDATE_ROOM, never a bare room). That's not incidental:
# Room subclasses list, so json.dumps would serialise a bare Room as a plain
# array and skip Room.to_dict entirely. So these go through the carrier player.


def test_room_base_points_keep_int_keys_and_tuples():
    """base_points is dict[int, tuple]; JSON can keep neither, so the codec must
    rebuild both. A regression here silently moves every spawn point."""
    _room, ruler, _guest = _populated_room()

    out = _round_trip(ruler).room

    assert isinstance(out, Room)
    assert out.base_points == {0: (10, 20), 1: (30, 40)}
    assert all(isinstance(k, int) for k in out.base_points)
    assert all(isinstance(v, tuple) for v in out.base_points.values())
    assert (out.id, out.map_name) == (7, "dust")


def test_room_round_trip_rebuilds_player_cycle():
    """The carried room comes back with every player pointed at that one room
    instance (the cycle is rebuilt), with no nested-room recursion."""
    _room, ruler, _guest = _populated_room()

    out = _round_trip(ruler).room

    assert len(out) == 2
    assert {p.name for p in out} == {"alice", "bob"}
    for player in out:
        assert isinstance(player, PlayerInfo)
        assert player.room is out  # re-pointed at THIS room, not a copy


def test_player_carries_its_room_without_recursing():
    """The server sends a PlayerInfo that carries the whole room; encoding must
    terminate (players inside the room are serialised room-less) and the decoded
    player's room must list players whose base points survived."""
    _room, ruler, _guest = _populated_room()

    out = _round_trip(ruler)  # include_room defaults to True

    assert isinstance(out, PlayerInfo)
    assert out.base_number == 0 and out.base_point == (10, 20)
    assert isinstance(out.room, Room)
    assert len(out.room) == 2
    # The ruler appears inside its own room's player list, room-less there.
    me = next(p for p in out.room if p.id == ruler.id)
    assert me.base_point == (10, 20)


def test_mobinfo_round_trip_drops_server_only_fields():
    """MobInfo crosses with only id/position/size/target_base/hp; room and
    target_player are server-only and must not be required to decode."""
    room, _ruler, _guest = _populated_room()
    mob = MobInfo(42, room, target_base=(10, 20), position=(100, 200))
    mob.hp = 50

    out = _round_trip(mob)

    assert isinstance(out, MobInfo)
    assert out.id == 42
    assert out.position == (100, 200) and isinstance(out.position, tuple)
    assert out.target_base == (10, 20) and isinstance(out.target_base, tuple)
    assert out.hp == 50
    assert out.room is None
