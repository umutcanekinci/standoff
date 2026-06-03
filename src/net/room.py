from __future__ import annotations

import pygame
import random

from util.constants import MAX_ROOM_SIZE, SPAWN_RATE, TILE_WIDTH, TILE_HEIGHT
from net.player_info import PlayerInfo, MobInfo


class Room(list[PlayerInfo]):
    def __init__(self, room_id, map_name, base_points, is_online=True, is_public=True):
        super().__init__()

        if not pygame.get_init():
            pygame.init()

        self.id = room_id
        self.size = min(MAX_ROOM_SIZE, len(base_points))
        self.map_name = map_name
        self.base_points = base_points
        self.is_online = is_online
        # Public rooms appear in the room browser (LIST_ROOMS); private ones are
        # reachable only by typing their id. Listen-server games default public so
        # a LAN friend who connects sees the host's room without knowing its id.
        self.is_public = is_public
        # True once the match has started, so a player who joins (or readies up)
        # afterwards can be dropped straight into the game in progress instead of
        # being stranded in the lobby. Server-authoritative; not serialised.
        self.started = False

        # Mob spawner
        self.mob_id = 0
        self.last_spawn = 0

    def handle_spawner(self, spawn_func):
        now = pygame.time.get_ticks()

        if now - self.last_spawn >= SPAWN_RATE:
            for player in self:
                if not player.alive:
                    continue  # dead players stop attracting mobs: no wave at their base
                self.mob_id += 1
                spawn_point = (
                    player.base_point[0]
                    + random.choice([-1, +1])
                    * random.randint(10 * TILE_WIDTH, 20 * TILE_WIDTH),
                    player.base_point[1]
                    + random.choice([-1, +1])
                    * random.randint(10 * TILE_HEIGHT, 20 * TILE_HEIGHT),
                )
                mob_info = MobInfo(self.mob_id, self, player.base_point, spawn_point)

                if self.is_online:
                    spawn_func(self, mob_info)

                else:
                    spawn_func(mob_info)

            self.last_spawn = now

    def update(self, spawn_func):
        self.handle_spawner(spawn_func)

    # Wire form (TypedJSONCodec). base_points is dict[int, tuple]; JSON can't keep
    # int keys or tuples, so it travels as [[number, [x, y]], ...] and is rebuilt
    # to dict[int, tuple]. Players are serialised without their room back-ref to
    # break the cycle, then re-pointed at this room on the way in.
    def to_dict(self) -> dict:
        return {
            "__type__": "Room",
            "id": self.id,
            "map_name": self.map_name,
            "size": self.size,
            "is_online": self.is_online,
            "is_public": self.is_public,
            "base_points": [
                [number, list(point)] for number, point in self.base_points.items()
            ],
            "players": [player.to_dict(include_room=False) for player in self],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Room":
        base_points = {
            int(number): tuple(point) for number, point in data.get("base_points", [])
        }
        room = cls(
            data["id"],
            data["map_name"],
            base_points,
            data.get("is_online", True),
            data.get("is_public", True),
        )
        for player in data.get("players", []):  # already PlayerInfo (object_hook)
            player.room = room
            room.append(player)
        return room
