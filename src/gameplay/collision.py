"""Axis-resolved collision against a list of wall objects (ECS, no pygame.sprite)."""


def is_collide(one, two) -> bool:
    return one.hit_rect.colliderect(two.rect)


def collide(obj, direction: str, walls) -> None:
    hit = next((w for w in walls if w is not obj and obj.hit_rect.colliderect(w.rect)), None)
    if hit is None:
        return

    if direction == 'x':
        if obj.rect.x < hit.rect.x:
            obj.hit_rect.right = hit.rect.left - .001
        else:
            obj.hit_rect.left = hit.rect.right + .001
        obj.velocity.x = 0

    if direction == 'y':
        if obj.rect.y < hit.rect.y:
            obj.hit_rect.bottom = hit.rect.top - .001
        else:
            obj.hit_rect.top = hit.rect.bottom + .001
        obj.velocity.y = 0
