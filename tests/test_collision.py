"""Behavior and robustness checks for the tile collision engine."""

from __future__ import annotations

import pygame

from world.collision import CollisionEngine
from world.tilemap import TileMap


def engine_for(tile_id: int, position: tuple[int, int] = (3, 3)) -> CollisionEngine:
    data: dict[str, object] = {
        "width": 10,
        "height": 8,
        "tile_size": 50,
        "tiles": [{"id": tile_id, "position": list(position)}],
    }
    return CollisionEngine(TileMap.from_data(data))


def move(
    engine: CollisionEngine,
    start: tuple[float, float],
    velocity_value: tuple[float, float],
    dt: float,
) -> tuple[pygame.Vector2, pygame.Vector2, pygame.Rect, object]:
    position = pygame.Vector2(start)
    velocity = pygame.Vector2(velocity_value)
    rect = pygame.Rect(round(position.x), round(position.y), 30, 40)
    result = engine.move(position, velocity, rect, dt)
    return position, velocity, rect, result


def test_solid_prevents_high_speed_tunneling() -> None:
    _, velocity, rect, result = move(engine_for(1), (40, 160), (2_000, 0), 0.1)
    assert rect.right == 150
    assert velocity.x == 0.0
    assert result.hit_wall


def test_one_way_allows_upward_passage_but_catches_fall() -> None:
    engine = engine_for(2)
    _, upward_velocity, upward_rect, upward = move(engine, (160, 190), (0, -900), 0.1)
    assert upward_rect.top < 150
    assert upward_velocity.y == -900
    assert not upward.grounded

    _, downward_velocity, downward_rect, downward = move(engine, (160, 90), (0, 700), 0.1)
    assert downward_rect.bottom == 150
    assert downward_velocity.y == 0.0
    assert downward.grounded


def test_hazard_reports_contact_without_blocking() -> None:
    _, velocity, _, result = move(engine_for(3), (160, 100), (0, 700), 0.1)
    assert result.hit_hazard
    assert velocity.y == 700


def test_bounce_and_slippery_surface_responses() -> None:
    _, bounce_velocity, bounce_rect, bounce = move(engine_for(6), (160, 90), (0, 700), 0.1)
    assert bounce_rect.bottom <= 150
    assert bounce_velocity.y < 0.0
    assert bounce.bounced

    _, slippery_velocity, slippery_rect, slippery = move(
        engine_for(7), (160, 90), (0, 700), 0.1
    )
    assert slippery_rect.bottom == 150
    assert slippery_velocity.y == 0.0
    assert slippery.grounded and slippery.on_slippery


def test_breakable_tile_is_solid_until_broken_by_future_interaction() -> None:
    _, velocity, rect, result = move(engine_for(5), (40, 160), (2_000, 0), 0.1)
    assert rect.right == 150
    assert velocity.x == 0.0
    assert result.hit_wall

