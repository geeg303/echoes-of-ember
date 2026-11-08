"""`all_of` unlock requirements: a route opens only when every listed condition holds (World 4 branches)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from world.world_map import (
    ConnectionState,
    MapDefinitionError,
    RequirementType,
    WorldMapDefinition,
    WorldMapRuntime,
    requirement_leaves,
)

LEVELS = ("branch_a", "branch_b", "branch_c", "finale")


def _map(final_unlock: dict) -> dict:
    nodes = [{"id": "gate", "type": "start", "title": "Gate", "x": 100, "y": 100}]
    for index, level_id in enumerate(LEVELS):
        nodes.append(
            {"id": f"node_{level_id}", "type": "level", "level_id": level_id, "x": 200 + 100 * index, "y": 200}
        )
    nodes.append({"id": "goal", "type": "world_goal", "title": "Goal", "x": 900, "y": 100})
    connections = [
        {"id": f"to_{level_id}", "from": "gate", "to": f"node_{level_id}", "unlock": {"type": "always"}}
        for level_id in LEVELS[:3]
    ]
    connections.append({"id": "to_finale", "from": "gate", "to": "node_finale", "unlock": final_unlock})
    connections.append(
        {
            "id": "to_goal",
            "from": "node_finale",
            "to": "goal",
            "unlock": {"type": "level_complete", "level_id": "finale"},
        }
    )
    return {"start_node": "gate", "nodes": nodes, "connections": connections}


ALL_BRANCHES = {
    "type": "all_of",
    "requirements": [{"type": "level_complete", "level_id": level_id} for level_id in LEVELS[:3]],
}


def _progress(completed: set[str]) -> SimpleNamespace:
    return SimpleNamespace(
        completed_levels_once=completed,
        discovered_secret_exits=set(),
        defeated_bosses=set(),
        results={},
        world_completed_once=False,
    )


def _finale_state(completed: set[str]) -> ConnectionState:
    definition = WorldMapDefinition.from_data(_map(ALL_BRANCHES), LEVELS)
    runtime = WorldMapRuntime(definition, _progress(completed))
    connection = next(item for item in definition.connections if item.connection_id == "to_finale")
    return runtime.connection_state(connection)


def test_all_of_parses_nested_requirements() -> None:
    definition = WorldMapDefinition.from_data(_map(ALL_BRANCHES), LEVELS)
    unlock = next(item for item in definition.connections if item.connection_id == "to_finale").unlock
    assert unlock.kind is RequirementType.ALL_OF
    assert [item.level_id for item in unlock.requirements] == ["branch_a", "branch_b", "branch_c"]


@pytest.mark.parametrize("completed", [set(), {"branch_a"}, {"branch_a", "branch_c"}, {"branch_b", "branch_c"}])
def test_all_of_stays_locked_until_every_branch_is_complete(completed: set[str]) -> None:
    assert _finale_state(completed) is ConnectionState.LOCKED


@pytest.mark.parametrize("order", [("branch_a", "branch_b", "branch_c"), ("branch_c", "branch_a", "branch_b")])
def test_all_of_opens_in_any_completion_order(order: tuple[str, ...]) -> None:
    assert _finale_state(set(order)) is ConnectionState.AVAILABLE


def test_all_of_can_nest() -> None:
    nested = {"type": "all_of", "requirements": [ALL_BRANCHES, {"type": "always"}]}
    definition = WorldMapDefinition.from_data(_map(nested), LEVELS)
    runtime = WorldMapRuntime(definition, _progress(set(LEVELS[:3])))
    connection = next(item for item in definition.connections if item.connection_id == "to_finale")
    assert runtime.connection_state(connection) is ConnectionState.AVAILABLE


@pytest.mark.parametrize(
    "bad",
    [
        {"type": "all_of"},
        {"type": "all_of", "requirements": []},
        {"type": "all_of", "requirements": "branch_a"},
        {"type": "all_of", "requirements": [{"type": "level_complete", "level_id": "missing_level"}]},
        {"type": "all_of", "requirements": [{"type": "not_a_rule"}]},
    ],
)
def test_malformed_all_of_is_rejected(bad: dict) -> None:
    with pytest.raises(MapDefinitionError):
        WorldMapDefinition.from_data(_map(bad), LEVELS)


def test_requirement_leaves_flattens_nested_rules() -> None:
    nested = {"type": "all_of", "requirements": [ALL_BRANCHES, {"type": "always"}]}
    definition = WorldMapDefinition.from_data(_map(nested), LEVELS)
    unlock = next(item for item in definition.connections if item.connection_id == "to_finale").unlock
    kinds = [item.kind for item in requirement_leaves(unlock)]
    assert kinds == [RequirementType.LEVEL_COMPLETE] * 3 + [RequirementType.ALWAYS]


def _verdant_with_wrapped_veil():
    """Verdant Reaches, but the Ember Veil route requires its secret exit inside an all_of rule."""
    from dataclasses import replace

    from world.campaign import DEFAULT_WORLD_REGISTRY, WorldRegistry
    from world.world_map import UnlockRequirement

    registry = WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
    connections = []
    for connection in registry.map_definition.connections:
        if connection.unlock.kind is RequirementType.SECRET_EXIT_DISCOVERED:
            wrapped = UnlockRequirement(
                RequirementType.ALL_OF,
                requirements=(connection.unlock, UnlockRequirement(RequirementType.ALWAYS)),
            )
            connection = replace(connection, unlock=wrapped)
        connections.append(connection)
    return replace(registry, map_definition=replace(registry.map_definition, connections=tuple(connections)))


def _secret_result():
    from systems.level_completion import CompletionRating, ExitType, LevelResult

    return LevelResult(
        "verdant_04",
        True,
        10.0,
        100,
        1,
        68,
        0,
        4,
        0,
        1,
        0,
        10,
        0,
        3,
        3,
        1,
        CompletionRating.BRONZE,
        1,
        4,
        0,
        ExitType.SECRET,
        "v04_secret_exit",
    )


def test_nested_secret_exit_still_reveals_its_map_node() -> None:
    from world.campaign import WorldProgress

    progress = WorldProgress(_verdant_with_wrapped_veil())
    progress.record(_secret_result())
    assert "ember_veil" in progress.revealed_map_nodes


def test_nested_secret_exit_is_accepted_by_save_validation() -> None:
    from systems.save_data import SaveSession

    registry = _verdant_with_wrapped_veil()
    session = SaveSession.fresh(1, registry)
    session.progress.record(_secret_result())
    restored = SaveSession.from_dict(session.to_dict(), registry, 1)
    assert ("verdant_04", "v04_secret_exit") in restored.progress.discovered_secret_exits
