"""Player input as intent, not device.

Gameplay asks *what the player wants* — which way to move, where to aim, whether
to fire — and a backend decides how to read it. ``KeyboardMouseControls`` reads
the desktop keyboard+mouse (the original Player behaviour, unchanged);
``TouchControls`` will read an on-screen joystick + auto-aim for Android.
Swapping backends never touches Player or the scene — that's the whole point of
this seam, and it's the first step toward the Android (buildozer) port.

Only the *local* player has a Controls; remote players are driven by the network.
"""

from __future__ import annotations

import os

import pygame
from pygame.math import Vector2 as Vec


def is_android() -> bool:
    """True when running under python-for-android (buildozer sets this env var)."""
    return bool(os.environ.get("ANDROID_ARGUMENT"))


def make_controls(*, size, assets, get_keys, get_mouse_pos):
    """Pick the input backend for this device.

    Touch on Android, or on desktop when STANDOFF_TOUCH is set so the on-screen
    controls can be play-tested with the mouse before there's a phone in hand.
    """
    if is_android() or os.environ.get("STANDOFF_TOUCH"):
        return TouchControls(size, assets)
    return KeyboardMouseControls(get_keys, get_mouse_pos)


class Controls:
    """Interface the local Player reads each frame. One instance per session.

    The defaults are inert (no movement, keep facing, never fire) so a partial
    backend is still safe to plug in.
    """

    def movement(self) -> Vec:
        """Unit movement direction in screen space, or a zero vector when idle."""
        return Vec()

    def aim_angle(self, player, camera) -> float:
        """Angle in degrees (measured from +x) the player should face."""
        return player.angle

    def is_firing(self) -> bool:
        """Whether the fire control is held this frame."""
        return False

    def handle_event(self, event) -> None:
        """Feed a raw pygame event (button edges on desktop, finger lifts on
        touch). Polled state (movement/aim/firing) is read separately each frame.
        """

    def draw(self, window) -> None:
        """Draw any on-screen controls (HUD). No-op for physical devices."""


class KeyboardMouseControls(Controls):
    """Desktop backend: WASD/arrows to move, mouse to aim, left button to fire.

    Reads live device state through two callables the scene passes in, so it
    stays decoupled from how the app happens to store keys/mouse. The movement
    and aim maths are lifted verbatim from the old Player methods, so desktop
    feel is unchanged.
    """

    def __init__(self, get_keys, get_mouse_pos) -> None:
        self._get_keys = get_keys
        self._get_mouse_pos = get_mouse_pos
        self._firing = False

    def movement(self) -> Vec:
        keys = self._get_keys()
        move = Vec()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            move.x = -1
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            move.x = 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            move.y = -1
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            move.y = 1
        if move.length_squared():
            move.normalize_ip()  # diagonals stay unit length, not ~41% faster
        return move

    def aim_angle(self, player, camera) -> float:
        # Angle between the player->cursor vector and the x axis, in screen space.
        mouse = Vec(self._get_mouse_pos())
        center = Vec(camera.apply(player.rect).center)
        return (mouse - center).angle_to(Vec(1, 0))

    def is_firing(self) -> bool:
        return self._firing

    def handle_event(self, event) -> None:
        # Fire is a held state edged by the left mouse button.
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._firing = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._firing = False


