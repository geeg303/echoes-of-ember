"""Metadata, goal, timer, frozen results, completion, and replay tests."""

from __future__ import annotations

import copy
import json

import pygame

from core.game import Game
from entities.level_goal import EmberGate
from systems.level_completion import (
    CompletionRating,
    CompletionRequirements,
    GameplayPhase,
    calculate_rating,
)
from systems.progression import CollectibleType
from tools.validation import validate_level_data


def level_data() -> dict[str, object]:
    with open("data/levels/verdant_01.json", encoding="utf-8") as handle:
        return json.load(handle)


def test_metadata_validation_missing_identity_bad_world_goal_and_requirements() -> None:
    data = level_data()
    invalid = copy.deepcopy(data)
    del invalid["id"]
    invalid["world_id"] = "Bad World!"
    invalid["goal"] = {"type": "finish_flag", "x": 99999, "y": 50}
    invalid["completion_requirements"] = {"reach_goal": "yes", "boss": True}
    errors = validate_level_data(invalid)
    assert any("missing required field: id" in error for error in errors)
    assert any("world_id" in error for error in errors)
    assert any("unsupported type" in error for error in errors)
    assert any("outside level bounds" in error for error in errors)
    assert any("unsupported values" in error for error in errors)


def test_declared_collectible_totals_must_match_derived_content() -> None:
    data = level_data()
    data["shard_total"] = 999
    assert any("shard_total does not match" in error for error in validate_level_data(data))


def test_goal_range_activation_and_one_shot_behavior() -> None:
    gate = EmberGate((500, 500))
    far = pygame.Rect(0, 0, 44, 62)
    near = pygame.Rect(510, 530, 44, 62)
    gate.update(0.1, far)
    assert not gate.nearby and not gate.try_activate(far, True)
    gate.update(0.1, near)
    assert gate.nearby and not gate.try_activate(near, False)
    assert gate.try_activate(near, True)
    assert not gate.try_activate(near, True)


def test_completion_requirement_evaluation() -> None:
    game = Game()
    try:
        requirement = CompletionRequirements(True, 2)
        assert not requirement.evaluate(True, game.progress)
        game.progress.register("one", CollectibleType.EMBER_SHARD)
        game.progress.register("two", CollectibleType.EMBER_SHARD)
        assert requirement.evaluate(True, game.progress)
        assert not requirement.evaluate(False, game.progress)
    finally:
        game.shutdown()


def activate_goal(game: Game) -> None:
    game.player.reposition((game.goal.rect.x + 18, game.goal.rect.bottom - game.player.rect.height - 2))
    game._interact_pressed = True
    game.update(0.0)


def test_timer_stops_result_freezes_and_completion_happens_once() -> None:
    game = Game()
    try:
        game.update(1.25)
        assert game.elapsed_time == 1.25
        game.progress.register("test_shard", CollectibleType.EMBER_SHARD)
        game.enemies.defeated_ids.add("crawler_01")
        game.deaths = 1
        activate_goal(game)
        assert game.gameplay_phase is GameplayPhase.COMPLETION_SEQUENCE
        result = game.level_result
        assert result and result.score == 100 and result.ember_shards_collected == 1
        assert result.enemies_defeated == 1 and result.enemies_total == 10
        assert result.deaths == 1 and result.level_id == "verdant_01"
        frozen_time = game.elapsed_time
        game.progress.award_score(5000)
        game.enemies.defeated_ids.add("flyer_01")
        game.update(2.0)
        assert game.gameplay_phase is GameplayPhase.LEVEL_COMPLETE
        assert game.elapsed_time == frozen_time
        assert game.level_result is result and result.score == 100 and result.enemies_defeated == 1
        assert not game.goal.try_activate(game.player.rect, True)
    finally:
        game.shutdown()


def test_rating_thresholds_are_metadata_driven() -> None:
    game = Game()
    try:
        thresholds = game.level.metadata.ratings
        assert calculate_rating(0, 0, 52, 100, thresholds) is CompletionRating.BRONZE
        assert calculate_rating(thresholds.silver_score, 5, 52, 100, thresholds) is CompletionRating.SILVER
        assert calculate_rating(thresholds.gold_score, 52, 52, thresholds.gold_time, thresholds) is CompletionRating.GOLD
    finally:
        game.shutdown()


def test_replay_reconstructs_every_runtime_counter_and_state() -> None:
    game = Game()
    try:
        game.elapsed_time = 50
        game.deaths = 2
        game.progress.register("test", CollectibleType.EMBER_SHARD)
        game.enemies.defeated_ids.add("crawler_01")
        game.world_objects.activated_checkpoint_ids.add("checkpoint_01")
        activate_goal(game)
        game.reset_level()
        assert game.gameplay_phase is GameplayPhase.PLAYING
        assert game.elapsed_time == 0 and game.deaths == 0 and game.level_result is None
        assert game.progress.score == 0 and not game.enemies.defeated_ids
        assert not game.world_objects.activated_checkpoint_ids
        assert not game.goal.activated and not game.projectiles.projectiles
        assert game.player.lives == 3 and game.player.health == 3
    finally:
        game.shutdown()
