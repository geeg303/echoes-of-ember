"""Reload-driven World 1 campaign and secret-route scenarios."""
from __future__ import annotations

import pytest

from systems.level_completion import ExitType
from tests.helpers import campaign_result
from world.world_map import NodeState, WorldMapRuntime


@pytest.mark.scenario
def test_complete_world_one_with_reload_between_every_stage(isolated_save_manager) -> None:
    manager = isolated_save_manager
    session = manager.new_game(1)
    expected_nodes = ("node_verdant_02", "node_verdant_03", "node_verdant_04", "first_flame_sanctum")
    for index, level_id in enumerate(manager.registry.level_ids[:-1]):
        session.progress.record(campaign_result(level_id, score=(index + 1) * 100))
        manager.save(session)
        session = manager.load(1).session
        assert session is not None
        runtime = WorldMapRuntime(manager.registry.map_definition, session.progress)
        assert runtime.node_state(expected_nodes[index]) is NodeState.AVAILABLE
        assert session.progress.completed_levels_once == set(manager.registry.level_ids[: index + 1])
    session.progress.record_boss_defeat("ashen_warden", campaign_result("verdant_boss", score=5000, exit_id="ashen_warden"))
    manager.save(session)
    restored = manager.load(1).session
    assert restored is not None
    assert restored.progress.complete
    assert restored.progress.defeated_bosses == {"ashen_warden"}
    assert restored.progress.completed_levels_once == set(manager.registry.level_ids)
    assert restored.progress.score == 6000


@pytest.mark.scenario
def test_secret_exit_and_normal_replay_remain_monotonic_after_reload(isolated_save_manager) -> None:
    manager = isolated_save_manager
    session = manager.new_game(1)
    session.progress.record(campaign_result("verdant_04", exit_type=ExitType.SECRET, exit_id="v04_secret_exit"))
    manager.save(session)
    restored = manager.load(1).session
    assert restored is not None
    assert "ember_veil" in restored.progress.revealed_map_nodes
    restored.progress.record(campaign_result("verdant_04"))
    manager.save(restored)
    final = manager.load(1).session
    assert final is not None
    assert final.progress.results["verdant_04"].exit_type is ExitType.NORMAL
    assert ("verdant_04", "v04_secret_exit") in final.progress.discovered_secret_exits
    assert "ember_veil" in final.progress.revealed_map_nodes


@pytest.mark.scenario
def test_all_authored_world_secrets_aggregate_without_duplicate_replays(isolated_save_manager) -> None:
    manager = isolated_save_manager
    session = manager.new_game(1)
    total = 0
    counts: dict[str, int] = {}
    for level_id, path in manager.registry.level_paths.items():
        if level_id == "verdant_boss":
            continue
        from world.level import Level
        count = len(Level.load(path).secret_definitions)
        counts[level_id] = count
        total += count
        session.progress.record(campaign_result(level_id, secrets=count))
    assert total == 12
    assert session.progress.secrets == (12, 12)
    session.progress.record(campaign_result("verdant_01", secrets=counts["verdant_01"]))
    assert session.progress.secrets == (12, 12)
