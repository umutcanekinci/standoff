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
        self.auto_shoot = True

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

    def rotate_to_mouse(self):
        self.angle = (
            Vec(self.world.mouse_position)
            - Vec(self.world.camera.apply(self.rect).center)
        ).angle_to(Vec(1, 0))  # angle between difference vector and x axis

    def _update_force_rotation(self):
        # Map held keys to a unit force direction
        keys = self.world.keys
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.force_rotation.x = -1
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.force_rotation.x = 1
        else:
            self.force_rotation.x = 0

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.force_rotation.y = -1
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.force_rotation.y = 1
        else:
            self.force_rotation.y = 0

        if self.force_rotation.length() != 0:
            # normalize() returns a new vector; mutate in place so diagonals are a
            # unit direction (otherwise diagonal input is ~41% stronger).
            self.force_rotation.normalize_ip()

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

    def handle_events(self, event):
        if self.alive:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.auto_shoot:
                    self.is_shooting = True

                else:
                    self.world.shoot()

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.is_shooting = False

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
