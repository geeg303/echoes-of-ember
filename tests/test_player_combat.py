"""Ember Pulse cooldown, limits, faction damage, resistance, and score safety."""

from __future__ import annotations

import pygame

from entities.player import Player
from entities.projectile import EmberPulseProjectile, Faction
from settings import (
    EMBER_PULSE_COOLDOWN,
    EMBER_PULSE_DAMAGE,
    EMBER_PULSE_LIFETIME,
    EMBER_PULSE_MAX_ACTIVE,
    EMBER_PULSE_SPEED,
)
from systems.enemy_config import EnemyType
from systems.enemy_system import EnemyManager
from systems.player_combat import PlayerCombatController
from systems.progression import LevelProgress
from systems.projectile_system import ProjectileManager
from world.collision import CollisionEngine
from world.level import EnemySpawn
from world.tilemap import TileMap


def empty_world() -> tuple[TileMap, CollisionEngine]:
    tilemap = TileMap.from_data(
        {"width": 30, "height": 10, "tile_size": 50, "tiles": []}
    )
    return tilemap, CollisionEngine(tilemap)


def test_ember_pulse_configuration_cooldown_direction_and_limit() -> None:
    player = Player((100, 100))
    projectiles = ProjectileManager()
    combat = PlayerCombatController(ember_pulse_enabled=True)
    assert combat.try_attack(player, projectiles)
    first = projectiles.projectiles[0]
    assert first.damage == EMBER_PULSE_DAMAGE
    assert first.velocity.x == EMBER_PULSE_SPEED
    assert first.lifetime == EMBER_PULSE_LIFETIME
    assert first.faction is Faction.PLAYER
    assert not combat.try_attack(player, projectiles)

    for _ in range(EMBER_PULSE_MAX_ACTIVE - 1):
        combat.update(EMBER_PULSE_COOLDOWN)
        assert combat.try_attack(player, projectiles)
    combat.update(EMBER_PULSE_COOLDOWN)
    assert not combat.try_attack(player, projectiles)
    assert len(projectiles.projectiles) == EMBER_PULSE_MAX_ACTIVE

    projectiles.clear()
    player.facing = -1
    combat.update(EMBER_PULSE_COOLDOWN)
    assert combat.try_attack(player, projectiles)
    assert projectiles.projectiles[0].velocity.x == -EMBER_PULSE_SPEED


def pulse_at(manager: ProjectileManager, center: tuple[int, int]) -> None:
    manager.spawn(
        EmberPulseProjectile(
            manager.new_id("pulse"),
            center,
            pygame.Vector2(),
            1,
            Faction.PLAYER,
            1.0,
            owner_id="player",
        )
    )


def test_projectile_kills_normal_enemy_and_awards_score_once() -> None:
    tilemap, collision = empty_world()
    projectiles = ProjectileManager()
    enemies = EnemyManager(
        (EnemySpawn("crawler", EnemyType.CRAWLER, (300, 200), {}),), projectiles
    )
    player = Player((0, 0))
    progress = LevelProgress.from_types([])
    target = enemies.enemies[0]
    pulse_at(projectiles, target.rect.center)
    outcome = enemies.update(
        0.0, pygame.Rect(0, 0, 1000, 600), player, collision, tilemap, progress
    )
    assert not target.alive and outcome.score_awarded == 200 and progress.score == 200

    pulse_at(projectiles, target.rect.center)
    second = enemies.update(
        0.0, pygame.Rect(0, 0, 1000, 600), player, collision, tilemap, progress
    )
    assert second.score_awarded == 0 and progress.score == 200
    assert projectiles.projectiles == []


def test_armored_enemy_requires_four_separate_pulse_hits() -> None:
    tilemap, collision = empty_world()
    projectiles = ProjectileManager()
    enemies = EnemyManager(
        (EnemySpawn("armor", EnemyType.ARMORED, (300, 200), {}),), projectiles
    )
    player = Player((0, 0))
    progress = LevelProgress.from_types([])
    target = enemies.enemies[0]
    for expected_health in (3, 2, 1, 0):
        target.hit_cooldown = 0.0
        pulse_at(projectiles, target.rect.center)
        outcome = enemies.update(
            0.0, pygame.Rect(0, 0, 1000, 600), player, collision, tilemap, progress
        )
        assert target.health == expected_health
    assert not target.alive
    assert outcome.score_awarded == 750 and progress.score == 750


def test_level_reset_replaces_all_active_projectiles() -> None:
    from core.game import Game

    game = Game()
    try:
        assert game.player_combat.try_attack(game.player, game.projectiles)
        assert game.projectiles.projectiles
        game.reset_level()
        assert game.projectiles.projectiles == []
    finally:
        game.shutdown()
