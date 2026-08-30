"""Integrated Phase 5 hazard, pickup persistence, death, and restart behavior."""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from core.game import Game
from systems.progression import CollectibleType

DT = 1.0 / 60.0


def enter_first_hazard(game: Game) -> None:
    game.player.reposition((12 * 64 + 10, 16 * 64 + 8))
    game.update(DT)


def test_hazard_damage_death_and_respawn_preserve_pickups() -> None:
    game = Game()
    try:
        shard = next(
            item
            for item in game.collectibles.collectibles
            if item.kind is CollectibleType.EMBER_SHARD
        )
        game.player.reposition(
            (
                shard.pickup_rect.centerx - game.player.rect.width / 2,
                shard.pickup_rect.centery - game.player.rect.height / 2,
            )
        )
        game.update(0.0)
        assert game.progress.score == 100
        active_after_pickup = game.collectibles.active_count

        enter_first_hazard(game)
        assert game.player.health == 2 and not game.player.is_dead
        assert game.progress.score == 100
        assert game.collectibles.active_count == active_after_pickup

        enter_first_hazard(game)
        enter_first_hazard(game)
        assert game.player.is_dead and game.player.health == 0
        for _ in range(60):
            game.update(DT)
        assert not game.player.is_dead
        assert game.player.health == game.player.max_health
        assert game.player.lives == 2
        assert game.progress.score == 100
    finally:
        game.shutdown()


def test_full_game_level_reset_restores_authored_state() -> None:
    game = Game()
    try:
        original_total = len(game.level.collectible_spawns)
        game.collectibles.collectibles[0].active = False
        game.progress.register("shard_01", CollectibleType.EMBER_SHARD)
        game.player.take_damage()
        game.reset_level()
        assert game.collectibles.active_count == original_total
        assert game.progress.score == 0
        assert game.player.health == game.player.max_health
        assert game.player.lives == 3
    finally:
        game.shutdown()

