from util.constants import MOB_MAX_HP


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
        # to steer mobs toward players. Seeded to the spawn base in join_room.
        self.position = (0, 0)
        self.alive = True  # client reports this; mobs ignore dead players

        # Room membership — populated by join_room(), cleared by leave_room().
        self.room = None
        self.is_ready = False
        self.is_ruler = False
        self.base_number = None
        self.base_point = None

    def set_name(self, name: str):
        self.name = name

    def set_character_name(self, name: str):
        self.character_name = name

    def join_room(self, room, is_ruler):
        self.is_ready = is_ruler
        self.is_ruler = is_ruler
        self.room = room
        room.append(self)
        # Take the first base point not already claimed by a room mate (len()-based
        # numbering breaks when a player leaves and another joins).
        used = {
            mate.base_number
            for mate in room
            if mate is not self and hasattr(mate, "base_number")
        }
        self.base_number = next(
            number for number in room.base_points if number not in used
        )
        self.base_point = self.room.base_points[self.base_number]
        self.position = self.base_point

    def leave_room(self):
        self.room.remove(self)
        self.room = None

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
            data["id"],
            name=data.get("name", ""),
            character_name=data.get("character_name", ""),
        )
        player.base_number = data.get("base_number")
        base_point = data.get("base_point")
        player.base_point = tuple(base_point) if base_point is not None else None
        player.is_ready = data.get("is_ready", False)
        player.is_ruler = data.get("is_ruler", False)
        player.size = data.get("size", 1)
        player.position = tuple(data.get("position", (0, 0)))
        player.alive = data.get("alive", True)
        player.room = data.get("room")  # already a Room (object_hook) or absent
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
        target_base = data.get("target_base")
        mob = cls(
            data["id"],
            None,
            tuple(target_base) if target_base is not None else None,
            tuple(data["position"]),
        )
        mob.size = data.get("size", 1)
        mob.hp = data.get("hp", mob.hp)
        return mob
