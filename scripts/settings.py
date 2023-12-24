#region #-# Import Paackages #-#

import pygame
from colorama import Fore
import socket
from pygame.math import Vector2 as Vec

#endregion

#region TO-DO

# collision with obstacles
# shooting improvments
# online position fix
# lose hp
# mobs
# sounds
# pause screen
# background music
# character selection
# item collecting
# crafting
# days
# effects


# takımlar birbiine saldırabilecek
# aynı takımdakiler birbirine saldıramayacak
# takımdaki oyuncular oyuna aynı anda mı girmeli / istedikleri zaman mı

#endregion

#region #-# Colors #-#

Black = (0,0,0)
White = (255,255,255)
Red = (255,0,0)
LightRed = (255, 127, 127)
Lime = (0,255,0)
Blue = (0,0,255)
Yellow = (255,255,0)
Cyan = (0,255,255)
Magenta = (255,0,255)
Silver = (192,192,192)
Gray = (128,128,128)
Maroon = (128,0,0)
Olive = (128,128,0)
Green = (0,128,0)
Purple = (128,0,128)
Teal = (0,128,128)
Navy = (0,0,128)
CustomBlue = (72, 218, 233)

SERVER_PREFIX = f"{Fore.CYAN}[SERVER] {Fore.RED}=> {Fore.YELLOW}"

#endregion

#region #-# Game Settings #-#

#-# Window #-#
WINDOW_TITLE = "CHOOSE YOUR WAY"
WINDOW_SIZE = WINDIW_WIDTH, WINDOW_HEIGHT = 1920, 1080
WINDOW_RECT = pygame.Rect((0, 0), WINDOW_SIZE)

BACKGROUND_COLORS = {"menu" : CustomBlue}

#-# Game #-#
DEVELOP_MODE = False
FPS = 60
MAX_ROOM_SIZE = 4
HEALTH_BAR_SIZE = (60, 15)

#-# Tile #-#
TILE_SIZE = TILE_WIDTH, TILE_HEIGHT = 64, 64
BORDER_WIDTH = 2
MAP_GRID_SIZE = 2

#-# Player #-#
PLAYER_MAX_HP = 100
PLAYER_SIZE = TILE_SIZE
CHARACTER_SIZE = 48, 48
PLAYER_HIT_RECT = pygame.Rect(0, 0, 35, 35)
CHARACTER_LIST = ["hitman", "man_blue", "man_brown", "man_old", "robot", "solider", "survivor", "woman_green"] # , "zombie"

#-# Shooting #-#
BARREL_OFFSET = Vec(30, 10)
SHOOT_RATE = 300
KICKBACK = 1
GUN_SPREAD = 5
BULLET_SPEED = 5
BULLET_DAMAGE = 10
FLASH_DURATOION = 40

#-# Mob #-#
MOB_MAX_HP = 100
MOB_HIT_RECT = pygame.Rect(0, 0, 30, 30)
SPAWN_RATE = 2000
RANGE_RADIUS = 5*TILE_WIDTH # for attract by players
AVOID_RADIUS = 50
MOB_SPEEDS = [1.2, 1.3, 1.4, 1.1]
MOB_KNOCKBACK = 20

#-# Sprite Layers #-#
WALL_LAYER = 1 
ENTITY_LAYER = 2
BULLET_LAYER = 3
EFFECT_LAYER = 4
GUI_LAYER = 5
#endregion

#region #-# Socket Settings#-#

#-# Client #-#
CLIENT_IP = socket.gethostbyname(socket.gethostname()) #"localhost" #"5.tcp.eu.ngrok.io"
CLIENT_PORT = 5050
CLIENT_ADDR = (CLIENT_IP, CLIENT_PORT)

#-# Server #-#
SERVER_IP = socket.gethostbyname(socket.gethostname()) #localhost
SERVER_PORT = 5050
SERVER_ADDR = (SERVER_IP, SERVER_PORT)

SERVER_TITLE = WINDOW_TITLE + " SERVER"
SERVER_SIZE = SERVER_WIDTH, SERVER_HEIGHT = 600, 800

HEADER = 4
FORMAT = 'utf-8'

#endregion