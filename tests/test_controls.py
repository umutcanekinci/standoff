"""Unit tests for gameplay.controls: the device-input backends.

The touch backend is the newest and most logic-dense client code (the Android
port), and it's pure enough to drive with synthetic pygame events — no phone,
no display. Pins: backend selection, the analog stick (dead zone + radius clamp),
multi-touch move/fire independence, the fire hit-test, and auto-aim.
"""

import pygame
from pygame.math import Vector2 as Vec

from gameplay.controls import (
    Controls,
    KeyboardMouseControls,
    TouchControls,
    make_controls,
)


# --- fakes -------------------------------------------------------------------


class _FakeAssets:
    """get_image returns a fresh translucent surface the HUD can scale/blend."""

    def get_image(self, _name):
        return pygame.Surface((64, 64), pygame.SRCALPHA)


class _Keys(dict):
    """Key-state mapping: unset keys read False, like pygame's key state."""

    def __missing__(self, _key):
        return False


class _Mob:
    def __init__(self, position):
        self.position = position


class _World:
    def __init__(self, mobs):
        self.mobs = mobs


class _Player:
    def __init__(self, position, angle, mobs=None, rect=None):
        self.position = Vec(position)
        self.angle = angle
        self.world = _World(mobs if mobs is not None else [])
        self.rect = rect


SIZE = (800, 600)


def _touch():
    return TouchControls(SIZE, _FakeAssets())


# --- make_controls selection -------------------------------------------------


def test_make_controls_defaults_to_keyboard_mouse(monkeypatch):
    monkeypatch.delenv("ANDROID_ARGUMENT", raising=False)
    monkeypatch.delenv("STANDOFF_TOUCH", raising=False)
    controls = make_controls(
        size=SIZE, assets=_FakeAssets(), get_keys=_Keys, get_mouse_pos=lambda: (0, 0)
    )
    assert isinstance(controls, KeyboardMouseControls)


def test_make_controls_picks_touch_when_forced(monkeypatch):
    monkeypatch.delenv("ANDROID_ARGUMENT", raising=False)
    monkeypatch.setenv("STANDOFF_TOUCH", "1")
    controls = make_controls(
        size=SIZE, assets=_FakeAssets(), get_keys=_Keys, get_mouse_pos=lambda: (0, 0)
    )
    assert isinstance(controls, TouchControls)


def test_make_controls_picks_touch_on_android(monkeypatch):
    monkeypatch.setenv("ANDROID_ARGUMENT", "anything")
    controls = make_controls(
        size=SIZE, assets=_FakeAssets(), get_keys=_Keys, get_mouse_pos=lambda: (0, 0)
    )
    assert isinstance(controls, TouchControls)


# --- Controls base is inert --------------------------------------------------


def test_base_controls_are_inert():
    """A partial backend is safe to plug in: no move, hold facing, never fire."""
    base = Controls()
    assert base.movement() == Vec()
    assert base.is_firing() is False
    player = _Player((0, 0), angle=42)
    assert base.aim_angle(player, camera=None) == 42


# --- TouchControls: analog stick ---------------------------------------------


def test_touch_stick_dead_zone_reads_as_no_movement():
    """A tiny nudge inside the dead zone must not drift the player."""
    tc = _touch()
    # base centre = (margin+base_r, h-margin-base_r) = (126, 474), base_r = 96.
    # Offset of 10px -> 10/96 = 0.10 < 0.15 dead zone.
    tc._press("f", Vec(126 + 10, 474))
    assert tc.movement() == Vec()


def test_touch_stick_just_past_dead_zone_moves():
    tc = _touch()
    tc._press("f", Vec(126 + 20, 474))  # 20/96 = 0.208 > 0.15
    move = tc.movement()
    assert move.x > 0 and move.y == 0
    assert move.length() < 1.0  # analog, not full tilt


