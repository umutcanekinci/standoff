from __future__ import annotations

import pygame
from pygame.math import Vector2 as Vec

from util.constants import (
    Red,
    MOB_MAX_HP,
    MOB_HIT_RECT,
    RANGE_RADIUS,
    AVOID_RADIUS,
    MOB_SPEEDS,
    MOB_KNOCKBACK,
    REMOTE_SMOOTHING,
    REMOTE_SNAP_DISTANCE,
)
from gameplay.entity import Entity


class Mob(Entity):
    def __init__(
        self, entity_id, name, position, size, target_base, character, world
    ) -> None:
        super().__init__(
            entity_id,
            name,
            Red,
            position,
            size,
            world.assets.image_path(f"char_{character}_idle"),
            MOB_MAX_HP,
            MOB_MAX_HP,
        )

        self.target_base, self.character, self.world = target_base, character, world
        self.map, self.camera = world.map, world.camera
        self.damage = 10
        self.range = RANGE_RADIUS

        # Hit rect for collisions
        self.set_position(position)
        self.hit_rect = MOB_HIT_RECT.copy()
        self.hit_rect.center = self.rect.center

        self.velocity = Vec()
        self.acceleration = Vec()
        self.delta = Vec()  # per-frame move vector; recomputed in update_movement
        self.angle = 0
        # Keyed by the (server-assigned, synced) mob id rather than random, so
        # every client gives the same mob the same speed.
        self.speed = MOB_SPEEDS[entity_id % len(MOB_SPEEDS)]

        self.target = target_base  # current chase target; refreshed by check_range
        self.last_attack = -1000  # ticks of last hit landed; gates the 1s cooldown

        # Online: the server owns mob movement and we follow target_position;
        # offline we run the local AI below. GameplayScene.spawn_mob sets is_network.
        self.is_network = False
        self.target_position = Vec(position)

    def check_range(self):
        if not self.world.players:
            self.target = self.target_base
            return

        # Squared distances throughout — avoids a sqrt per player per frame.
        cx, cy = self.rect.center
        nearest = min(
            (player.rect.center for player in self.world.players),
            key=lambda c: (c[0] - cx) ** 2 + (c[1] - cy) ** 2,
        )
        nx, ny = nearest
        in_range = (nx - cx) ** 2 + (ny - cy) ** 2 < self.range * self.range
        self.target = nearest if in_range else self.target_base

    def rotate_to_target(self):
        self.angle = (Vec(self.target) - Vec(self.rect.center)).angle_to(
            Vec(1, 0)
        )  # angle between difference vector and x axis
        self.rotate(self.angle)

    def avoid_mobs(self):
        # Only test mobs in nearby grid cells, not all of them (was O(N^2)).
        cx, cy = self.rect.center
        radius_sq = AVOID_RADIUS * AVOID_RADIUS
        for mob in self.world.mob_grid.query_radius((cx, cy), AVOID_RADIUS):
            if mob is self:
                continue
            dx, dy = cx - mob.rect.centerx, cy - mob.rect.centery
            dist_sq = dx * dx + dy * dy
            if 0 < dist_sq < radius_sq:
                self.acceleration += Vec(dx, dy).normalize()

    def update_movement(self):
        self.acceleration = Vec(1, 0).rotate(-self.angle)
        self.avoid_mobs()
        self.acceleration *= self.speed
        self.acceleration += self.velocity * -1
        self.velocity += self.acceleration * self.world.delta_time
        # Semi-implicit Euler: velocity is already advanced, so the step is just
        # velocity * dt (the old 0.5*a*dt**2 term double-counted acceleration).
        self.delta = self.velocity * self.world.delta_time
        super().move(self.delta)

    def _follow_remote(self):
        # Online: ease toward the server's authoritative position (snap on a large
        # gap), and face the way we're moving. No local AI, so all clients agree.
        gap = self.target_position - self.position
        if gap.length() > 1:
            self.angle = gap.angle_to(Vec(1, 0))
        self.rotate(self.angle)
        if gap.length() > REMOTE_SNAP_DISTANCE:
            new_position = Vec(self.target_position)
        else:
            t = 1 - REMOTE_SMOOTHING**self.world.delta_time
            new_position = self.position.lerp(self.target_position, t)
        self.update_position(new_position)

    def _try_attack(self):
        # HP is client-local (not synced), so each client applies mob hits to its
        # own view of the players — same as bullets.
        now = pygame.time.get_ticks()
        if now - self.last_attack > 1000:
            for player in [
                p
                for p in self.world.players
                if p.alive and self.hit_rect.colliderect(p.rect)
            ]:
                player.lose_hp(self.damage)
                player.apply_knockback(Vec(1, 0).rotate(-self.angle), MOB_KNOCKBACK)
                self.last_attack = now
                break

    def update(self):
        if self.is_network:
            self._follow_remote()
        else:
            self.check_range()
            self.rotate_to_target()
            self.update_movement()
        self._try_attack()


class Mobs(list):
    def __init__(self, world) -> None:
        super().__init__()
        self.world = world

    def add_mob(self, mob_info, character="zombie") -> "Mob":
        mob = Mob(
            mob_info.id,
            "Mob " + str(mob_info.id),
            mob_info.position,
            mob_info.size,
            mob_info.target_base,
            character,
            self.world,
        )
        self.append(mob)
        return mob

    def get_mob_from_id(self, mob_id: int):
        return next((mob for mob in self if mob.id == mob_id), None)
