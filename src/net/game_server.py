"""Game/lobby logic for the server, with no sockets in sight.

This is Layer 2: it owns players, rooms, and mobs, and it interprets the game
protocol (!JOIN_ROOM, !SHOOT, ...). It talks to the network only through a
BaseServer (Layer 1) via callbacks, and it never imports tkinter (Layer 3
subscribes to `on_status` if it wants a log).

Compared with the old net/server.py, everything to do with recv_all, struct,
pickle, accept loops, and per-client threads has moved down into the transport.
What is left here is purely "what should happen when a client says X".

Serialization note: this wires up with PickleCodec so it stays drop-in
compatible with the current client (which receives whole PlayerInfo / Room /
MobInfo objects). To move to JSON later, give those classes to_dict/from_dict
and swap the codec in `serve()` — nothing in this file changes.
"""

import threading
import time
from typing import Any, Callable, Iterable

from net.player_info import PlayerInfo
from net.room import Room
from net.protocol import Protocol, PickleCodec
from net.transport import BaseServer, Connection


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
        self._lock = threading.Lock()

        self._server: BaseServer | None = None

    # region wiring -----------------------------------------------------------

    def serve(self, address) -> None:
        """Build the transport, point its callbacks at us, and run. Blocking."""
        self._server = BaseServer(
            on_connect=self._on_connect,
            on_message=self._on_message,
            on_disconnect=self._on_disconnect,
            on_status=self._log,
            protocol=Protocol(PickleCodec()),
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

    # endregion

    # region sending ----------------------------------------------------------

    def _send(
        self,
        players: PlayerInfo | Iterable[PlayerInfo],
        command: str,
        value: Any = None,
        exclude: Iterable[PlayerInfo] = (),
    ) -> None:
        """Send one message to one or many players, addressed by PlayerInfo.

        Mirrors the old send_data: accepts a single player or any iterable
        (including a Room), and resolves each to its Connection.
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
        self._send(list(self.players.values()), "!SET_PLAYER_COUNT", len(self.players))

    # endregion

    # region connection lifecycle --------------------------------------------

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
        self._send(player, "!UPDATE_ROOM", player)

    def _on_disconnect(self, connection: Connection) -> None:
        with self._lock:
            player = self._players_by_connection.pop(connection, None)
            if player is None:
                return
            self._connection_by_player_id.pop(player.id, None)
            self.players.pop(player.id, None)

        if player.room:
            self.leave_room(player)

        self._send(list(self.players.values()), "!DISCONNECT", player.id)
        self._broadcast_player_count()
        self._log(f"{player.name} ({player.IP}) disconnected.")
        self._log(f"Player count is now {len(self.players)}.")

    # endregion

    # region command dispatch -------------------------------------------------

    def _on_message(self, connection: Connection, message: Any) -> None:
        player = self._players_by_connection.get(connection)
        if player is None:
            return

        command = message.get("command")
        value = message.get("value")

        if command == "!SET_PLAYER":
            player_name, character_name = value
            player.set_name(player_name)
            player.set_character_name(character_name)
            self._log(f"{player.name} ({player.id}) entered the lobby.")

        elif command == "!JOIN_ROOM":
            self._join_room(player, value)

        elif command == "!CREATE_ROOM":
            self.create_room(*value)
            player.join_room(self.room_list[self._next_room_id], True)
            self._send(player, "!UPDATE_ROOM", player)
            self._log(f"{player.name} ({player.id}) created room {self._next_room_id}.")

        elif command == "!LEAVE_ROOM":
            self.leave_room(player)

        elif command == "!GET_READY":
            player.is_ready = True
            self._update_room_mates(player)

        elif command == "!GET_UNREADY":
            player.is_ready = False
            self._update_room_mates(player)

        elif command == "!START_GAME":
            self._send(player.room, command)
            threading.Thread(
                target=self.handle_room, args=(player.room,), daemon=True
            ).start()

        elif command == "!SHOOT":
            self._send(player.room, command, value)

        elif command == "!UPDATE_PLAYER":
            self._send(player.room, command, value, exclude=())

        elif command == "!DISCONNECT":
            connection.close()  # transport's _handle will run _on_disconnect

        else:
            self._log(f"Unknown command from {player.name}: {command!r}")

    # endregion

    # region room logic -------------------------------------------------------

    def _join_room(self, player: PlayerInfo, room_id: int) -> None:
        room = self.room_list.get(room_id)
        if room is not None and len(room) < room.size:
            player.join_room(room, False)
            self._log(f"{player.name} ({player.id}) joined room {room_id}.")
            self._update_room_mates(player)
        else:
            self._send(player, "!UPDATE_ROOM", False)

    def create_room(self, map_name, base_points) -> None:
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
                self._send(room_mate, "!UPDATE_ROOM", room_mate)

        self._send(player, "!LEAVE_ROOM", player)

    def _update_room_mates(self, player: PlayerInfo) -> None:
        """Push a fresh !UPDATE_ROOM to everyone sharing the player's room."""
        if player.room:
            for room_mate in player.room:
                self._send(room_mate, "!UPDATE_ROOM", room_mate)

    # endregion

    # region mob spawning -----------------------------------------------------

    def spawn_mob(self, room: Room, mob) -> None:
        self.mobs[mob.id] = mob
        self._send(room, "!SPAWN", mob)

    def handle_room(self, room: Room) -> None:
        while room.id in self.room_list:
            room.update(self.spawn_mob)
            time.sleep(0.01)

    # endregion
