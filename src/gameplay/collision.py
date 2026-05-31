"""Axis-resolved collision against a list of wall objects (ECS, no pygame.sprite)."""


def is_collide(one, two) -> bool:
    return one.hit_rect.colliderect(two.rect)


def collide(obj, direction: str, walls) -> None:
    # Resolve against EVERY overlapping wall (a corner can touch two at once), and
    # decide the push side from hit_rect's centre — never the sprite rect, whose
    # width changes with rotation and would skew the test (snapping to the wrong
    # side reads as teleporting through the wall).
    for wall in walls:
        if wall is obj or not obj.hit_rect.colliderect(wall.rect):
            continue

        if direction == "x":
            if obj.hit_rect.centerx < wall.rect.centerx:
                obj.hit_rect.right = wall.rect.left
            else:
                obj.hit_rect.left = wall.rect.right
            obj.velocity.x = 0
        else:
            if obj.hit_rect.centery < wall.rect.centery:
                obj.hit_rect.bottom = wall.rect.top
            else:
                obj.hit_rect.top = wall.rect.bottom
            obj.velocity.y = 0
