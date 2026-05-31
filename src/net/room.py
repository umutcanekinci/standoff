import pygame
import random

from util.constants import *
from net.player_info import PlayerInfo, MobInfo


class Room(list[PlayerInfo]):
    def __init__(self, id, map_name, base_points, is_online=True):
        super().__init__()

        if not pygame.get_init():
            pygame.init()

        self.id = id
        self.size = min(MAX_ROOM_SIZE, len(base_points))
        self.map_name = map_name
        self.base_points = base_points
        self.is_online = is_online

        # Mob spawner
        self.mob_id = 0
        self.last_spawn = 0

    def handle_spawner(self, spawn_func):
        now = pygame.time.get_ticks()

        if now - self.last_spawn >= SPAWN_RATE:
            for player in self:
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
