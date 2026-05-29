import pygame


def isCollide(one, two):
    return one.hitRect.colliderect(two.rect)


def Collide(object, direction: str, spriteGroup: pygame.sprite.Group) -> None:
    hits = pygame.sprite.spritecollide(object, spriteGroup, False, isCollide)

    if hits and hits[0] != object:

        if direction == 'x':

            if object.rect.x < hits[0].rect.x:
                object.hitRect.right = hits[0].rect.left - .001
            else:
                object.hitRect.left = hits[0].rect.right + .001

            object.velocity.x = 0

        if direction == 'y':

            if object.rect.y < hits[0].rect.y:
                object.hitRect.bottom = hits[0].rect.top - .001
            else:
                object.hitRect.top = hits[0].rect.bottom + .001

            object.velocity.y = 0
