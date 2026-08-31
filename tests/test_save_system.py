"""Versioned slots, atomic writes, recovery, validation, and progression persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.save_manager import SaveManager, SlotState
from core.game import Game
from systems.level_completion import CompletionRating, ExitType, LevelResult
from systems.save_data import CURRENT_SAVE_VERSION, SaveSession, SaveValidationError
from world.campaign import DEFAULT_WORLD_REGISTRY, WorldRegistry
from world.world_map import NodeState, WorldMapRuntime


@pytest.fixture
def registry() -> WorldRegistry:
    return WorldRegistry.load(DEFAULT_WORLD_REGISTRY)


@pytest.fixture
def manager(tmp_path: Path, registry: WorldRegistry) -> SaveManager:
    return SaveManager(registry, tmp_path)


def result(level_id: str, score: int = 100, exit_type: ExitType = ExitType.NORMAL, exit_id: str = "ember_gate") -> LevelResult:
    return LevelResult(
        level_id, True, 12.5, score, 3, 10, 1, 3, 1, 1, 2, 4,
        1, 2, 3, 1, CompletionRating.SILVER, 2, 3, 1, exit_type, exit_id,
    )


def test_new_game_writes_versioned_readable_json(manager: SaveManager) -> None:
    session = manager.new_game(1)
    path = manager.save_root / "slot_1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema_version"] == CURRENT_SAVE_VERSION
    assert data["campaign"]["current_map_node"] == "starting_grove"
    assert data["campaign"]["level_results"] == {}
    assert session.progress.completed_levels_once == set()
    assert len(path.read_bytes()) < 10_000


def test_round_trip_preserves_results_progression_and_metadata(manager: SaveManager) -> None:
    session = manager.new_game(1)
    session.progress.record(result("verdant_01", 1234))
    session.current_map_node = "node_verdant_01"
    session.play_time_seconds = 83.25
    created = session.created_at
    manager.save(session)
    loaded = manager.load(1).session
    assert loaded is not None
    assert loaded.created_at == created
    assert loaded.play_time_seconds == pytest.approx(83.25)
    assert loaded.current_map_node == "node_verdant_01"
    assert loaded.progress.results["verdant_01"] == result("verdant_01", 1234)
    runtime = WorldMapRuntime(manager.registry.map_definition, loaded.progress)
    assert runtime.node_state("node_verdant_02") is NodeState.AVAILABLE


def test_three_slots_are_independent(manager: SaveManager) -> None:
    first = manager.new_game(1)
    second = manager.new_game(2)
    manager.new_game(3)
    for level_id in manager.registry.level_ids:
        first.progress.record(result(level_id))
    first.progress.record_boss_defeat("ashen_warden", result("verdant_boss"))
    second.progress.record(result("verdant_01"))
    manager.save(first)
    manager.save(second)
    assert manager.load(1).session.progress.world_completed_once
    assert manager.load(2).session.progress.completed_levels_once == {"verdant_01"}
    assert manager.load(3).session.progress.completed_levels_once == set()


def test_new_game_refuses_silent_overwrite_and_delete_is_slot_scoped(manager: SaveManager) -> None:
    manager.new_game(1)
    manager.new_game(2)
    with pytest.raises(FileExistsError):
        manager.new_game(1)
    manager.delete(1)
    assert manager.inspect_slot(1).state is SlotState.EMPTY
    assert manager.inspect_slot(2).state is SlotState.VALID


def test_replacement_creates_last_known_good_backup(manager: SaveManager) -> None:
    session = manager.new_game(1)
    session.play_time_seconds = 10
    manager.save(session)
    session.play_time_seconds = 20
    manager.save(session)
    backup = json.loads((manager.save_root / "slot_1.json.bak").read_text())
    primary = json.loads((manager.save_root / "slot_1.json").read_text())
    assert backup["metadata"]["play_time_seconds"] == 10
    assert primary["metadata"]["play_time_seconds"] == 20


def test_corrupt_primary_recovers_valid_backup(manager: SaveManager) -> None:
    session = manager.new_game(1)
    session.progress.record(result("verdant_01"))
    manager.save(session)
    manager.save(session)
    (manager.save_root / "slot_1.json").write_text("{broken", encoding="utf-8")
    outcome = manager.load(1)
    assert outcome.state is SlotState.RECOVERED
    assert outcome.session is not None
    assert "verdant_01" in outcome.session.progress.completed_levels_once


def test_missing_primary_can_recover_backup(manager: SaveManager) -> None:
    session = manager.new_game(1)
    manager.save(session)
    (manager.save_root / "slot_1.json").unlink()
    assert manager.load(1).state is SlotState.RECOVERED


def test_corrupt_primary_and_backup_are_reported_without_deletion(manager: SaveManager) -> None:
    primary = manager.save_root / "slot_1.json"
    backup = manager.save_root / "slot_1.json.bak"
    primary.write_text("bad", encoding="utf-8")
    backup.write_text("also bad", encoding="utf-8")
    outcome = manager.load(1)
    assert outcome.state is SlotState.CORRUPT and outcome.session is None
    assert primary.exists() and backup.exists()


def test_future_version_is_unsupported_and_untouched(manager: SaveManager) -> None:
    path = manager.save_root / "slot_1.json"
    raw = {"schema_version": CURRENT_SAVE_VERSION + 1}
    path.write_text(json.dumps(raw), encoding="utf-8")
    before = path.read_bytes()
    assert manager.load(1).state is SlotState.UNSUPPORTED_VERSION
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "mutation",
    [
        lambda data: data.pop("schema_version"),
        lambda data: data["metadata"].update(play_time_seconds=-1),
        lambda data: data["campaign"].update(active_world_id="unknown"),
        lambda data: data["campaign"].update(current_map_node="unknown"),
        lambda data: data["campaign"]["progression"].update(completed_levels_once=["unknown"]),
        lambda data: data["campaign"]["progression"].update(revealed_map_nodes=["unknown"]),
        lambda data: data["campaign"]["progression"].update(discovered_secret_exits=[{"level_id": "verdant_04", "exit_id": "unknown"}]),
    ],
)
def test_invalid_save_data_is_rejected(manager: SaveManager, mutation) -> None:
    session = SaveSession.fresh(1, manager.registry)
    data = session.to_dict()
    mutation(data)
    with pytest.raises(SaveValidationError):
        SaveSession.from_dict(data, manager.registry, 1)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("completed", False),
        ("ember_shards_collected", 11),
        ("rare_crystals_collected", 4),
        ("secret_tokens_collected", 2),
        ("enemies_defeated", 5),
        ("secrets_discovered", 4),
        ("secret_rooms_completed", 4),
    ],
)
def test_impossible_level_results_are_rejected(
    manager: SaveManager, field: str, value: object
) -> None:
    session = SaveSession.fresh(1, manager.registry)
    session.progress.record(result("verdant_01"))
    data = session.to_dict()
    data["campaign"]["level_results"]["verdant_01"][field] = value
    with pytest.raises(SaveValidationError):
        SaveSession.from_dict(data, manager.registry, 1)


def test_stale_temp_is_ignored_and_removed_during_inspection(manager: SaveManager) -> None:
    manager.new_game(1)
    temp = manager.save_root / "slot_1.json.tmp"
    temp.write_text('{"untrusted": true}', encoding="utf-8")
    assert manager.inspect_slot(1).state is SlotState.VALID
    assert not temp.exists()


def test_secret_exit_survives_save_load_and_normal_replay(manager: SaveManager) -> None:
    session = manager.new_game(1)
    session.progress.record(result("verdant_04", exit_type=ExitType.SECRET, exit_id="v04_secret_exit"))
    manager.save(session)
    loaded = manager.load(1).session
    assert loaded is not None and "ember_veil" in loaded.progress.revealed_map_nodes
    loaded.progress.record(result("verdant_04", exit_type=ExitType.NORMAL))
    manager.save(loaded)
    reloaded = manager.load(1).session
    assert reloaded.progress.results["verdant_04"].exit_type is ExitType.NORMAL
    assert ("verdant_04", "v04_secret_exit") in reloaded.progress.discovered_secret_exits
    assert "ember_veil" in reloaded.progress.revealed_map_nodes


def test_world_completion_and_sanctum_restore(manager: SaveManager) -> None:
    session = manager.new_game(1)
    for level_id in manager.registry.level_ids:
        session.progress.record(result(level_id))
    session.progress.record_boss_defeat("ashen_warden", result("verdant_boss"))
    manager.save(session)
    loaded = manager.load(1).session
    assert loaded.progress.world_completed_once
    runtime = WorldMapRuntime(manager.registry.map_definition, loaded.progress)
    assert runtime.node_state("first_flame_sanctum") is NodeState.COMPLETED


def test_slot_summary_is_lightweight_and_derived(manager: SaveManager) -> None:
    session = manager.new_game(1)
    session.progress.record(result("verdant_01", 900))
    manager.save(session)
    summary = manager.inspect_slot(1)
    assert summary.state is SlotState.VALID
    assert summary.levels_completed == 1 and summary.score == 900
    assert manager.inspect_slot(2).state is SlotState.EMPTY


@pytest.mark.parametrize("slot", [0, 4, -1, True])
def test_invalid_slot_ids_never_construct_paths(manager: SaveManager, slot) -> None:
    with pytest.raises(ValueError):
        manager.inspect_slot(slot)



def _complete_current_level(game: Game, secret: bool = False) -> None:
    if secret:
        definition = next(item for item in game.level.secret_definitions if item.secret_id == "v04_secret_exit")
        game.player.reposition((definition.bounds[0] + 10, definition.bounds[1] + 10))
    else:
        game.player.reposition((game.goal.rect.x + 10, game.goal.rect.bottom - game.player.rect.height))
    game._interact_pressed = True
    game.update(0)
    game.update(2)


def test_game_completion_autosaves_and_restart_unlocks_map(manager: SaveManager) -> None:
    game = Game(start_on_map=True, save_manager=manager, persistence=True, slot_id=1)
    try:
        game.world_map_runtime.return_to_level_node("verdant_01")
        game.load_level("verdant_01")
        _complete_current_level(game)
        game.return_to_world_map()
    finally:
        game.shutdown()
    restored = Game(start_on_map=True, save_manager=manager, persistence=True, slot_id=1)
    try:
        assert restored.world_map_runtime.current_node_id == "node_verdant_01"
        assert restored.world_map_runtime.node_state("node_verdant_02") is NodeState.AVAILABLE
    finally:
        restored.shutdown()


def test_game_secret_then_normal_replay_persists_branch_across_restarts(manager: SaveManager) -> None:
    game = Game(start_on_map=True, save_manager=manager, persistence=True, slot_id=1)
    try:
        game.world_map_runtime.return_to_level_node("verdant_04")
        game.load_level("verdant_04")
        _complete_current_level(game, secret=True)
        game.return_to_world_map()
    finally:
        game.shutdown()
    replay = Game(start_on_map=True, save_manager=manager, persistence=True, slot_id=1)
    try:
        assert replay.world_map_runtime.node_state("ember_veil") is NodeState.AVAILABLE
        replay.load_level("verdant_04")
        _complete_current_level(replay)
        replay.return_to_world_map()
    finally:
        replay.shutdown()
    restored = manager.load(1).session
    assert restored.progress.results["verdant_04"].exit_type is ExitType.NORMAL
    assert ("verdant_04", "v04_secret_exit") in restored.progress.discovered_secret_exits
    assert "ember_veil" in restored.progress.revealed_map_nodes


def test_direct_debug_game_never_creates_or_changes_slot(manager: SaveManager) -> None:
    game = Game(level_id="verdant_03", save_manager=manager, persistence=False, slot_id=1)
    try:
        _complete_current_level(game)
    finally:
        game.shutdown()
    assert manager.inspect_slot(1).state is SlotState.EMPTY


def test_play_time_adds_incrementally_without_duplicate_accumulation(manager: SaveManager) -> None:
    game = Game(start_on_map=True, save_manager=manager, persistence=True, slot_id=1)
    try:
        game.update(2.5)
        game._mark_save_dirty()
        game._autosave()
        first = manager.load(1).session.play_time_seconds
        game.update(1.5)
        game._mark_save_dirty()
        game._autosave()
        second = manager.load(1).session.play_time_seconds
        assert first == pytest.approx(2.5)
        assert second == pytest.approx(4.0)
    finally:
        game.shutdown()

def test_abandoned_replay_preserves_previous_persistent_result(manager: SaveManager) -> None:
    session = manager.new_game(1)
    session.progress.record(result("verdant_01", 4321))
    manager.save(session)
    game = Game(start_on_map=True, save_manager=manager, persistence=True, slot_id=1)
    try:
        game.load_level("verdant_01")
        game.progress.score = 99999
        game.return_to_world_map()
    finally:
        game.shutdown()
    restored = manager.load(1).session
    assert restored is not None
    assert restored.progress.results["verdant_01"].score == 4321


def test_valid_primary_is_preferred_over_older_backup(manager: SaveManager) -> None:
    session = manager.new_game(1)
    session.play_time_seconds = 10
    manager.save(session)
    session.play_time_seconds = 20
    manager.save(session)
    outcome = manager.load(1)
    assert outcome.state is SlotState.VALID
    assert outcome.session is not None
    assert outcome.session.play_time_seconds == pytest.approx(20)

def test_level_result_exit_id_must_match_authored_content(manager: SaveManager) -> None:
    session = SaveSession.fresh(1, manager.registry)
    session.progress.record(result("verdant_04"))
    data = session.to_dict()
    saved = data["campaign"]["level_results"]["verdant_04"]
    saved["exit_type"] = ExitType.SECRET.value
    saved["exit_id"] = "unknown_secret_exit"
    with pytest.raises(SaveValidationError):
        SaveSession.from_dict(data, manager.registry, 1)

def test_v1_migration_preserves_progress_but_revokes_legacy_world_completion(manager: SaveManager) -> None:
    session = SaveSession.fresh(1, manager.registry)
    for level_id in manager.registry.level_ids[:4]:
        session.progress.record(result(level_id))
    session.progress.record(result("verdant_04", exit_type=ExitType.SECRET, exit_id="v04_secret_exit"))
    session.current_map_node = "first_flame_sanctum"
    session.play_time_seconds = 4321.5
    data = session.to_dict()
    data["schema_version"] = 1
    progression = data["campaign"]["progression"]
    progression.pop("defeated_bosses")
    progression["completed_worlds_once"] = ["verdant_reaches"]
    path = manager.save_root / "slot_1.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    loaded = manager.load(1)
    assert loaded.state is SlotState.VALID and loaded.session is not None
    migrated = loaded.session
    assert migrated.play_time_seconds == pytest.approx(4321.5)
    assert set(manager.registry.level_ids[:4]) <= migrated.progress.completed_levels_once
    assert ("verdant_04", "v04_secret_exit") in migrated.progress.discovered_secret_exits
    assert "ember_veil" in migrated.progress.revealed_map_nodes
    assert migrated.progress.defeated_bosses == set()
    assert not migrated.progress.world_completed_once
    runtime = WorldMapRuntime(manager.registry.map_definition, migrated.progress)
    assert runtime.node_state("first_flame_sanctum") is NodeState.AVAILABLE
    manager.save(migrated)
    assert json.loads(path.read_text())["schema_version"] == 2


def test_boss_defeat_and_true_world_completion_round_trip(manager: SaveManager) -> None:
    session = manager.new_game(1)
    for level_id in manager.registry.level_ids[:4]:
        session.progress.record(result(level_id))
    boss_result = result("verdant_boss", exit_id="ashen_warden")
    session.progress.record_boss_defeat("ashen_warden", boss_result)
    session.current_map_node = "first_flame_sanctum"
    manager.save(session)
    restored = manager.load(1).session
    assert restored is not None
    assert restored.progress.results["verdant_boss"] == boss_result
    assert restored.progress.defeated_bosses == {"ashen_warden"}
    assert restored.progress.world_completed_once
    runtime = WorldMapRuntime(manager.registry.map_definition, restored.progress)
    assert runtime.node_state("first_flame_sanctum") is NodeState.COMPLETED
    assert runtime.node_state("verdant_beacon") is NodeState.COMPLETED


def test_boss_progression_is_isolated_across_three_slots(manager: SaveManager) -> None:
    first = manager.new_game(1)
    for level_id in manager.registry.level_ids[:4]:
        first.progress.record(result(level_id))
    first.progress.record_boss_defeat("ashen_warden", result("verdant_boss", exit_id="ashen_warden"))
    manager.save(first)
    second = manager.new_game(2)
    second.progress.record(result("verdant_04")); manager.save(second)
    manager.new_game(3)
    assert manager.load(1).session.progress.world_completed_once
    assert not manager.load(2).session.progress.world_completed_once
    assert manager.load(2).session.progress.defeated_bosses == set()
    assert manager.load(3).session.progress.completed_levels_once == set()


def test_v2_rejects_world_complete_without_defeated_boss(manager: SaveManager) -> None:
    data = SaveSession.fresh(1, manager.registry).to_dict()
    data["campaign"]["progression"]["completed_worlds_once"] = ["verdant_reaches"]
    with pytest.raises(SaveValidationError, match="defeated bosses"):
        SaveSession.from_dict(data, manager.registry, 1)

