"""Game network protocol command names — the single source of truth.

The client (``Game.get_data``) and the server (``GameServer._on_message``) each
dispatch on these strings. Keeping them here, rather than as literals scattered
across both sides, means the two dispatchers can never silently drift apart: a
renamed command is a one-line change, and a typo is an ``AttributeError`` at
import time instead of a message that's quietly ignored on the wire.

These are this game's protocol, so they live in ``net`` (the game's network
layer), not in the game-agnostic ``pygame_core`` engine.
"""


class Command:
    # Client -> Server (requests / actions)
    SET_PLAYER = "!SET_PLAYER"
    CREATE_ROOM = "!CREATE_ROOM"
    JOIN_ROOM = "!JOIN_ROOM"
    GET_READY = "!GET_READY"
    GET_UNREADY = "!GET_UNREADY"
    HIT_MOB = "!HIT_MOB"  # a client's bullet hit a mob; server owns the HP/kill

    # Server -> Client (state pushes)
    SET_PLAYER_COUNT = "!SET_PLAYER_COUNT"
    UPDATE_ROOM = "!UPDATE_ROOM"
    SPAWN = "!SPAWN"
    UPDATE_MOBS = "!UPDATE_MOBS"  # authoritative mob positions + hp, per tick
    KILL_MOB = "!KILL_MOB"  # server decided a mob died; clients remove it

    # Bidirectional (sent by one side, relayed/echoed by the other)
    LEAVE_ROOM = "!LEAVE_ROOM"
    START_GAME = "!START_GAME"
    SHOOT = "!SHOOT"
    UPDATE_PLAYER = "!UPDATE_PLAYER"
    DISCONNECT = "!DISCONNECT"
