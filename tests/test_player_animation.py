"""Nova animation state transitions and collision/visual independence."""

from __future__ import annotations

import pygame

from entities.player import Player, PlayerControls
from systems.player_animation import PlayerAnimationState
from world.collision import CollisionEngine
from world.tilemap import TileMap

DT = 1.0 / 60.0


def floor_collision() -> CollisionEngine:
    return CollisionEngine(
        TileMap.from_data(
            {
                "width": 20,
                "height": 8,
                "tile_size": 50,
                "tiles": [{"id": 1, "position": [0, 6], "size": [20, 2]}],
            }
        )
    )


def settle(player: Player, collision: CollisionEngine) -> None:
    for _ in range(60):
        player.update(DT, PlayerControls(), collision)
        if player.grounded:
            return
    raise AssertionError("player did not settle")


def test_idle_run_and_facing_transitions_are_stable() -> None:
    collision = floor_collision()
    player = Player((100, 238))
    settle(player, collision)
    player.update(DT, PlayerControls(), collision)
    assert player.animation.current_name == PlayerAnimationState.IDLE.value

    for _ in range(5):
        player.update(DT, PlayerControls(move_axis=-1), collision)
    assert player.animation.current_name == PlayerAnimationState.RUN.value
    assert player.facing == -1 and player.animation.flip_x
    frame_index = player.animation.frame_index
    player.update(DT, PlayerControls(move_axis=-1), collision)
    assert player.animation.frame_index >= frame_index


def test_jump_apex_and_fall_transitions() -> None:
    collision = floor_collision()
    player = Player((100, 238))
    settle(player, collision)
    player.update(DT, PlayerControls(jump_pressed=True, jump_held=True), collision)
    assert player.animation.current_name == PlayerAnimationState.JUMP.value

    for _ in range(120):
        player.update(DT, PlayerControls(), collision)
        if not player.grounded and player.velocity.y > 100:
            break
    assert player.animation.current_name == PlayerAnimationState.FALL.value


def test_meaningful_fall_triggers_non_looping_land() -> None:
    collision = floor_collision()
    player = Player((100, 100))
    player.velocity.y = 500
    for _ in range(60):
        player.update(DT, PlayerControls(), collision)
        if player.grounded:
            break
    assert player.grounded
    assert player.animation.current_name == PlayerAnimationState.LAND.value
    assert "land" in player.animation_events

    for _ in range(20):
        player.update(DT, PlayerControls(), collision)
    assert player.animation.current_name == PlayerAnimationState.IDLE.value


def test_hurt_attack_and_death_hooks_complete_safely() -> None:
    collision = floor_collision()
    player = Player((100, 238))
    settle(player, collision)

    player.trigger_attack()
    player.update(DT, PlayerControls(), collision)
    assert player.animation.current_name == PlayerAnimationState.ATTACK.value
    for _ in range(30):
        player.update(DT, PlayerControls(), collision)
    assert player.animation.current_name == PlayerAnimationState.IDLE.value

    player.trigger_hurt()
    player.update(DT, PlayerControls(), collision)
    assert player.animation.current_name == PlayerAnimationState.HURT.value
    for _ in range(30):
        player.update(DT, PlayerControls(), collision)
    assert player.animation.current_name == PlayerAnimationState.IDLE.value

    player.trigger_death()
    for _ in range(45):
        player.update(DT, PlayerControls(), collision)
    assert player.animation.current_name == PlayerAnimationState.DEATH.value
    assert player.death_animation_finished


def test_animation_frames_do_not_change_collision_rectangle() -> None:
    collision = floor_collision()
    player = Player((100, 238))
    settle(player, collision)
    original_rect = player.rect.copy()
    original_size = player.rect.size
    destination = pygame.Surface((200, 200), pygame.SRCALPHA)

    for trigger in (player.trigger_attack, player.trigger_hurt, player.trigger_death):
        trigger()
        player.draw(destination, (20, -100))
        assert player.rect == original_rect
        assert player.rect.size == original_size
        player.respawn(original_rect.topleft)

