"""Base class for the game's top-level states (lobby vs. in-world play).

A Scene owns one phase of the game and answers the three loop calls the
Application drives every frame: handle_event, update, draw. Game holds the
active Scene and forwards to it, so the old ``if is_game_started: ... else: ...``
forks in Game.update/draw/handle_event collapse into "ask the active scene."

Scenes read shared session state (the network client, the local PlayerInfo,
the online/offline mode, the window) from the Game passed in at construction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pygame

    from app.game import Game


class Scene:
    def __init__(self, game: "Game") -> None:
        self.game = game

    def on_enter(self) -> None:
        """Called when this scene becomes active. Override if needed."""

    def on_exit(self) -> None:
        """Called when this scene stops being active. Override if needed."""

    def handle_event(self, _event: "pygame.event.Event") -> None:
        """Handle one input event. Called once per event while active."""

    def update(self) -> None:
        """Advance state by one frame. Called once per frame while active."""

    def draw(self) -> None:
        """Render to ``self.game.window``. Called once per frame while active."""
