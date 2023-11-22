import pygame

# TO-DO

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

#-# Colors #-#
Black = (0,0,0)
White = (255,255,255)
Red = (255,0,0)
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

#-# Settings #-#
WINDOW_TITLE = "CHOOSE YOUR WAY"
WINDOW_SIZE = WINDOW_WIDTH, WINDOW_HEIGHT = 1920, 1080
WINDOW_RECT = pygame.Rect((0, 0), WINDOW_SIZE)
BACKGROUND_COLORS = {"mainMenu" : CustomBlue}
DEVELOP_MODE = False
FPS = 60
PLAYER_SPAWNPOINT = 0, 0
TILE_SIZE = 64
CHARACTER_SIZE = 48, 48
BORDER_WIDTH = 2
PLAYER_HIT_RECT = pygame.Rect(0, 0, 35, 35)
MOVABLE_TILES = ["01", "55", "56", "57", "60", "61"]

#-# Socket #-#
IP = "localhost" #"5.tcp.eu.ngrok.io"
PORT = 5050
ADDR = (IP, PORT)

SERVER_IP = "localhost" # socket.gethostbyname(socket.gethostname())
SERVER_PORT = 5050
SERVER_ADDR = (SERVER_IP, SERVER_PORT)

HEADER = 4
FORMAT = 'utf-8'