from __future__ import annotations

from util.constants import MOB_MAX_HP


# --- Wire-decoding guards ------------------------------------------------------
# from_dict runs inside the codec's json.loads(object_hook=...) on bytes from a
# possibly hostile peer. A raw data["id"] / tuple(data["position"]) would raise
# KeyError/TypeError, which json.loads propagates straight up and crashes the
# decode thread. Protocol.recv only catches ValueError (-> ProtocolError, a
# cleanly dropped message), so these helpers funnel every "malformed payload"
# case into ValueError. The promise in wire.py ("a peer can send bad data but
# never run code") only holds if bad data degrades to a dropped message.


def _require(data: dict, key: str):
    """Return a mandatory wire field, or raise ValueError if it's absent."""
    if not isinstance(data, dict) or key not in data:
        raise ValueError(f"wire payload missing required field {key!r}")
    return data[key]


def _as_point(value) -> tuple:
    """Coerce a wire ``[x, y]`` back into a numeric ``(x, y)`` tuple.

    JSON has no tuples, so points arrive as 2-element lists; a hostile/buggy peer
    could send the wrong shape or non-numbers, so validate rather than trust.
    """
    try:
        x, y = value
    except (TypeError, ValueError) as exc:
        raise ValueError(f"expected an [x, y] point, got {value!r}") from exc
    # bool is an int subclass; reject it so True/False can't masquerade as coords.
    if (
        isinstance(x, bool)
        or isinstance(y, bool)
        or not isinstance(x, (int, float))
        or not isinstance(y, (int, float))
    ):
        raise ValueError(f"point coordinates must be numbers, got {value!r}")
    return (x, y)


def _opt_point(value):
    """_as_point, but a nullable field: None passes through untouched."""
    return None if value is None else _as_point(value)


class PlayerInfo:
    name: str  # set via set_name(), which __init__ calls
    character_name: str  # set via set_character_name(), which __init__ calls

    def __init__(self, player_id=1, address=(0, 0), name="", character_name="") -> None:
        self.id = player_id
        self.address = self.IP, self.PORT = address
        self.size = 1
        self.set_name(name)
        self.set_character_name(character_name)

        # Latest center the client reported (UPDATE_PLAYER); the server reads it
        # to steer mobs toward players. Seeded to the spawn base by Room.add_player.
        self.position = (0, 0)
        self.alive = True  # client reports this; mobs ignore dead players

        # Room membership — populated by Room.add_player(), cleared by
        # Room.remove_player(). PlayerInfo just holds the back-ref; the room owns
        # the roster logic (base-slot assignment, ruler handover).
        self.room = None
        self.is_ready = False
        self.is_ruler = False
        self.base_number = None
        self.base_point = None

    def set_name(self, name: str):
        self.name = name

    def set_character_name(self, name: str):
        self.character_name = name

    # Wire form (TypedJSONCodec). Tuples become lists and dict keys become strings
    # over JSON, so to_dict/from_dict coerce back. `include_room` breaks the
    # PlayerInfo<->Room cycle: the player the server sends carries the whole room,
    # but the players listed *inside* that room are serialised without it.
    def to_dict(self, include_room: bool = True) -> dict:
        data = {
            "__type__": "PlayerInfo",
            "id": self.id,
            "name": self.name,
            "character_name": self.character_name,
            "base_number": self.base_number,
            "base_point": list(self.base_point)
            if self.base_point is not None
            else None,
            "is_ready": self.is_ready,
            "is_ruler": self.is_ruler,
            "size": self.size,
            "position": list(self.position),
            "alive": self.alive,
        }
        if include_room and self.room is not None:
            data["room"] = self.room.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerInfo":
        player = cls(
            _require(data, "id"),
            name=data.get("name", ""),
            character_name=data.get("character_name", ""),
        )
        player.base_number = data.get("base_number")
        player.base_point = _opt_point(data.get("base_point"))
        player.is_ready = bool(data.get("is_ready", False))
        player.is_ruler = bool(data.get("is_ruler", False))
        player.size = data.get("size", 1)
        player.position = _as_point(data.get("position", (0, 0)))
        player.alive = bool(data.get("alive", True))
        # Already a Room (object_hook ran on the nested dict) or absent. A peer
        # could send a dict that isn't a tagged Room; reject it rather than store
        # a half-object the game logic will choke on later. Local import to dodge
        # the room <-> player_info import cycle.
        room = data.get("room")
        if room is not None:
            from net.room import Room

            if not isinstance(room, Room):
                raise ValueError(
                    f"expected a Room for 'room', got {type(room).__name__}"
                )
        player.room = room
        return player


class MobInfo:
    def __init__(self, mob_id, room, target_base, position, target_player=None) -> None:
        (
            self.id,
            self.room,
            self.target_base,
            self.position,
            self.size,
            self.target_player,
        ) = mob_id, room, target_base, position, 1, target_player
        self.hp = MOB_MAX_HP  # server-authoritative; clients display, don't decide

    # Wire form (TypedJSONCodec). The client only needs id/position/size/target_base
    # to spawn a mob; room/target_player are server-only, so they don't cross.
    def to_dict(self) -> dict:
        return {
            "__type__": "MobInfo",
            "id": self.id,
            "position": list(self.position),
            "size": self.size,
            "target_base": list(self.target_base)
            if self.target_base is not None
            else None,
            "hp": self.hp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MobInfo":
        mob = cls(
            _require(data, "id"),
            None,
            _opt_point(data.get("target_base")),
            _as_point(_require(data, "position")),
        )
        mob.size = data.get("size", 1)
        mob.hp = data.get("hp", mob.hp)
        return mob
