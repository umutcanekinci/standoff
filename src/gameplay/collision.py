import pygame


def is_collide(one, two):
    return one.hit_rect.colliderect(two.rect)


def collide(object, direction: str, sprite_group: pygame.sprite.Group) -> None:
    hits = pygame.sprite.spritecollide(object, sprite_group, False, is_collide)

    if hits and hits[0] != object:

        if direction == 'x':

            if object.rect.x < hits[0].rect.x:
                object.hit_rect.right = hits[0].rect.left - .001
            else:
                object.hit_rect.left = hits[0].rect.right + .001

            object.velocity.x = 0

        if direction == 'y':

            if object.rect.y < hits[0].rect.y:
                object.hit_rect.bottom = hits[0].rect.top - .001
            else:
                object.hit_rect.top = hits[0].rect.bottom + .001

            object.velocity.y = 0
