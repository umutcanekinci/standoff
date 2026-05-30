"""Test doubles and helpers shared across the suite.

The two fakes here are the heart of the unit layer: they let us test logic at
the socket boundary (Protocol) and at the game-logic boundary (GameServer)
without ever opening a real socket.
"""

import socket
import threading
import time


class FakeSocket:
    """A stand-in for a TCP socket.

    `recv` hands back the queued bytes in `chunk`-sized pieces, which lets us
    reproduce TCP fragmentation (the exact condition the old network.py's
    single-recv code got wrong). `sendall` just records what was written.
    """

    def __init__(self, data: bytes = b"", chunk: int = 4096) -> None:
        self._recv_data = bytearray(data)
        self._chunk = chunk
        self.sent = bytearray()

    def recv(self, n: int) -> bytes:
        take = min(n, self._chunk, len(self._recv_data))
        chunk = bytes(self._recv_data[:take])
        del self._recv_data[:take]
        return chunk

    def sendall(self, data: bytes) -> None:
        self.sent.extend(data)


class FakeConnection:
    """A stand-in for net.transport.Connection for GameServer unit tests.

    Records every message GameServer tries to send, so a test can assert on the
    protocol-level behaviour ("what would this client receive?") with no sockets.
    """

    def __init__(self, address=("test-host", 0)) -> None:
        self.address = address
        self.is_open = True
        self.sent: list = []

    def send(self, message) -> None:
        self.sent.append(message)

    def close(self) -> None:
        self.is_open = False

    def commands(self) -> list[str]:
        return [m["command"] for m in self.sent]

    def last_with(self, command: str):
        """The most recent message sent with the given command, or None."""
        for message in reversed(self.sent):
            if message["command"] == command:
                return message
        return None


def wait_until(predicate, timeout: float = 2.0, interval: float = 0.01) -> bool:
    """Poll `predicate` until it is true or `timeout` elapses.

    Used to wait for asynchronous state (e.g. a server becoming ready) without a
    blind sleep. Returns the final truthiness so callers can assert on it.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return bool(predicate())


def start_in_thread(target, *args) -> threading.Thread:
    thread = threading.Thread(target=target, args=args, daemon=True)
    thread.start()
    return thread


def connect_raw(port: int) -> socket.socket:
    """A plain client socket connected to loopback `port` (for malformed-input tests)."""
    return socket.create_connection(("127.0.0.1", port), timeout=2)