def test_touch_stick_clamps_to_unit_at_full_tilt():
    """Pushing past the base radius saturates at a unit vector. Stays on the left
    half (x < 0.55*w = 440) so the press claims the stick, not nothing."""
    tc = _touch()
    tc._press("f", Vec(326, 474))  # offset (200, 0), well past base_r = 96
    assert tc.movement() == Vec(1, 0)


def test_touch_release_recentres_stick():
    tc = _touch()
    tc._press("f", Vec(326, 474))
    assert tc.movement() != Vec()
    tc._release("f")
    assert tc.movement() == Vec()


# --- TouchControls: fire + multitouch ----------------------------------------


def test_touch_fire_button_press_and_release():
    tc = _touch()
    # fire centre = (w-margin-fire_r, h-margin-fire_r) = (704, 504), fire_r = 66.
    tc._press("f", Vec(704, 504))
    assert tc.is_firing() is True
    tc._release("f")
    assert tc.is_firing() is False


def test_touch_move_and_fire_are_independent_fingers():
    """One finger drives the stick, another holds fire; releasing fire keeps the
    stick, and vice versa."""
    tc = _touch()
    tc._press("move", Vec(326, 474))  # left side -> stick
    tc._press("fire", Vec(704, 504))  # fire button
    assert tc.movement() == Vec(1, 0) and tc.is_firing() is True

    tc._release("fire")
    assert tc.is_firing() is False
    assert tc.movement() == Vec(1, 0)  # stick unaffected

    tc._release("move")
    assert tc.movement() == Vec()


def test_touch_finger_dispatch_via_events():
    """handle_event maps normalised FINGER coords to the logical HUD layout."""
    tc = _touch()
    # Normalise the fire centre (704, 504) over the 800x600 window.
    down = pygame.event.Event(pygame.FINGERDOWN, finger_id=1, x=704 / 800, y=504 / 600)
    tc.handle_event(down)
    assert tc.is_firing() is True
    tc.handle_event(pygame.event.Event(pygame.FINGERUP, finger_id=1, x=0, y=0))
    assert tc.is_firing() is False


# --- TouchControls: auto-aim -------------------------------------------------


def test_touch_aim_faces_nearest_mob():
    tc = _touch()
    player = _Player((0, 0), angle=999, mobs=[_Mob((10, 0)), _Mob((0, 100))])
    # Nearest is (10, 0): straight along +x -> 0 degrees.
    assert tc.aim_angle(player, camera=None) == 0


def test_touch_aim_holds_facing_without_mobs():
    tc = _touch()
    player = _Player((0, 0), angle=123, mobs=[])
    assert tc.aim_angle(player, camera=None) == 123


# --- KeyboardMouseControls ---------------------------------------------------


def test_keyboard_movement_is_unit_and_normalised():
    keys = _Keys()
    kbm = KeyboardMouseControls(lambda: keys, lambda: (0, 0))

    assert kbm.movement() == Vec()  # nothing held

    keys[pygame.K_d] = True
    assert kbm.movement() == Vec(1, 0)

    keys[pygame.K_w] = True  # diagonal stays unit length, not ~1.41
    diag = kbm.movement()
    assert diag.x > 0 and diag.y < 0
    assert abs(diag.length() - 1.0) < 1e-6


def test_keyboard_fire_is_edged_by_left_button():
    kbm = KeyboardMouseControls(_Keys, lambda: (0, 0))
    assert kbm.is_firing() is False

    kbm.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0)))
    assert kbm.is_firing() is True

    kbm.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(0, 0)))
    assert kbm.is_firing() is False


def test_keyboard_aim_points_from_player_to_cursor():
    rect = pygame.Rect(0, 0, 10, 10)
    rect.center = (100, 100)
    player = _Player((100, 100), angle=0, rect=rect)

    class _Camera:
        def apply(self, r):
            return r  # identity: screen == world here

    kbm = KeyboardMouseControls(_Keys, lambda: (200, 100))  # cursor due +x
    assert kbm.aim_angle(player, _Camera()) == 0
