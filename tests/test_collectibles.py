"""Collectible pickup, score, health, tracking, totals, and reset behavior."""

from __future__ import annotations

import pygame

from entities.player import Player
from settings import PROJECT_ROOT
from systems.collectible_system import CollectibleManager
from systems.progression import CollectibleType, LevelProgress
from world.level import Level


def loaded_level() -> Level:
    return Level.load(PROJECT_ROOT / "data" / "levels" / "level_01.json")


def progress_for(level: Level) -> LevelProgress:
    return LevelProgress.from_types([spawn.kind for spawn in level.collectible_spawns])


def overlap_player(player: Player, collectible_rect: pygame.Rect) -> None:
    player.position.update(collectible_rect.centerx - player.rect.width / 2, collectible_rect.centery - player.rect.height / 2)
    player.sync_rect()


def test_level_collectible_totals_match_authored_content() -> None:
    level = loaded_level()
    progress = progress_for(level)
    assert progress.total(CollectibleType.EMBER_SHARD) == 52
    assert progress.total(CollectibleType.RARE_CRYSTAL) == 3
    assert progress.total(CollectibleType.SECRET_TOKEN) == 1
    assert progress.total(CollectibleType.HEALTH_ITEM) == 2


def test_ember_shard_scores_once_and_disappears() -> None:
    level = loaded_level()
    manager = CollectibleManager(level.collectible_spawns)
    progress = progress_for(level)
    player = Player(level.player_spawn)
    shard = next(item for item in manager.collectibles if item.kind is CollectibleType.EMBER_SHARD)
    overlap_player(player, shard.pickup_rect)

    first = manager.collect_overlaps(player.rect, player, progress)
    second = manager.collect_overlaps(player.rect, player, progress)
    assert len(first) == 1 and second == ()
    assert not shard.active
    assert progress.count(CollectibleType.EMBER_SHARD) == 1
    assert progress.score == 100


def test_all_collectible_scores_and_separate_tracking() -> None:
    level = loaded_level()
    manager = CollectibleManager(level.collectible_spawns)
    progress = progress_for(level)
    player = Player(level.player_spawn)
    player.take_damage()

    for kind in CollectibleType:
        item = next(collectible for collectible in manager.collectibles if collectible.kind is kind)
        overlap_player(player, item.pickup_rect)
        result = manager.collect_overlaps(player.rect, player, progress)
        assert len(result) == 1 and result[0].kind is kind

    assert player.health == player.max_health
    assert progress.count(CollectibleType.EMBER_SHARD) == 1
    assert progress.count(CollectibleType.RARE_CRYSTAL) == 1
    assert progress.count(CollectibleType.SECRET_TOKEN) == 1
    assert progress.count(CollectibleType.HEALTH_ITEM) == 1
    assert progress.score == 3_600


def test_health_item_waits_when_health_is_full() -> None:
    level = loaded_level()
    manager = CollectibleManager(level.collectible_spawns)
    progress = progress_for(level)
    player = Player(level.player_spawn)
    health_item = next(item for item in manager.collectibles if item.kind is CollectibleType.HEALTH_ITEM)
    overlap_player(player, health_item.pickup_rect)

    assert manager.collect_overlaps(player.rect, player, progress) == ()
    assert health_item.active
    assert progress.count(CollectibleType.HEALTH_ITEM) == 0


def test_full_level_reset_restores_collectibles_and_tracking() -> None:
    level = loaded_level()
    manager = CollectibleManager(level.collectible_spawns)
    progress = progress_for(level)
    player = Player(level.player_spawn)
    item = next(collectible for collectible in manager.collectibles if collectible.kind is CollectibleType.EMBER_SHARD)
    overlap_player(player, item.pickup_rect)
    manager.collect_overlaps(player.rect, player, progress)
    assert manager.active_count == len(level.collectible_spawns) - 1

    manager.reset()
    progress = progress_for(level)
    assert manager.active_count == len(level.collectible_spawns)
    assert progress.score == 0 and not progress.collected_ids


def test_player_health_and_lives_are_bounded() -> None:
    player = Player((0, 0))
    assert player.take_damage() is False
    assert player.health == player.max_health - 1
    player.heal(99)
    assert player.health == player.max_health
    player.take_damage(player.max_health)
    assert player.health == 0
    player.lose_life_and_restore()
    assert player.health == player.max_health
    assert player.lives == 2
