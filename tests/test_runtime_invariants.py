"""Cross-system runtime invariants and repeated lifecycle stress."""
from __future__ import annotations

import pygame
import pytest

from entities.player import DamageSource, Player, PlayerControls
from tests.helpers import activate_goal
from world.collision import CollisionEngine
from world.tilemap import TileMap


def floor_collision() -> CollisionEngine:
    return CollisionEngine(TileMap.from_data({
        "width": 40, "height": 10, "tile_size": 50,
        "tiles": [{"id": 1, "position": [0, 8], "size": [40, 2]}],
    }))


def simulate_motion(dt: float, frames: int) -> Player:
    player = Player((100, 338))
    collision = floor_collision()
    player.update(dt, PlayerControls(), collision)
    for _ in range(frames):
        player.update(dt, PlayerControls(move_axis=1), collision)
    return player


def test_horizontal_motion_is_semantically_stable_across_dt_sequences() -> None:
    sixty = simulate_motion(1 / 60, 60)
    one_twenty = simulate_motion(1 / 120, 120)
    assert sixty.velocity.x == pytest.approx(one_twenty.velocity.x, abs=0.01)
    assert sixty.position.x == pytest.approx(one_twenty.position.x, abs=12.0)
    assert sixty.grounded and one_twenty.grounded


def test_health_and_lives_remain_bounded_under_generated_damage(seeded_rng) -> None:
    player = Player((0, 0))
    for _ in range(250):
        player.invulnerability_timer = 0
        amount = seeded_rng.randint(0, 4)
        player.apply_damage(amount, DamageSource.ENEMY)
        assert 0 <= player.health <= player.max_health
        assert player.lives >= 0
        if player.is_dead:
            player.lives = max(0, player.lives - 1)
            player.respawn((0, 0))


@pytest.mark.integration
@pytest.mark.parametrize("level_id", ["verdant_01", "verdant_02", "verdant_boss"])
def test_repeated_full_reconstruction_does_not_accumulate_runtime_state(game_factory, level_id) -> None:
    game = game_factory(level_id=level_id)
    expected = None
    for _ in range(12):
        game.reset_level()
        snapshot = (
            len(game.collectibles.collectibles), len(game.enemies.enemies),
            len(game.world_objects.platforms), len(game.npcs.npcs),
            len(game.projectiles.projectiles), game.effects.emitter_count,
        )
        expected = expected or snapshot
        assert snapshot == expected


@pytest.mark.scenario
def test_gameplay_pause_complete_map_transition_cleans_transient_state(game_factory) -> None:
    game = game_factory()
    game.open_pause()
    before = (game.player.position.copy(), game.elapsed_time)
    game.update(1)
    assert (game.player.position, game.elapsed_time) == before
    game.resume_game()
    activate_goal(game)
    assert game.level_result is not None
    game.continue_campaign()
    assert game.app_mode == "map"
    assert game.effects.emitter_count <= 1  # map ambience may own one emitter
    assert not game.projectiles.projectiles
