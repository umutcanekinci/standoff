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
