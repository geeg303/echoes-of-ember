"""Secret definition, lifecycle, challenge, exit, and campaign tests."""

from __future__ import annotations

import copy

import pygame

from core.game import Game

from settings import PROJECT_ROOT
from systems.level_completion import CompletionRating, ExitType, GameplayPhase, LevelResult
from systems.secret_system import SecretSystem
from tools.validation import load_and_validate_level, validate_level_data
from world.campaign import DEFAULT_WORLD_REGISTRY, WorldProgress, WorldRegistry
from world.level import Level
from ui.notifications import NotificationQueue
from world.secret_area import SecretDefinition, SecretState, SecretTrigger, SecretType


def definition(
    kind: SecretType = SecretType.CACHE,
    trigger: SecretTrigger = SecretTrigger.ENTER_REGION,
    enemy_ids: tuple[str, ...] = (),
) -> SecretDefinition:
    return SecretDefinition("test_secret", kind, trigger, (100, 100, 120, 100), enemy_ids)


def test_secret_starts_undiscovered_and_rewards_once() -> None:
    system = SecretSystem((definition(),))
    assert system.areas["test_secret"].state is SecretState.UNDISCOVERED
    first = system.update(pygame.Rect(120, 120, 30, 40), False, set())
    second = system.update(pygame.Rect(120, 120, 30, 40), False, set())
    assert first.score_awarded == 250
    assert first.messages == ["SECRET DISCOVERED"]
    assert second.score_awarded == 0
    assert system.discovered_count == 1


def test_challenge_tracks_only_designated_enemies_and_completes_once() -> None:
    system = SecretSystem((definition(SecretType.CHALLENGE, SecretTrigger.DEFEAT_ALL, ("target_a", "target_b")),))
    player = pygame.Rect(120, 120, 30, 40)
    assert system.update(player, False, {"unrelated", "target_a"}).score_awarded == 0
    completed = system.update(player, False, {"unrelated", "target_a", "target_b"})
    repeated = system.update(player, False, {"target_a", "target_b"})
    assert completed.score_awarded == 750
    assert repeated.score_awarded == 0
    assert system.completed_room_count == 1


def test_secret_exit_requires_interact_and_reports_stable_id() -> None:
    system = SecretSystem((definition(SecretType.EXIT, SecretTrigger.INTERACT),))
    player = pygame.Rect(120, 120, 30, 40)
    assert system.update(player, False, set()).secret_exit_id is None
    outcome = system.update(player, True, set())
    assert outcome.secret_exit_id == "test_secret"
    assert system.update(player, True, set()).score_awarded == 0


def test_secret_validation_rejects_unknown_bounds_references_and_exit_trigger() -> None:
    data = load_and_validate_level(PROJECT_ROOT / "data" / "levels" / "verdant_03.json")
    bad = copy.deepcopy(data)
    bad["secrets"][0]["secret_type"] = "mystery"
    assert any("unknown secret type" in error for error in validate_level_data(bad))
    bad = copy.deepcopy(data)
    bad["secrets"][0]["properties"]["bounds"] = [-1, 0, 0, 20]
    assert any("bounds is invalid" in error for error in validate_level_data(bad))
    bad = copy.deepcopy(data)
    bad["secrets"][2]["properties"]["enemy_ids"] = ["missing"]
    assert any("missing challenge enemy" in error for error in validate_level_data(bad))
    bad = copy.deepcopy(load_and_validate_level(PROJECT_ROOT / "data" / "levels" / "verdant_04.json"))
    bad["secrets"][-1]["properties"]["trigger_type"] = "enter_region"
    assert any("secret exit must use interact" in error for error in validate_level_data(bad))


def result(level_id: str, discovered: int, total: int, exit_type: ExitType = ExitType.NORMAL) -> LevelResult:
    return LevelResult(level_id, True, 10, 100, 0, 1, 0, 1, 0, 1, 0, 1, 0, 3, 3, 0, CompletionRating.BRONZE, discovered, total, 0, exit_type)


def test_world_progress_secret_aggregate_replaces_replay() -> None:
    progress = WorldProgress(WorldRegistry.load(DEFAULT_WORLD_REGISTRY))
    progress.record(result("verdant_01", 2, 2))
    progress.record(result("verdant_01", 1, 2, ExitType.SECRET))
    progress.record(result("verdant_02", 3, 3))
    assert progress.secrets == (4, 5)
    assert progress.results["verdant_01"].exit_type is ExitType.SECRET


def test_all_world_levels_have_expected_secret_totals_and_one_secret_exit() -> None:
    registry = WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
    levels = [Level.load(registry.level_paths[level_id]) for level_id in registry.level_ids]
    assert [len(level.secret_definitions) for level in levels] == [2, 3, 3, 4]
    exits = [item for level in levels for item in level.secret_definitions if item.kind is SecretType.EXIT]
    assert len(exits) == 1 and exits[0].secret_id == "v04_secret_exit"



def test_f7_style_reset_reconstructs_secret_state() -> None:
    game = Game(level_id="verdant_01")
    try:
        secret = game.level.secret_definitions[0]
        game.player.reposition((secret.bounds[0] + 10, secret.bounds[1] + 10))
        game.update(0)
        assert game.secrets.discovered_count == 1
        game.reset_level()
        assert game.secrets.discovered_count == 0
    finally:
        game.shutdown()


def test_runtime_secret_exit_freezes_result_and_keeps_campaign_destination() -> None:
    game = Game(level_id="verdant_04")
    try:
        secret_exit = next(item for item in game.level.secret_definitions if item.kind is SecretType.EXIT)
        game.player.reposition((secret_exit.bounds[0] + 10, secret_exit.bounds[1] + 10))
        game._interact_pressed = True
        game.update(0)
        assert game.gameplay_phase is GameplayPhase.COMPLETION_SEQUENCE
        assert game.level_result is not None
        assert game.level_result.exit_type is ExitType.SECRET
        assert game.level_result.exit_id == "v04_secret_exit"
        frozen_score = game.level_result.score
        game.update(2)
        assert game.level_result.score == frozen_score
        game.continue_campaign()
        assert game.gameplay_phase is GameplayPhase.WORLD_COMPLETE
    finally:
        game.shutdown()


def test_notification_queue_state_is_deterministic() -> None:
    queue = NotificationQueue(None)
    queue.push("SECRET DISCOVERED", duration=1.0)
    queue.push("CHALLENGE COMPLETE", duration=1.0)
    queue.update(1.1)
    assert [item.text for item in queue.items] == ["CHALLENGE COMPLETE"]
    queue.clear()
    assert not queue.items
