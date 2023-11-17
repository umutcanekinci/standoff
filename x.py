import pygame

v1 = pygame.Rect(100, 100, 100, 100)
v2 = pygame.Rect(100, 100, 100, 100)

print(v1.topleft + pygame.math.Vector2(10, 5))