"""The one place that says how Standoff talks over the wire.

Server, client, and the e2e tests all build their Protocol from here, so the
codec and the set of types it knows how to round-trip can never drift between the
two ends (a mismatch is the classic "everything connects but nothing decodes"
bug). JSON + to_dict/from_dict replaces pickle: a peer can send us bad data, but
never code that runs in our process.
"""

from net.player_info import PlayerInfo, MobInfo
from net.room import Room
from pygame_core.net.protocol import Protocol, TypedJSONCodec

# Type tag (the "__type__" each to_dict writes) -> class. Both ends must agree.
WIRE_TYPES = {
    "PlayerInfo": PlayerInfo,
    "Room": Room,
    "MobInfo": MobInfo,
}


def make_protocol() -> Protocol:
    """A Protocol wired with the shared JSON codec. Use this on both ends."""
    return Protocol(TypedJSONCodec(WIRE_TYPES))
