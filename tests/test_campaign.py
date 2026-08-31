"""World registry, progress aggregation, continue flow, and direct loading."""
from __future__ import annotations
import json
import pygame
import pytest
from core.game import Game
from systems.level_completion import CompletionRating, GameplayPhase, LevelResult
from world.campaign import DEFAULT_WORLD_REGISTRY, WorldProgress, WorldRegistry, WorldRegistryError
from world.level import Level

def result(level_id: str, score: int = 100) -> LevelResult:
    return LevelResult(level_id, True, 10, score, 1, 10, 0, 3, 0, 1, 1, 4, 0, 3, 3, 0, CompletionRating.BRONZE)

def test_registry_is_valid_and_preserves_explicit_order() -> None:
    registry = WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
    assert registry.level_ids == ("verdant_01", "verdant_02", "verdant_03", "verdant_04")
    assert [Level.load(registry.level_paths[item]).metadata.level_id for item in registry.level_ids] == list(registry.level_ids)

def test_registry_rejects_unknown_and_duplicate_references(tmp_path) -> None:
    path = tmp_path / "world.json"
    path.write_text(json.dumps({"id":"verdant_reaches","display_name":"Bad","levels":["missing","missing"]}), encoding="utf-8")
    with pytest.raises(WorldRegistryError, match="duplicate|unknown"):
        WorldRegistry.load(path)

def test_world_progress_replaces_replays_and_aggregates() -> None:
    progress = WorldProgress(WorldRegistry.load(DEFAULT_WORLD_REGISTRY))
    progress.record(result("verdant_01", 100)); progress.record(result("verdant_01", 250)); progress.record(result("verdant_02", 300))
    assert progress.levels_completed == 2 and progress.score == 550
    assert progress.aggregate("ember_shards_collected", "ember_shards_total") == (2, 20)
    assert not progress.complete

def complete(game: Game) -> None:
    game.player.reposition((game.goal.rect.x + 10, game.goal.rect.bottom - game.player.rect.height))
    game._interact_pressed = True; game.update(0); game.update(2)

def test_continue_flow_reaches_world_complete_and_replay_world() -> None:
    game = Game()
    try:
        for expected in ("verdant_01", "verdant_02", "verdant_03", "verdant_04"):
            assert game.level.metadata.level_id == expected
            complete(game)
            assert game.gameplay_phase is GameplayPhase.LEVEL_COMPLETE
            game.continue_campaign()
        assert game.gameplay_phase is GameplayPhase.WORLD_COMPLETE and game.world_progress.complete
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)); game._handle_events()
        assert game.level.metadata.level_id == "verdant_01" and not game.world_progress.results
    finally:
        game.shutdown()

def test_game_can_launch_registered_level_directly() -> None:
    game = Game(level_id="verdant_03")
    try: assert game.level.metadata.level_id == "verdant_03"
    finally: game.shutdown()
