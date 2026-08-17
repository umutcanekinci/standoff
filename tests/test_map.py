import pygame

from gameplay.map import Map
from gameplay.tiles import Obstacle
from util.constants import TILE_WIDTH, TILE_HEIGHT

MAP_PATH = "assets/maps/level2.tmx"


class FakeWorld:
    def __init__(self):
        self.walls = []


def test_get_objects_parses_base_points_offset_to_tile_center():
    world = FakeWorld()
    m = Map(world, MAP_PATH, border_width=2)

    assert m.base_points[1] == (1536 + TILE_WIDTH / 2, 1536 + TILE_HEIGHT / 2)
    assert set(m.base_points) == {1, 2, 3, 4}


def test_get_objects_parses_spawn_points_offset_to_tile_center():
    world = FakeWorld()
    m = Map(world, MAP_PATH, border_width=2)

    assert m.spawn_points[1] == (3137 + TILE_WIDTH / 2, 3136 + TILE_HEIGHT / 2)
    assert set(m.spawn_points) == {1, 2, 3, 4}


def test_get_objects_registers_a_wall_obstacle_per_wall_object():
    world = FakeWorld()
    Map(world, MAP_PATH, border_width=2)

    assert len(world.walls) == 17  # level2.tmx has 25 objects: 4 base + 4 spawn + 17 wall
    assert all(isinstance(w, Obstacle) for w in world.walls)


def test_wall_position_is_offset_from_its_top_left_by_half_its_own_size():
    world = FakeWorld()
    Map(world, MAP_PATH, border_width=2)

    first_wall = world.walls[0]
    # Map passes a top-left (obj.x, obj.y); Obstacle centers itself using its
    # own (width, height) -- self-consistent regardless of this particular
    # wall object's actual size in the tmx.
    w, h = first_wall.rect.size
    assert first_wall.rect.topleft == (1408, 1920)
    assert first_wall.position == pygame.math.Vector2(1408 + w / 2, 1920 + h / 2)


def test_render_builds_an_image_sized_to_the_map():
    world = FakeWorld()
    m = Map(world, MAP_PATH, border_width=2)

    m.render()

    assert m.image.get_size() == (m.map_width, m.map_height)
    assert m.rect.size == (m.map_width, m.map_height)


def test_obstacle_draw_rect_applies_the_camera_transform():
    world = FakeWorld()
    calls = []
    world.camera = type("Cam", (), {"apply": lambda self, rect: calls.append(rect) or rect})()
    obstacle = Obstacle(world, (0, 0), (64, 64))
    surface = pygame.Surface((100, 100))

    obstacle.draw_rect(surface)

    assert calls == [obstacle.rect]
