"""
Smoke test for the unified ``net.network.Network`` class (copied from the
zombie-survivors prototype). Run from the project root:

    python tests/test_network.py

This spins up a host and a client on the local machine and checks that a TCP
connection is established and the server registers the client. It needs no
display, so it runs headless.

NOTE: the Network class is copied verbatim and is known to have rough edges
(see the findings printed at the end). The intent is to test/iterate on it
here before refactoring, not to ship it as-is.
"""

import os
import sys
import time
import socket
from pathlib import Path

# Mirror __main__.py so `net`/`util`/`pygame_core` imports resolve.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "pygame_core"))
# util.constants imports pygame; make sure it never needs a real display.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from net.network import Network  # noqa: E402


def wait_until(predicate, timeout=3.0, interval=0.05):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


def main() -> int:
    failures = []

    received = []
    host = Network(lambda data: received.append(("host", data)))
    client = Network(lambda data: received.append(("client", data)))

    # 1. host starts (bind + listen).
    if host.host() == 1 and host.is_connected:
        print("PASS: host started (bound + listening)")
    else:
        failures.append("host failed to start")
        print("FAIL: host failed to start")
        print(host.status)
        return 1  # nothing else can run

    # 2. Client connects.
    local_ip = socket.gethostbyname(socket.gethostname())
    if client.connect(local_ip) == 1:
        print("PASS: client connect() reported success")
    else:
        failures.append("client failed to connect")
        print("FAIL: client failed to connect")
        print(client.status)

    # 3. Server-side accept registers the client (host=player 0, client=player 1).
    if wait_until(lambda: len(host.players) >= 2):
        print(f"PASS: server registered the client (players={host.players})")
    else:
        failures.append("server did not register the connecting client")
        print(f"FAIL: server did not register the client (players={host.players})")

    # 4. (Informational) client receive loop. Exposes a known bug: connect()
    #    never sets client.is_connected = True, so __recieve_from_server exits
    #    immediately and the client never reads the server's !SET_PLAYER.
    got_client_data = wait_until(
        lambda: any(side == "client" for side, _ in received), timeout=1.0
    )
    if got_client_data:
        print("INFO: client received server data:",
              [d for s, d in received if s == "client"])
    else:
        print("WARN: client received nothing - connect() does not set "
              "is_connected=True, so the client receive thread never runs.")

    # Cleanup.
    try:
        client.close()
    except Exception:
        pass
    try:
        host.close()
    except Exception:
        pass

    print()
    if failures:
        print(f"RESULT: {len(failures)} check(s) failed: {failures}")
        return 1
    print("RESULT: connection smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
