#region Importing Packages

from player_info import PlayerInfo
import pygame
import random
from settings import *
from player_info import MobInfo

#endregion

class Room(list[PlayerInfo]):

    def __init__(self, ID, mapName, basePoints, isOnline=True):

        super().__init__()
        pygame.init()

        self.ID = ID
        self.size = MAX_ROOM_SIZE
        self.mapName = mapName
        self.basePoints = basePoints
        self.isOnline = isOnline

        # Mob spawner
        self.mobID = 0
        self.lastSpawn = 0

    def HandleSpawner(self, spawnFunc):

        now = pygame.time.get_ticks()

        if now - self.lastSpawn >= SPAWN_RATE:

            for player in self:

                self.mobID += 1
                spawnPoint = player.basePoint[0] + random.choice([-1, +1]) * random.randint(10*TILE_WIDTH, 20*TILE_WIDTH), player.basePoint[0] + random.choice([-1, +1]) * random.randint(10*TILE_HEIGHT, 20*TILE_HEIGHT)
                mobInfo = MobInfo(self.mobID, self, player.basePoint, spawnPoint)

                if self.isOnline:

                    spawnFunc(self, mobInfo)

                else:

                    spawnFunc(mobInfo)

            self.lastSpawn = now

    def Update(self, spawnFunc):
        
        self.HandleSpawner(spawnFunc)