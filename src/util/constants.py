from __future__ import annotations

import os
import pygame
from colorama import Fore
import socket
from enum import StrEnum
from pygame.math import Vector2 as Vec

# Colors
Black = (0, 0, 0)
White = (255, 255, 255)
Red = (255, 0, 0)
Blue = (0, 0, 255)
Yellow = (255, 255, 0)
Gray = (128, 128, 128)
Green = (0, 128, 0)
CustomBlue = (72, 218, 233)

SERVER_PREFIX = f"{Fore.CYAN}[SERVER] {Fore.RED}=> {Fore.YELLOW}"

# Window
WINDOW_TITLE = "Standoff"

# UI_REFERENCE_SIZE is the resolution config/panels.yaml was authored against;
# the lobby maps that layout onto the actual window so menus look right at any
# logical resolution.
UI_REFERENCE_SIZE = (1920, 1080)

_TOUCH = bool(os.environ.get("ANDROID_ARGUMENT")) or bool(
    os.environ.get("STANDOFF_TOUCH")
)

# No longer a design/render resolution -- Application's canvas is always
# sized off the real display now (see RENDER_SCALE for the actual
# render-resolution knob). This is just the preferred *windowed* size,
# relevant on desktop only (Android has no windowing concept; F11 never
# fires there).
WINDOW_SIZE = (1920, 1080)

# Fraction of the real display's pixels Application actually renders at
# (self.window), upscaled for free in _present(). On touch devices this
# renders at ~2/3 linear resolution (~44% of the pixels), roughly halving
# the per-frame software-blit cost -- the in-game bottleneck -- at the cost
# of a softer/more zoomed-in image (the camera viewport is the logical
# render size, so a lower RENDER_SCALE shows a tighter slice of the arena).
# Desktop renders 1:1. Raise this (e.g. 0.8) for less zoom at the cost of
# some FPS on weaker devices.
RENDER_SCALE = 2 / 3 if _TOUCH else 1.0

BACKGROUND_COLORS = {"menu": CustomBlue}

# Startup splash (pygamine.SplashScreen): fade-in then hold, per image
SPLASH_FADE_MS = 1500
SPLASH_HOLD_MS = 1000

# Game
DEVELOP_MODE = False
FPS = 60

# Upper bound on the per-frame timestep multiplier (delta_time is 1.0 at FPS).
# A slow frame (notably the first in-world frame, which includes scene/map build
# time, or any fps dip on mobile) would otherwise make movement steps huge —
# entities teleport across the arena and tunnel through walls, and the mob
# velocity integrator v += (target - v)*dt actually diverges once dt > 2. Clamp
# below 2 so physics stay stable; below ~40 fps the sim just runs a touch slow
# instead of exploding. Desktop holds 60 fps (dt ~ 1), so this never bites there.
MAX_DELTA_TIME = 1.5


# Play modes (Game.mode)
class Mode(StrEnum):
    """How a session is played. StrEnum members are real strings, so a Mode
    compares equal to its value and still serializes/logs as 'online'/'offline'."""

    ONLINE = "online"
    OFFLINE = "offline"


MAX_ROOM_SIZE = 4
HEALTH_BAR_SIZE = (60, 15)

# Tile
TILE_SIZE = TILE_WIDTH, TILE_HEIGHT = 64, 64
BORDER_WIDTH = 2
MAP_GRID_SIZE = 2

# Player
PLAYER_MAX_HP = 100
PLAYER_SIZE = TILE_SIZE
CHARACTER_SIZE = 48, 48
PLAYER_HIT_RECT = pygame.Rect(0, 0, 35, 35)
# Per-(60fps)frame velocity retained on an axis with no input (0..1). Lower
# brakes faster (less ice-skating); 1.0 would coast frictionlessly.
PLAYER_FRICTION = 0.8
# Online: how a remote player eases toward the position sent by its owner.
# REMOTE_SMOOTHING is the fraction of the gap retained per (60fps)frame (0..1) —
# lower follows faster / smooths less. Gaps beyond REMOTE_SNAP_DISTANCE px snap
# instead of easing (respawns / large corrections).
REMOTE_SMOOTHING = 0.5
REMOTE_SNAP_DISTANCE = 150
# Milliseconds a dead player must wait before respawning.
RESPAWN_DELAY = 5000
CHARACTER_LIST = [
    "hitman",
    "man_blue",
    "man_brown",
    "man_old",
    "robot",
    "solider",
    "survivor",
    "woman_green",
]

# Shooting
BARREL_OFFSET = Vec(30, 10)
SHOOT_RATE = 300
KICKBACK = 1
GUN_SPREAD = 5
BULLET_SPEED = 5
BULLET_DAMAGE = 10
FLASH_DURATOION = 40

# Mob
MOB_MAX_HP = 100
MOB_HIT_RECT = pygame.Rect(0, 0, 30, 30)
SPAWN_RATE = 2000
RANGE_RADIUS = 5 * TILE_WIDTH  # aggro range: switch from base to nearest player
AVOID_RADIUS = 50
# How strongly mobs steer apart vs. toward their target (server-side separation).
# 0 = no avoidance (they stack); higher spreads them out more.
MOB_SEPARATION = 1.5
MOB_SPEEDS = [1.2, 1.3, 1.4, 1.1]
MOB_KNOCKBACK = 20  # total knockback distance (px), spread smoothly over frames
KNOCKBACK_DECAY = 0.8  # per-frame falloff of the knockback impulse (0..1)

# Sprite layers
WALL_LAYER = 1
ENTITY_LAYER = 2
BULLET_LAYER = 3
EFFECT_LAYER = 4
GUI_LAYER = 5


# Sockets
def _local_ip() -> str:
    # Resolved at import time. On an Android device hostname resolution can raise
    # (no /etc/hosts entry for the device name), which would crash the app before
    # it starts, so fall back to loopback. The phone is a client and dials a real
    # server address anyway; this default only matters for local desktop play.
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "127.0.0.1"


CLIENT_IP = _local_ip()
CLIENT_PORT = 5050
CLIENT_ADDR = (CLIENT_IP, CLIENT_PORT)

SERVER_IP = _local_ip()
SERVER_PORT = 5050
SERVER_ADDR = (SERVER_IP, SERVER_PORT)

SERVER_TITLE = WINDOW_TITLE + " SERVER"
SERVER_SIZE = SERVER_WIDTH, SERVER_HEIGHT = 600, 800

FORMAT = "utf-8"