class TouchControls(Controls):
    """Android backend: a left-thumb virtual joystick, auto-aim, and a fire button.

    Movement is analog (push further = move faster). Aim is automatic — the
    player faces the nearest mob — so the only buttons needed are "move" and
    "fire", which suits a twin-corner phone layout. Multi-touch is tracked by
    finger id so moving and firing at once works; the mouse is accepted too
    (one "finger") so the HUD can be exercised on desktop via STANDOFF_TOUCH.

    All geometry is in the game's logical (SCALED) coordinates, the same space
    the scene draws in, so finger positions and sprite blits line up.
    """

    _DEAD_ZONE = 0.15  # fraction of the base radius ignored, to stop drift

    def __init__(self, size, assets) -> None:
        self._w, self._h = size

        base_r = int(self._h * 0.16)
        knob_r = int(base_r * 0.5)
        fire_r = int(self._h * 0.11)
        margin = int(self._h * 0.05)

        self._base_img = self._fit(assets.get_image("touch_joystick_base"), base_r, 190)
        # Lighten the knob so it reads against the same-coloured base.
        knob = assets.get_image("touch_joystick_knob").copy()
        knob.fill((45, 45, 55, 0), special_flags=pygame.BLEND_RGB_ADD)
        self._knob_img = self._fit(knob, knob_r, 230)
        self._fire_img = self._fit(assets.get_image("touch_fire_button"), fire_r, 190)
        self._fire_img_pressed = self._fire_img.copy()
        self._fire_img_pressed.fill((70, 30, 30, 0), special_flags=pygame.BLEND_RGB_ADD)

        self._base_r = base_r
        self._base_center = Vec(margin + base_r, self._h - margin - base_r)
        self._fire_r = fire_r
        self._fire_center = Vec(self._w - margin - fire_r, self._h - margin - fire_r)

        self._move = Vec()
        self._knob_offset = Vec()  # knob pixel offset from base centre, for drawing
        self._firing = False
        self._move_finger = None  # finger id currently driving the stick
        self._fire_finger = None  # finger id currently holding fire

    @staticmethod
    def _fit(surface, radius, opacity):
        """Scale a sprite to a diameter and apply an overall opacity (so the HUD
        sits lightly over the game). BLEND_RGBA_MULT scales the per-pixel alpha,
        which set_alpha can't do on a per-pixel surface."""
        img = pygame.transform.smoothscale(surface, (radius * 2, radius * 2))
        img.fill((255, 255, 255, opacity), special_flags=pygame.BLEND_RGBA_MULT)
        return img

    # --- intent the Player reads ---

    def movement(self) -> Vec:
        return Vec(self._move)

    def aim_angle(self, player, camera) -> float:
        # Auto-aim: face the nearest mob (camera is translation-only, so world
        # and screen directions share the same angle). No mobs -> hold facing.
        mobs = getattr(player.world, "mobs", None)
        if mobs:
            nearest = min(
                mobs, key=lambda m: (Vec(m.position) - player.position).length_squared()
            )
            return (Vec(nearest.position) - player.position).angle_to(Vec(1, 0))
        return player.angle

    def is_firing(self) -> bool:
        return self._firing

    # --- input ---

    def handle_event(self, event) -> None:
        if event.type == pygame.FINGERDOWN:
            self._press(event.finger_id, self._finger_pos(event))
        elif event.type == pygame.FINGERMOTION:
            self._drag(event.finger_id, self._finger_pos(event))
        elif event.type == pygame.FINGERUP:
            self._release(event.finger_id)
        # Mouse mirror, for desktop play-testing only.
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._press("mouse", Vec(event.pos))
        elif event.type == pygame.MOUSEMOTION and event.buttons[0]:
            self._drag("mouse", Vec(event.pos))
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._release("mouse")

    def _finger_pos(self, event) -> Vec:
        # FINGER* events are normalised [0, 1] over the window; map to logical px.
        return Vec(event.x * self._w, event.y * self._h)

    def _press(self, finger, pos: Vec) -> None:
        if pos.distance_to(self._fire_center) <= self._fire_r:
            self._fire_finger = finger
            self._firing = True
        elif pos.x < self._w * 0.55:  # left side claims the stick
            self._move_finger = finger
            self._update_move(pos)

    def _drag(self, finger, pos: Vec) -> None:
        if finger == self._move_finger:
            self._update_move(pos)

    def _release(self, finger) -> None:
        if finger == self._move_finger:
            self._move_finger = None
            self._move = Vec()
            self._knob_offset = Vec()
        if finger == self._fire_finger:
            self._fire_finger = None
            self._firing = False

    def _update_move(self, pos: Vec) -> None:
        offset = pos - self._base_center
        if offset.length() > self._base_r:
            offset.scale_to_length(self._base_r)
        self._knob_offset = offset
        analog = offset / self._base_r
        self._move = Vec() if analog.length() < self._DEAD_ZONE else analog

    # --- HUD ---

    def draw(self, window) -> None:
        window.blit(self._base_img, self._base_img.get_rect(center=self._base_center))
        knob_center = self._base_center + self._knob_offset
        window.blit(self._knob_img, self._knob_img.get_rect(center=knob_center))
        fire = self._fire_img_pressed if self._firing else self._fire_img
        window.blit(fire, fire.get_rect(center=self._fire_center))
