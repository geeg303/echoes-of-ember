"""Authored graph, navigation, monotonic progression, and map integration."""

from __future__ import annotations

import copy
import json

import pygame
import pytest

from core.game import Game
from systems.level_completion import CompletionRating, ExitType, LevelResult
from world.campaign import DEFAULT_WORLD_REGISTRY, WorldProgress, WorldRegistry
from world.world_map import (
    ConnectionState,
    MapDefinitionError,
    NodeState,
    WorldMapDefinition,
    WorldMapRuntime,
)


def result(
    level_id: str,
    score: int = 100,
    exit_type: ExitType = ExitType.NORMAL,
    exit_id: str = "ember_gate",
) -> LevelResult:
    return LevelResult(
        level_id, True, 10, score, 1, 10, 0, 3, 0, 1, 1, 4,
        0, 3, 3, 0, CompletionRating.BRONZE, 0, 2, 0, exit_type, exit_id,
    )


def map_data() -> dict[str, object]:
    return json.loads(DEFAULT_WORLD_REGISTRY.read_text(encoding="utf-8"))["map"]


def test_world_map_definition_preserves_authored_graph() -> None:
    registry = WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
    definition = registry.map_definition
    assert definition.start_node == "starting_grove"
    assert len(definition.nodes) == 8
    assert [item.connection_id for item in definition.connections] == [
        "grove_to_01", "route_01_02", "route_02_03", "route_03_04",
        "route_04_goal", "route_04_secret", "sanctum_to_beacon",
    ]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda data: data["nodes"].append(copy.deepcopy(data["nodes"][0])), "duplicate map node"),
        (lambda data: data["nodes"][0].update(type="shop"), "unknown node type"),
        (lambda data: data["nodes"][1].update(level_id="missing"), "unknown level"),
        (lambda data: data.update(start_node="missing"), "start_node"),
        (lambda data: data["connections"][0].update(to="missing"), "missing node"),
        (lambda data: data["connections"][0].update(waypoints=[[1]]), "malformed waypoint"),
        (lambda data: data["connections"][0].update(unlock={"type": "coins"}), "invalid unlock"),
        (lambda data: next(item for item in data["connections"] if item["id"] == "route_04_secret")["unlock"].update(exit_id="missing"), "unknown secret exit"),
        (lambda data: data["connections"][-1]["unlock"].update(boss_id="missing"), "unknown boss"),
    ],
)
def test_map_validation_rejects_malformed_graph(mutation, message: str) -> None:
    data = map_data()
    mutation(data)
    with pytest.raises(MapDefinitionError, match=message):
        WorldMapDefinition.from_data(data, ("verdant_01", "verdant_02", "verdant_03", "verdant_04", "verdant_boss"), {("verdant_04", "v04_secret_exit")})


def test_initial_node_and_connection_states() -> None:
    registry = WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
    runtime = WorldMapRuntime(registry.map_definition, WorldProgress(registry))
    assert runtime.node_state("node_verdant_01") is NodeState.AVAILABLE
    assert runtime.node_state("node_verdant_02") is NodeState.LOCKED
    assert runtime.node_state("ember_veil") is NodeState.HIDDEN
    assert runtime.node_state("first_flame_sanctum") is NodeState.LOCKED


def test_unlock_sequence_and_world_landmark_are_data_driven() -> None:
    registry = WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
    progress = WorldProgress(registry)
    runtime = WorldMapRuntime(registry.map_definition, progress)
    for completed, unlocked in zip(registry.level_ids[:4], registry.level_ids[1:4]):
        progress.record(result(completed))
        node_id = next(node.node_id for node in registry.map_definition.nodes.values() if node.level_id == unlocked)
        assert runtime.node_state(node_id) is NodeState.AVAILABLE
    progress.record(result("verdant_04"))
    assert runtime.node_state("first_flame_sanctum") is NodeState.AVAILABLE
    assert not progress.world_completed_once
    progress.record_boss_defeat("ashen_warden", result("verdant_boss"))
    assert runtime.node_state("first_flame_sanctum") is NodeState.COMPLETED
    assert runtime.node_state("verdant_beacon") is NodeState.COMPLETED
    assert progress.world_completed_once


def test_map_travel_follows_waypoints_and_ends_exactly() -> None:
    registry = WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
    runtime = WorldMapRuntime(registry.map_definition, WorldProgress(registry), travel_speed=1000)
    assert runtime.choose_direction(pygame.Vector2(1, 0))
    assert runtime.travelling
    for _ in range(20):
        runtime.update(0.1)
    assert runtime.current_node_id == "node_verdant_01"
    assert runtime.avatar_position == pygame.Vector2(registry.map_definition.nodes["node_verdant_01"].position)
    locked = next(item for item in registry.map_definition.connections if item.connection_id == "route_01_02")
    assert runtime.connection_state(locked) is ConnectionState.LOCKED
    assert not runtime.choose_direction(pygame.Vector2(1, -1))


def test_progression_is_monotonic_while_latest_result_replaces() -> None:
    registry = WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
    progress = WorldProgress(registry)
    progress.record(result("verdant_01", 900))
    progress.record(result("verdant_02"))
    progress.record(result("verdant_01", 10))
    assert progress.results["verdant_01"].score == 10
    assert {"verdant_01", "verdant_02"} <= progress.completed_levels_once
    runtime = WorldMapRuntime(registry.map_definition, progress)
    assert runtime.node_state("node_verdant_03") is NodeState.AVAILABLE


def test_secret_branch_remains_after_normal_replay() -> None:
    registry = WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
    progress = WorldProgress(registry)
    progress.record(result("verdant_04", exit_type=ExitType.SECRET, exit_id="v04_secret_exit"))
    runtime = WorldMapRuntime(registry.map_definition, progress)
    assert runtime.node_state("ember_veil") is NodeState.AVAILABLE
    progress.record(result("verdant_04", exit_type=ExitType.NORMAL))
    assert progress.results["verdant_04"].exit_type is ExitType.NORMAL
    assert ("verdant_04", "v04_secret_exit") in progress.discovered_secret_exits
    assert "ember_veil" in progress.revealed_map_nodes
    assert runtime.node_state("ember_veil") is NodeState.AVAILABLE


def test_world_map_secret_placeholder_is_safe() -> None:
    game = Game(start_on_map=True)
    try:
        game.world_progress.record(result("verdant_04", exit_type=ExitType.SECRET, exit_id="v04_secret_exit"))
        game.world_map_runtime.current_node_id = "ember_veil"
        action, level_id = game.world_map_screen.activate_current()
        assert action == "placeholder" and level_id is None
        assert "NOT YET OPEN" in game.world_map_screen.message
    finally:
        game.shutdown()


def test_normal_startup_mode_and_direct_level_bypass() -> None:
    map_game = Game(start_on_map=True)
    direct_game = Game(level_id="verdant_03")
    try:
        assert map_game.app_mode == "map"
        assert not hasattr(map_game, "player")
        assert direct_game.app_mode == "gameplay"
        assert direct_game.level.metadata.level_id == "verdant_03"
    finally:
        map_game.shutdown()
        direct_game.shutdown()

