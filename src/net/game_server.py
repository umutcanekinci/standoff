"""Game/lobby logic for the server, with no sockets in sight.

This is Layer 2: it owns players, rooms, and mobs, and it interprets the game
protocol (!JOIN_ROOM, !SHOOT, ...). It talks to the network only through a
BaseServer (Layer 1) via callbacks, and it never imports tkinter (Layer 3
subscribes to `on_status` if it wants a log). All the recv_all / struct / pickle
/ accept-loop / per-client-thread machinery lives down in the transport; what is
left here is purely "what should happen when a client says X".

Serialization note: the wire codec is built in `net.wire.make_protocol()` (shared
with the client). It's a JSON codec that round-trips PlayerInfo / Room / MobInfo
via their to_dict/from_dict, so a peer can never run code in our process the way
pickle allowed — this file is unaffected by the codec choice.
"""

from __future__ import annotations

import math
import threading
import time
from typing import Any, Callable, Iterable

from util.constants import MOB_SPEEDS, RANGE_RADIUS, AVOID_RADIUS, MOB_SEPARATION
from net.commands import Command
from net.player_info import PlayerInfo
from net.room import Room
from net.wire import make_protocol
from pygame_core.net.transport import BaseServer, Connection

# How often the server pushes authoritative mob positions to a room (seconds).
MOB_SYNC_INTERVAL = 0.05


def _dist_sq(a, b) -> float:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


