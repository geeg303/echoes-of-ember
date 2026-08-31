"""Enemy configuration, damage, death, stomps, and projectile contracts."""

from __future__ import annotations

import pygame

from enemies import create_enemy
from entities.player import Player
from entities.projectile import Faction, Projectile
from settings import PLAYER_STOMP_BOUNCE_SPEED, PROJECT_ROOT
from systems.combat import DamageSource
from systems.enemy_config import ENEMY_CONFIGS, EnemyType, configured_enemy
from systems.enemy_system import EnemyManager
from systems.progression import LevelProgress
from systems.projectile_system import ProjectileManager
from world.collision import CollisionEngine
from world.level import EnemySpawn, Level
from world.tilemap import TileMap


def floor_world() -> tuple[TileMap, CollisionEngine]:
    tilemap = TileMap.from_data(
        {
            "width": 20,
            "height": 8,
            "tile_size": 50,
            "tiles": [{"id": 1, "position": [0, 6], "size": [20, 2]}],
        }
    )
    return tilemap, CollisionEngine(tilemap)


def test_level_spawns_all_five_enemy_types() -> None:
    level = Level.load(PROJECT_ROOT / "data" / "levels" / "level_01.json")
    assert len(level.enemy_spawns) == 10
    assert {spawn.kind for spawn in level.enemy_spawns} == set(EnemyType)


def test_enemy_configuration_overrides_are_typed_and_isolated() -> None:
    crawler = configured_enemy(EnemyType.CRAWLER, {"speed": 99, "cliff_avoidance": False})
    assert crawler.speed == 99.0 and not crawler.cliff_avoidance
    assert ENEMY_CONFIGS[EnemyType.CRAWLER].speed == 82.0


def test_enemy_damage_death_cleanup_and_score_are_one_shot() -> None:
    enemy = create_enemy(EnemySpawn("c", EnemyType.CRAWLER, (100, 264), {}))
    assert enemy.take_damage(1)
    assert not enemy.alive and enemy.health == 0
    assert enemy.claim_score() == 200
    assert enemy.claim_score() == 0
    assert not enemy.take_damage(1)
    tilemap, collision = floor_world()
    from entities.enemy import EnemyUpdateContext

    context = EnemyUpdateContext(
        pygame.Rect(), pygame.Vector2(), collision, tilemap, lambda projectile: None, lambda p: p
    )
    for _ in range(40):
        enemy.update(1 / 60, context)
    assert not enemy.active


def test_player_enemy_damage_uses_invulnerability_and_knockback() -> None:
    player = Player((100, 100))
    first = player.apply_damage(1, DamageSource.ENEMY, pygame.Vector2(-300, -400))
    second = player.apply_damage(1, DamageSource.ENEMY, pygame.Vector2(300, -400))
    assert first.applied and not first.died
    assert not second.applied
    assert player.health == 2
    assert player.velocity == pygame.Vector2(-300, -400)
    assert player.invulnerability_timer > 1.0


def test_normal_stomp_kills_once_and_armored_stomp_only_bounces() -> None:
    tilemap, collision = floor_world()
    progress = LevelProgress.from_types([])
    projectiles = ProjectileManager()
    player = Player((205, 220))
    player.velocity.y = 400
    player.previous_rect = pygame.Rect(205, 195, player.rect.width, player.rect.height)

    crawler_spawn = EnemySpawn("c", EnemyType.CRAWLER, (200, 264), {})
    manager = EnemyManager((crawler_spawn,), projectiles)
    outcome = manager.update(
        0.0, pygame.Rect(0, 0, 1000, 500), player, collision, tilemap, progress
    )
    assert not manager.enemies[0].alive
    assert outcome.score_awarded == 200 and progress.score == 200
    assert player.velocity.y == -PLAYER_STOMP_BOUNCE_SPEED

    armored_spawn = EnemySpawn("a", EnemyType.ARMORED, (200, 250), {})
    manager = EnemyManager((armored_spawn,), ProjectileManager())
    player.position.update(205, 210)
    player.sync_rect()
    player.previous_rect = pygame.Rect(205, 180, player.rect.width, player.rect.height)
    player.velocity.y = 400
    manager.update(0.0, pygame.Rect(0, 0, 1000, 500), player, collision, tilemap, progress)
    armored = manager.enemies[0]
    assert armored.alive and armored.health == armored.max_health
    assert player.velocity.y == -PLAYER_STOMP_BOUNCE_SPEED


def test_projectile_faction_lifetime_and_terrain_cleanup() -> None:
    tilemap, _ = floor_world()
    manager = ProjectileManager()
    projectile = Projectile(
        "bolt", (100, 100), pygame.Vector2(100, 0), 1, Faction.ENEMY, lifetime=0.05
    )
    manager.spawn(projectile)
    manager.update(0.06, tilemap)
    assert manager.projectiles == []
    assert projectile.faction is Faction.ENEMY

    terrain_hit = Projectile(
        "bolt2", (100, 270), pygame.Vector2(0, 500), 1, Faction.ENEMY, lifetime=2
    )
    manager.spawn(terrain_hit)
    manager.update(0.1, tilemap)
    assert manager.projectiles == []


def test_crawler_reverses_at_platform_edge_without_vibration() -> None:
    tilemap = TileMap.from_data(
        {
            "width": 12,
            "height": 8,
            "tile_size": 50,
            "tiles": [{"id": 1, "position": [2, 6], "size": [5, 1]}],
        }
    )
    collision = CollisionEngine(tilemap)
    manager = EnemyManager(
        (EnemySpawn("edge", EnemyType.CRAWLER, (150, 264), {}),),
        ProjectileManager(),
    )
    player = Player((500, 100))
    progress = LevelProgress.from_types([])
    facings: set[int] = set()
    for _ in range(360):
        manager.update(
            1 / 60,
            pygame.Rect(0, 0, 600, 400),
            player,
            collision,
            tilemap,
            progress,
        )
        facings.add(manager.enemies[0].facing)
    enemy = manager.enemies[0]
    assert facings == {-1, 1}
    assert 95 <= enemy.rect.left <= 350


def test_turret_only_fires_inside_detection_radius() -> None:
    tilemap, collision = floor_world()
    manager = EnemyManager(
        (EnemySpawn("turret", EnemyType.TURRET, (300, 244), {"attack_cooldown": 0.2}),),
        ProjectileManager(),
    )
    player = Player((900, 238))
    progress = LevelProgress.from_types([])
    for _ in range(30):
        manager.update(1 / 60, pygame.Rect(0, 0, 1000, 500), player, collision, tilemap, progress)
    assert manager.projectiles.projectiles == []
    player.reposition((500, 238))
    for _ in range(30):
        manager.update(1 / 60, pygame.Rect(0, 0, 1000, 500), player, collision, tilemap, progress)
    assert manager.projectiles.projectiles
    assert all(projectile.faction is Faction.ENEMY for projectile in manager.projectiles.projectiles)
