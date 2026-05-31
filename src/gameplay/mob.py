from util.constants import *
from random import choice
from gameplay.entity import Entity


class Mob(Entity):
    def __init__(self, id, name, position, size, target_base, character, game) -> None:
        super().__init__(
            id,
            name,
            Red,
            position,
            size,
            game.assets.image_path(f"char_{character}_idle"),
            MOB_MAX_HP,
            MOB_MAX_HP,
        )

        self.target_base, self.character, self.game = target_base, character, game
        self.map, self.camera = game.map, game.camera
        self.damage = 10
        self.range = RANGE_RADIUS

        # Hit rect for collisions
        self.set_position(position)
        self.hit_rect = MOB_HIT_RECT.copy()
        self.hit_rect.center = self.rect.center

        self.velocity = Vec()
        self.acceleration = Vec()
        self.angle = 0
        self.speed = choice(MOB_SPEEDS)

    def check_range(self):
        if not self.game.players:
            self.target = self.target_base
            return

        # Squared distances throughout — avoids a sqrt per player per frame.
        cx, cy = self.rect.center
        nearest = min(
            (player.rect.center for player in self.game.players),
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
        for mob in self.game.mob_grid.query_radius((cx, cy), AVOID_RADIUS):
            if mob is self:
                continue
            dx, dy = cx - mob.rect.centerx, cy - mob.rect.centery
            dist_sq = dx * dx + dy * dy
            if 0 < dist_sq < radius_sq:
                self.acceleration += Vec(dx, dy).normalize()

    def move(self):
        self.acceleration = Vec(1, 0).rotate(-self.angle)
        self.avoid_mobs()
        self.acceleration *= self.speed
        self.acceleration += self.velocity * -1
        self.velocity += self.acceleration * self.game.delta_time
        self.delta = (
            self.velocity * self.game.delta_time
            + 0.5 * self.acceleration * self.game.delta_time**2
        )
        super().move(self.delta)

    def update(self):
        self.check_range()
        self.rotate_to_target()
        self.move()

        now = pygame.time.get_ticks()

        if not hasattr(self, "last_attack"):
            self.last_attack = -1000

        if now - self.last_attack > 1000:
            for player in [
                p for p in self.game.players if self.hit_rect.colliderect(p.rect)
            ]:
                player.lose_hp(self.damage)
                player.apply_knockback(Vec(1, 0).rotate(-self.angle), MOB_KNOCKBACK)
                self.last_attack = now
                break


class Mobs(list):
    def __init__(self, game) -> None:
        super().__init__()
        self.game = game

    def add_mob(self, mob_info, character="zombie") -> None:
        self.append(
            Mob(
                mob_info.id,
                "Mob " + str(mob_info.id),
                mob_info.position,
                mob_info.size,
                mob_info.target_base,
                character,
                self.game,
            )
        )

    def get_mob_from_id(self, id: int):
        return next((mob for mob in self if mob.id == id), None)
