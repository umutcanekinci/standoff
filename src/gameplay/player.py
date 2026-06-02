from util.constants import (
    PLAYER_MAX_HP,
    PLAYER_FRICTION,
    REMOTE_SMOOTHING,
    REMOTE_SNAP_DISTANCE,
    SHOOT_RATE,
    GUN_SPREAD,
    BARREL_OFFSET,
    KICKBACK,
    KNOCKBACK_DECAY,
    TILE_WIDTH,
    TILE_HEIGHT,
    PLAYER_HIT_RECT,
)
import pygame
from pygame.math import Vector2 as Vec
from gameplay.bullet import Bullet
from gameplay.entity import Entity
from gameplay.muzzle_flash import MuzzleFlash
from random import uniform


class Player(Entity):
    def __init__(
        self, entity_id, name, name_color, character, position, size, world
    ) -> None:
        super().__init__(
            entity_id,
            name,
            name_color,
            position,
            size,
            world.assets.image_path(f"char_{character}_gun"),
            PLAYER_MAX_HP,
            PLAYER_MAX_HP,
        )

        # Shooting
        self.is_shooting = False
        self.shoot_rate = SHOOT_RATE
        self.last_shoot_time = -1000

        self.character, self.world = character, world
        self.map, self.camera = world.map, world.camera

        # Hit rect for collisions
        self.hit_rect = PLAYER_HIT_RECT.copy()
        self.hit_rect.center = self.rect.center

        # Source of move/aim/fire intent for the LOCAL player; the scene injects a
        # KeyboardMouseControls (desktop) or TouchControls (Android). Remote
        # players leave this None and are driven by the network instead.
        self.controls = None

        self.force = Vec(3, 3)
        self.net_force = Vec()

        self.acceleration = Vec()
        self.max_acceleration = 5

        self.velocity = Vec()
        self.max_speed = 5

        self.force_rotation = Vec()
        self.delta = Vec()
        self.knockback = Vec()
        self.angle = 0

        # Local player is input-driven; remote players follow networked positions.
        # GameplayScene flips is_local on the one it owns. target_position is the
        # latest center received from the owner (see _follow_remote).
        self.is_local = False
        self.target_position = Vec(position)

        self.density = 25
        self.weight = (
            self.rect.width / TILE_WIDTH * self.rect.height / TILE_HEIGHT
        ) * self.density

        # Live vs downed appearance. Keep the colour surface so we can swap back on
        # respawn; the grey one is built lazily the first time this player dies.
        self._color_image = self.original_image
        self._grey_image = None

    @staticmethod
    def _greyscale(surface):
        try:
            return pygame.transform.grayscale(surface)
        except (AttributeError, ValueError, pygame.error):
            faded = surface.copy()  # fallback: darken if grayscale isn't available
            faded.fill((110, 110, 110, 255), special_flags=pygame.BLEND_RGB_MULT)
            return faded

    def set_alive(self, alive: bool) -> None:
        # Drive the alive flag AND the look together, so a downed remote player
        # reads as a grey corpse instead of a still-living sprite. update() rotates
        # from original_image each frame, so swapping it is enough.
        if alive == self.alive:
            return
        self.alive = alive
        if not alive and self._grey_image is None:
            self._grey_image = self._greyscale(self._color_image)
        self.set_image(self._color_image if alive else self._grey_image)

    def aim(self):
        # Face wherever the controls say (mouse cursor on desktop, auto-aim/stick
        # on touch). No controls (a remote player) keeps its networked angle.
        if self.controls:
            self.angle = self.controls.aim_angle(self, self.world.camera)

    def _update_force_rotation(self):
        # Movement intent comes from the controls as a unit (or zero) direction.
        if self.controls:
            self.force_rotation = self.controls.movement()

    def _apply_friction(self):
        # Brake any axis the player isn't actively driving so releasing the keys
        # stops you promptly instead of coasting (drag, not a force). Exponential
        # and scaled by delta_time, so the feel is frame-rate independent.
        damping = PLAYER_FRICTION**self.world.delta_time
        if self.force_rotation.x == 0:
            self.velocity.x *= damping
        if self.force_rotation.y == 0:
            self.velocity.y *= damping

    def _decay_knockback(self):
        # Smooth, decaying knock-back — applied through movement so it eases out
        # and still collides with walls (instead of an instant teleport).
        self.delta += self.knockback
        self.knockback *= KNOCKBACK_DECAY
        if self.knockback.length() < 0.1:
            self.knockback = Vec()

    def update_movement(self):
        self._update_force_rotation()

        self.net_force = self.force.elementwise() * self.force_rotation

        self.acceleration = self.net_force / self.weight
        self.acceleration.x = max(
            -self.max_acceleration, min(self.max_acceleration, self.acceleration.x)
        )
        self.acceleration.y = max(
            -self.max_acceleration, min(self.max_acceleration, self.acceleration.y)
        )

        self.velocity += self.acceleration * self.world.delta_time
        self._apply_friction()  # brake undriven axes (drag on velocity)
        if self.velocity.length() > self.max_speed:
            self.velocity.scale_to_length(self.max_speed)

        if abs(self.velocity.x) < 0.01:
            self.velocity.x = 0
        if abs(self.velocity.y) < 0.01:
            self.velocity.y = 0

        # Semi-implicit Euler: velocity is already advanced, so the step is just
        # velocity * dt (the old 0.5*a*dt**2 term double-counted acceleration).
        self.delta = self.velocity * self.world.delta_time
        self._decay_knockback()

    def apply_knockback(self, direction, distance):
        if direction.length() == 0:
            return
        # Initial impulse sized so the decaying per-frame series sums to ~distance px.
        self.knockback = direction.normalize() * distance * (1 - KNOCKBACK_DECAY)

    def shoot(self):
        now = pygame.time.get_ticks()

        if now - self.last_shoot_time > self.shoot_rate:
            spread = uniform(-GUN_SPREAD, GUN_SPREAD)
            angle = self.angle + spread
            position = Vec(self.rect.center) + BARREL_OFFSET.rotate(-angle)

            Bullet(self, position, angle)
            MuzzleFlash(self.world, position, self.angle)

            self.velocity = Vec(-KICKBACK, 0).rotate(-self.angle)

            self.last_shoot_time = now

    def update(self):
        self.rotate(self.angle)
        if self.is_local:
            super().move(self.delta)  # input-driven, collides with walls
        else:
            self._follow_remote()  # network-driven, eased toward owner's position

    def _follow_remote(self):
        # Ease toward the latest position the owner sent, smoothing out network
        # jitter; snap on a large gap (respawn / big correction) instead of
        # sliding across the map. Frame-rate independent via delta_time.
        gap = self.target_position - self.position
        if gap.length() > REMOTE_SNAP_DISTANCE:
            new_position = Vec(self.target_position)
        else:
            t = 1 - REMOTE_SMOOTHING**self.world.delta_time
            new_position = self.position.lerp(self.target_position, t)
        self.update_position(new_position)


class Players(list):
    def __init__(self, world) -> None:
        super().__init__()
        self.world = world

    def add_player(self, player_info, name_color) -> Player:
        player = Player(
            player_info.id,
            player_info.name,
            name_color,
            player_info.character_name,
            self.world.map.spawn_points[player_info.base_number],
            player_info.size,
            self.world,
        )
        self.append(player)
        return player

    def get_player_with_id(self, player_id: int) -> Player | None:
        return next((player for player in self if player.id == player_id), None)
