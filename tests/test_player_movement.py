"""Deterministic checks for Phase 1 movement feel and collision behavior."""

from __future__ import annotations

import pygame

from entities.player import Player, PlayerControls
from settings import PLAYER_PHYSICS
from world.collision import CollisionEngine
from world.tilemap import TileMap

DT = 1.0 / 60.0


def collision_map(
    placements: list[dict[str, object]] | None = None,
    width: int = 20,
    height: int = 8,
) -> CollisionEngine:
    data: dict[str, object] = {
        "width": width,
        "height": height,
        "tile_size": 50,
        "tiles": placements or [{"id": 1, "position": [0, 6], "size": [width, 2]}],
    }
    return CollisionEngine(TileMap.from_data(data))


FLOOR_TOP = 300


def step(
    player: Player,
    frames: int,
    controls: PlayerControls | None = None,
    collision: CollisionEngine | None = None,
) -> None:
    current = controls or PlayerControls()
    for frame in range(frames):
        player.update(
            DT,
            PlayerControls(
                move_axis=current.move_axis,
                jump_pressed=current.jump_pressed and frame == 0,
                jump_held=current.jump_held,
                jump_released=current.jump_released and frame == 0,
            ),
            collision or collision_map(),
        )


def grounded_player() -> Player:
    player = Player((100.0, FLOOR_TOP - Player.HEIGHT))
    step(player, 2)
    assert player.grounded
    return player


def test_acceleration_deceleration_and_max_speed() -> None:
    player = grounded_player()
    step(player, 30, PlayerControls(move_axis=1.0))
    assert player.velocity.x == PLAYER_PHYSICS.max_run_speed

    step(player, 10)
    assert player.velocity.x < PLAYER_PHYSICS.max_run_speed
    step(player, 10)
    assert player.velocity.x == 0.0


def test_floor_and_wall_collision() -> None:
    collision = collision_map(
        [
            {"id": 1, "position": [0, 6], "size": [20, 2]},
            {"id": 1, "position": [5, 0], "size": [1, 6]},
        ]
    )
    player = grounded_player()
    step(player, 60, PlayerControls(move_axis=1.0), collision)

    assert player.rect.right == 250
    assert player.velocity.x == 0.0
    assert player.grounded


def jump_peak(hold_jump: bool) -> float:
    player = grounded_player()
    start_y = player.position.y
    minimum_y = start_y
    for frame in range(90):
        player.update(
            DT,
            PlayerControls(
                jump_pressed=frame == 0,
                jump_held=hold_jump,
                jump_released=frame == 1 and not hold_jump,
            ),
            collision_map(),
        )
        minimum_y = min(minimum_y, player.position.y)
    return start_y - minimum_y


def test_variable_height_jump() -> None:
    short_height = jump_peak(False)
    full_height = jump_peak(True)
    assert short_height > 35.0
    assert full_height > short_height + 100.0


def test_coyote_time_allows_jump_after_leaving_platform() -> None:
    ledge = collision_map([{"id": 1, "position": [0, 4], "size": [3, 1]}])
    player = Player((75.0, 200 - Player.HEIGHT))
    step(player, 2, collision=ledge)
    player.velocity.x = PLAYER_PHYSICS.max_run_speed

    for _ in range(20):
        player.update(DT, PlayerControls(move_axis=1.0), ledge)
        if not player.grounded:
            break
    assert not player.grounded

    player.update(DT, PlayerControls(jump_pressed=True, jump_held=True), ledge)
    assert player.velocity.y < 0.0


def test_jump_buffer_fires_on_landing() -> None:
    player = Player((100.0, 195.0))
    player.velocity.y = 260.0
    collision = collision_map()
    player.update(DT, PlayerControls(jump_pressed=True, jump_held=True), collision)

    jumped = False
    for _ in range(12):
        player.update(DT, PlayerControls(jump_held=True), collision)
        if player.velocity.y < 0.0:
            jumped = True
            break
    assert jumped