class GameServer:
    def __init__(self, on_status: Callable[[str], None] | None = None) -> None:
        self._log = on_status or (lambda _msg: None)

        # Identity maps. A Connection is the network handle; PlayerInfo is the
        # game handle. We keep both directions plus the id-keyed dicts the rest
        # of the game logic expects.
        self._players_by_connection: dict[Connection, PlayerInfo] = {}
        self._connection_by_player_id: dict[int, Connection] = {}

        self.players: dict[int, PlayerInfo] = {}  # player_id : PlayerInfo
        self.room_list: dict[int, Room] = {}  # room_id   : Room
        self.mobs: dict[int, Any] = {}

        self._next_player_id = 0
        self._next_room_id = 0
        self._next_mob_id = 0  # server-global so mob ids never collide across rooms
        self._lock = threading.Lock()

        self._server: BaseServer | None = None

        # Command -> handler. Adding a message means adding a _cmd_* method and one
        # line here; _on_message itself never grows. Every handler takes the same
        # (player, value, connection) so dispatch stays uniform.
        self._handlers = {
            Command.SET_PLAYER: self._cmd_set_player,
            Command.JOIN_ROOM: self._cmd_join_room,
            Command.CREATE_ROOM: self._cmd_create_room,
            Command.LEAVE_ROOM: self._cmd_leave_room,
            Command.GET_READY: self._cmd_get_ready,
            Command.GET_UNREADY: self._cmd_get_unready,
            Command.JOIN_GAME: self._cmd_join_game,
            Command.START_GAME: self._cmd_start_game,
            Command.SHOOT: self._cmd_shoot,
            Command.UPDATE_PLAYER: self._cmd_update_player,
            Command.HIT_MOB: self._cmd_hit_mob,
            Command.DISCONNECT: self._cmd_disconnect,
        }

    def serve(self, address) -> None:
        """Build the transport, point its callbacks at us, and run. Blocking."""
        self._server = BaseServer(
            on_connect=self._on_connect,
            on_message=self._on_message,
            on_disconnect=self._on_disconnect,
            on_status=self._log,
            protocol=make_protocol(),
        )
        self._server.start(address)

    def close(self) -> None:
        if self._server:
            self._server.close()

    @property
    def is_running(self) -> bool:
        return self._server is not None and self._server.is_running

    def broadcast(self, command: str, value: Any = None) -> None:
        """Send a message to every connected player (used by the admin console)."""
        self._send(list(self.players.values()), command, value)

    def _send(
        self,
        players: PlayerInfo | Iterable[PlayerInfo],
        command: str,
        value: Any = None,
        exclude: Iterable[PlayerInfo] = (),
    ) -> None:
        """Send one message to one or many players, addressed by PlayerInfo.

        Accepts a single player or any iterable (including a Room), and resolves
        each to its Connection.
        """
        if isinstance(players, PlayerInfo):
            players = [players]

        excluded_ids = {p.id for p in exclude}
        message = {"command": command, "value": value}

        for player in list(players):
            if player.id in excluded_ids:
                continue
            connection = self._connection_by_player_id.get(player.id)
            if connection:
                connection.send(message)

    def _broadcast_player_count(self) -> None:
        self._send(
            list(self.players.values()), Command.SET_PLAYER_COUNT, len(self.players)
        )

    def _on_connect(self, connection: Connection) -> None:
        with self._lock:
            self._next_player_id += 1
            player_id = self._next_player_id
            player = PlayerInfo(player_id, connection.address)

            self.players[player_id] = player
            self._players_by_connection[connection] = player
            self._connection_by_player_id[player_id] = connection

        self._log(f"{player.IP}:{player.PORT} connected as player {player_id}.")
        self._log(f"Player count is now {len(self.players)}.")

        self._broadcast_player_count()
        self._send(player, Command.UPDATE_ROOM, player)

    def _on_disconnect(self, connection: Connection) -> None:
        with self._lock:
            player = self._players_by_connection.pop(connection, None)
            if player is None:
                return
            self._connection_by_player_id.pop(player.id, None)
            self.players.pop(player.id, None)

        if player.room:
            self.leave_room(player)

        self._send(list(self.players.values()), Command.DISCONNECT, player.id)
        self._broadcast_player_count()
        self._log(f"{player.name} ({player.IP}) disconnected.")
        self._log(f"Player count is now {len(self.players)}.")

    def _on_message(self, connection: Connection, message: Any) -> None:
        player = self._players_by_connection.get(connection)
        if player is None:
            return

        command = message.get("command")
        value = message.get("value")

        handler = self._handlers.get(command)
        if handler is None:
            self._log(f"Unknown command from {player.name}: {command!r}")
            return
        handler(player, value, connection)

    # Command handlers. All share the (player, value, connection) signature so
    # _on_message can dispatch them uniformly; each ignores the args it doesn't need.

    def _cmd_set_player(self, player: PlayerInfo, value, _connection) -> None:
        player_name, character_name = value
        player.set_name(player_name)
        player.set_character_name(character_name)
        self._log(f"{player.name} ({player.id}) entered the lobby.")

    def _cmd_join_room(self, player: PlayerInfo, value, _connection) -> None:
        self._join_room(player, value)

    def _cmd_create_room(self, player: PlayerInfo, value, _connection) -> None:
        self.create_room(*value)
        player.join_room(self.room_list[self._next_room_id], True)
        self._send(player, Command.UPDATE_ROOM, player)
        self._log(f"{player.name} ({player.id}) created room {self._next_room_id}.")

    def _cmd_leave_room(self, player: PlayerInfo, _value, _connection) -> None:
        self.leave_room(player)

    def _cmd_get_ready(self, player: PlayerInfo, _value, _connection) -> None:
        player.is_ready = True
        self._update_room_mates(player)

    def _cmd_get_unready(self, player: PlayerInfo, _value, _connection) -> None:
        player.is_ready = False
        self._update_room_mates(player)

    def _cmd_start_game(self, player: PlayerInfo, _value, _connection) -> None:
        room = player.room
        if room is None:
            return
        room.started = True  # lets late joiners drop straight in (see _cmd_join_game)
        self._send(room, Command.START_GAME)
        threading.Thread(target=self.handle_room, args=(room,), daemon=True).start()

    def _cmd_join_game(self, player: PlayerInfo, _value, _connection) -> None:
        # "Join Game" button. If the match is already running, drop this player in:
        # START_GAME builds their scene, then one SPAWN per live mob seeds the mobs
        # they missed (ongoing UPDATE_MOBS / UPDATE_PLAYER keep them in sync from
        # there). If it hasn't started, just ready up and wait for the ruler.
        room = player.room
        if room is None:
            return
        if room.started:
            self._send(player, Command.START_GAME)
            for mob in self._room_mobs(room):
                self._send(player, Command.SPAWN, mob)
        else:
            player.is_ready = True
            self._update_room_mates(player)

    def _cmd_shoot(self, player: PlayerInfo, value, _connection) -> None:
        self._send(player.room, Command.SHOOT, value)

    def _cmd_update_player(self, player: PlayerInfo, value, _connection) -> None:
        # [id, position, angle, alive]; track position/alive so mobs chase only
        # living players, then relay to room mates unchanged.
        player.position = value[1]
        player.alive = value[3] if len(value) > 3 else True
        self._send(player.room, Command.UPDATE_PLAYER, value)

    def _cmd_hit_mob(self, _player: PlayerInfo, value, _connection) -> None:
        # The server owns mob HP: apply the reported damage, and if the mob dies,
        # drop it from the sim and tell the room so every client removes it.
        #
        # HIT_MOB arrives on a per-connection thread, so two clients reporting hits
        # on the same mob run this concurrently. Without the lock the read-modify-
        # write on mob.hp drops a hit (the mob shrugs off damage it took) and both
        # can `del` the same id. Guard the lookup+mutate+remove; the mob dict is
        # also mutated/iterated by the sim thread (spawn_mob / _room_mobs), all
        # under the same lock. Send KILL_MOB outside the lock to avoid holding it
        # across the network.
        mob_id, damage = value
        killed = False
        with self._lock:
            mob = self.mobs.get(mob_id)
            if mob is None:
                return  # already dead (another bullet got it, or a stale report)
            mob.hp -= damage
            if mob.hp <= 0:
                del self.mobs[mob_id]
                killed, room = True, mob.room
        if killed:
            self._send(room, Command.KILL_MOB, mob_id)

    def _cmd_disconnect(
        self, _player: PlayerInfo, _value, connection: Connection
    ) -> None:
        connection.close()  # transport's _handle will run _on_disconnect

    def _join_room(self, player: PlayerInfo, room_id: int) -> None:
        room = self.room_list.get(room_id)
        if room is not None and len(room) < room.size:
            player.join_room(room, False)
            self._log(f"{player.name} ({player.id}) joined room {room_id}.")
            self._update_room_mates(player)
        else:
            self._send(player, Command.UPDATE_ROOM, False)

    def create_room(self, map_name, base_points) -> None:
        # base_points arrives from the client as {base_number: (x, y)}, but JSON
        # turns the int keys into strings and the points into lists. Normalise back
        # so base numbers stay ints (used to index spawn points) and points stay
        # hashable tuples (used in dead-base sets in the mob sim).
        base_points = {
            int(number): tuple(point) for number, point in base_points.items()
        }
        with self._lock:
            self._next_room_id += 1
            room_id = self._next_room_id
        self.room_list[room_id] = Room(room_id, map_name, base_points)

    def leave_room(self, player: PlayerInfo) -> None:
        room = player.room
        if not room:
            return

        player.leave_room()
        self._log(f"{player.name} ({player.IP}) left room {room.id}.")
        self._log(f"Room {room.id} now has {len(room)} players.")

        if len(room) == 0:
            self.room_list.pop(room.id, None)
            self._log(f"Room {room.id} deleted.")
        else:
            room[0].is_ruler = True
            for room_mate in room:
                self._send(room_mate, Command.UPDATE_ROOM, room_mate)

        self._send(player, Command.LEAVE_ROOM, player)

    def _update_room_mates(self, player: PlayerInfo) -> None:
        """Push a fresh !UPDATE_ROOM to everyone sharing the player's room."""
        if player.room:
            for room_mate in player.room:
                self._send(room_mate, Command.UPDATE_ROOM, room_mate)

    def spawn_mob(self, room: Room, mob) -> None:
        # The room numbers its own mobs from 0, which would collide across rooms in
        # the shared self.mobs / id-keyed messages. Reassign a server-global id
        # before storing and sending, so every live mob is uniquely addressable.
        # Locked: the id counter and the dict are also touched by other rooms'
        # sim threads and by HIT_MOB on connection threads.
        with self._lock:
            self._next_mob_id += 1
            mob.id = self._next_mob_id
            self.mobs[mob.id] = mob
        self._send(room, Command.SPAWN, mob)

    def handle_room(self, room: Room) -> None:
        # The server owns mob movement: it spawns, steps every mob toward the
        # nearest player (or its base) while spreading them apart, and pushes
        # positions so every client shows the same enemies. Clients
        # render/interpolate between these snapshots; they don't run mob AI. One
        # tick per broadcast (clients interpolate, so a faster sim buys nothing).
        last = time.time()
        while room.id in self.room_list:
            time.sleep(MOB_SYNC_INTERVAL)
            now = time.time()
            dt, last = now - last, now
            room.update(self.spawn_mob)
            self._simulate_mobs(room, dt)
            self._broadcast_mobs(room)

    def _room_mobs(self, room: Room) -> list:
        # Snapshot under the lock: HIT_MOB can `del` from self.mobs on another
        # thread mid-iteration ("dictionary changed size during iteration").
        with self._lock:
            return [mob for mob in self.mobs.values() if mob.room is room]

    def _simulate_mobs(self, room: Room, dt: float) -> None:
        players = [p for p in room if p.alive]  # dead players stop attracting mobs
        alive_bases = [p.base_point for p in players]  # ...and so do their bases
        dead_bases = {p.base_point for p in room if not p.alive}
        mobs = self._room_mobs(room)

        # Separation: each mob is pushed away from neighbours within AVOID_RADIUS
        # so they don't stack. Computed pairwise from this tick's positions (apply
        # each push to both mobs) before anyone moves.
        sep_x = [0.0] * len(mobs)
        sep_y = [0.0] * len(mobs)
        avoid_sq = AVOID_RADIUS * AVOID_RADIUS
        for i in range(len(mobs)):
            ax, ay = mobs[i].position
            for j in range(i + 1, len(mobs)):
                dx, dy = ax - mobs[j].position[0], ay - mobs[j].position[1]
                dist_sq = dx * dx + dy * dy
                if 0 < dist_sq < avoid_sq:
                    inv = 1.0 / math.sqrt(dist_sq)
                    ux, uy = dx * inv, dy * inv
                    sep_x[i] += ux
                    sep_y[i] += uy
                    sep_x[j] -= ux
                    sep_y[j] -= uy

        for i, mob in enumerate(mobs):
            if players:
                nearest = min(players, key=lambda p: _dist_sq(p.position, mob.position))
                if _dist_sq(nearest.position, mob.position) < RANGE_RADIUS**2:
                    target = nearest.position  # in range: chase the player
                elif mob.target_base in dead_bases:
                    # Its base's owner is down: peel off to the nearest living base
                    # instead of piling onto a corpse.
                    target = min(alive_bases, key=lambda b: _dist_sq(b, mob.position))
                else:
                    target = mob.target_base  # keep defending its assigned base
            else:
                target = mob.target_base  # everyone down: fall back to spawn base

            # Unit chase direction (none once basically on target), blended with
            # the separation push, then renormalised so speed stays constant.
            cx, cy = target[0] - mob.position[0], target[1] - mob.position[1]
            chase = math.hypot(cx, cy)
            if chase > 1:
                cx, cy = cx / chase, cy / chase
            else:
                cx = cy = 0.0

            dir_x = cx + MOB_SEPARATION * sep_x[i]
            dir_y = cy + MOB_SEPARATION * sep_y[i]
            length = math.hypot(dir_x, dir_y)
            if length > 1e-6:
                # speed is px per 60fps-frame on the client; convert to px/second.
                step = MOB_SPEEDS[mob.id % len(MOB_SPEEDS)] * 60 * dt
                mob.position = (
                    mob.position[0] + dir_x / length * step,
                    mob.position[1] + dir_y / length * step,
                )

    def _broadcast_mobs(self, room: Room) -> None:
        mobs = [(mob.id, mob.position, mob.hp) for mob in self._room_mobs(room)]
        if mobs:
            self._send(room, Command.UPDATE_MOBS, mobs)
