"""Deterministic checks for Phase 1 movement feel and collision behavior."""

from __future__ import annotations

import pygame

from entities.player import Player, PlayerControls
from settings import PLAYER_PHYSICS

DT = 1.0 / 60.0
FLOOR = pygame.Rect(0, 300, 900, 100)


def step(
    player: Player,
    frames: int,
    controls: PlayerControls | None = None,
    solids: list[pygame.Rect] | None = None,
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
            solids or [FLOOR],
        )


def grounded_player() -> Player:
    player = Player((100.0, FLOOR.top - Player.HEIGHT))
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
    wall = pygame.Rect(250, 0, 40, 300)
    player = grounded_player()
    step(player, 60, PlayerControls(move_axis=1.0), [FLOOR, wall])

    assert player.rect.right == wall.left
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
            [FLOOR],
        )
        minimum_y = min(minimum_y, player.position.y)
    return start_y - minimum_y


def test_variable_height_jump() -> None:
    short_height = jump_peak(False)
    full_height = jump_peak(True)
    assert short_height > 35.0
    assert full_height > short_height + 100.0


def test_coyote_time_allows_jump_after_leaving_platform() -> None:
    ledge = pygame.Rect(0, 200, 120, 30)
    player = Player((65.0, ledge.top - Player.HEIGHT))
    step(player, 2, solids=[ledge])
    player.velocity.x = PLAYER_PHYSICS.max_run_speed

    for _ in range(20):
        player.update(DT, PlayerControls(move_axis=1.0), [ledge])
        if not player.grounded:
            break
    assert not player.grounded

    player.update(DT, PlayerControls(jump_pressed=True, jump_held=True), [ledge])
    assert player.velocity.y < 0.0


def test_jump_buffer_fires_on_landing() -> None:
    player = Player((100.0, 195.0))
    player.velocity.y = 260.0
    player.update(DT, PlayerControls(jump_pressed=True, jump_held=True), [FLOOR])

    jumped = False
    for _ in range(12):
        player.update(DT, PlayerControls(jump_held=True), [FLOOR])
        if player.velocity.y < 0.0:
            jumped = True
            break
    assert jumped

