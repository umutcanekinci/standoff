from util.constants import (
    PLAYER_MAX_HP,
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
        self, entity_id, name, name_color, character, position, size, game
    ) -> None:
        super().__init__(
            entity_id,
            name,
            name_color,
            position,
            size,
            game.assets.image_path(f"char_{character}_gun"),
            PLAYER_MAX_HP,
            PLAYER_MAX_HP,
        )

        # Shooting
        self.is_shooting = False
        self.shoot_rate = SHOOT_RATE
        self.last_shoot_time = -1000

        self.character, self.game = character, game
        self.map, self.camera = game.map, game.camera

        # Hit rect for collisions
        self.hit_rect = PLAYER_HIT_RECT.copy()
        self.hit_rect.center = self.rect.center
        self.auto_shoot = (True,)

        self.force = Vec(3, 3)
        self.frictional_force = Vec(-1.0, -1.0)
        self.net_force = Vec()

        self.acceleration = Vec()
        self.max_acceleration = 5

        self.velocity = Vec()
        self.max_speed = 5

        self.force_rotation = Vec()
        self.delta = Vec()
        self.knockback = Vec()
        self.angle = 0

        self.density = 25
        self.weight = (
            self.rect.width / TILE_WIDTH * self.rect.height / TILE_HEIGHT
        ) * self.density

    def rotate_to_mouse(self):
        self.angle = (
            Vec(self.game.mouse_position)
            - Vec(self.game.camera.apply(self.rect).center)
        ).angle_to(Vec(1, 0))  # angle between difference vector and x axis

    def _update_force_rotation(self):
        # Map held keys to a unit force direction
        keys = self.game.keys
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
            self.force_rotation.normalize()

    def _apply_friction(self):
        if self.velocity.length() == 0:
            return

        if abs(self.net_force.x) > self.frictional_force.x:
            self.net_force.x += (
                self.frictional_force.x
                * self.velocity.normalize().x
                * self.game.delta_time
            )

        if abs(self.net_force.y) > self.frictional_force.y:
            self.net_force.y += (
                self.frictional_force.y
                * self.velocity.normalize().y
                * self.game.delta_time
            )

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
        self._apply_friction()

        self.acceleration = self.net_force / self.weight
        self.acceleration.x = max(
            -self.max_acceleration, min(self.max_acceleration, self.acceleration.x)
        )
        self.acceleration.y = max(
            -self.max_acceleration, min(self.max_acceleration, self.acceleration.y)
        )

        self.velocity += self.acceleration * self.game.delta_time
        if self.velocity.length() > self.max_speed:
            self.velocity.scale_to_length(self.max_speed)

        if abs(self.velocity.x) < 0.01:
            self.velocity.x = 0
        if abs(self.velocity.y) < 0.01:
            self.velocity.y = 0

        self.delta = (self.velocity * self.game.delta_time) + (
            0.5 * self.acceleration * self.game.delta_time * self.game.delta_time
        )
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
            MuzzleFlash(self.game, position, self.angle)

            self.velocity = Vec(-KICKBACK, 0).rotate(-self.angle)

            self.last_shoot_time = now

    def handle_events(self, event):
        if self.alive:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.auto_shoot:
                    self.is_shooting = True

                else:
                    self.game.shoot()

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.is_shooting = False

    def update(self):
        self.rotate(self.angle)
        super().move(self.delta)


class Players(list):
    def __init__(self, game) -> None:
        super().__init__()
        self.game = game

    def add_player(self, player_info, name_color) -> Player:
        player = Player(
            player_info.id,
            player_info.name,
            name_color,
            player_info.character_name,
            self.game.map.spawn_points[player_info.base_number],
            player_info.size,
            self.game,
        )
        self.append(player)
        return player

    def get_player_with_id(self, player_id: int) -> Player | None:
        return next((player for player in self if player.id == player_id), None)
