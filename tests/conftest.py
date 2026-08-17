"""Shared pytest setup and fixtures for the test suite."""

import os
import socket
import sys

# Room.__init__ calls pygame.init(); the dummy SDL video driver lets that run
# headless (e.g. in CI) without opening a real window. Must be set before pygame
# is imported anywhere.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

# Make the helper module in this directory importable as `import _util`.
sys.path.insert(0, os.path.dirname(__file__))

import pygame
import pytest

from pygamine import AssetManager

pygame.init()
# Entity/Player/Mob load images via convert_alpha(), which raises without a
# display surface. GameplayScene normally provides one; these tests construct
# game objects directly, with no Scene/Game involved, so they need their own.
pygame.display.set_mode((1, 1))


@pytest.fixture(scope="session")
def assets() -> AssetManager:
    manager = AssetManager()
    manager.load_manifest("config/assets.yaml")
    missing = manager.validate()
    assert not missing, f"Missing assets: {missing}"
    return manager


@pytest.fixture
def free_port() -> int:
    """A currently-free TCP port on loopback.

    We bind to port 0 (OS picks a free one), read it back, then release it so
    the test's server can bind it. Using ephemeral ports means tests never
    collide and there is no hardcoded port to clash with a running game.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port
