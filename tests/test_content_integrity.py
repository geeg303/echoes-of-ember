"""Cross-catalog integrity checks for all authored World 1 content."""
from __future__ import annotations

import json
from collections import deque

import pytest

from core.achievement_manager import AchievementProfile
from settings import PROJECT_ROOT
from systems.achievement_system import condition_matches, load_achievement_definitions
from systems.dialogue_system import NodeType, load_dialogue
from tools.validation import load_and_validate_level, validate_narrative_data
from world.campaign import DEFAULT_WORLD_REGISTRY, WorldRegistry


def test_all_authored_object_and_secret_ids_are_unique_per_level() -> None:
    registry = WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
    for level_id, path in registry.level_paths.items():
        data = load_and_validate_level(path)
        ids = [item["id"] for item in data.get("objects", [])]
        secret_ids = [item["id"] for item in data.get("secrets", [])]
        assert len(ids) == len(set(ids)), level_id
        assert len(secret_ids) == len(set(secret_ids)), level_id
        assert set(ids).isdisjoint(secret_ids), level_id


def test_world_map_graph_reaches_every_authored_node() -> None:
    definition = WorldRegistry.load(DEFAULT_WORLD_REGISTRY).map_definition
    adjacent: dict[str, set[str]] = {node: set() for node in definition.nodes}
    for connection in definition.connections:
        adjacent[connection.source].add(connection.target)
        adjacent[connection.target].add(connection.source)
    reached = {definition.start_node}
    pending = deque(reached)
    while pending:
        pending.extend(adjacent[pending.popleft()] - reached)
        reached.update(pending)
    assert reached == set(definition.nodes)


@pytest.mark.parametrize("path", sorted((PROJECT_ROOT / "data" / "dialogue").glob("*.json")))
def test_every_dialogue_node_can_reach_a_terminal(path) -> None:
    definition = load_dialogue(path)
    reverse: dict[str, set[str]] = {node_id: set() for node_id in definition.nodes}
    terminals: set[str] = set()
    for node in definition.nodes.values():
        targets = ({node.next_id} if node.next_id else set()) | {choice.target for choice in node.choices}
        if node.kind is NodeType.END or not targets:
            terminals.add(node.node_id)
        for target in targets:
            reverse[target].add(node.node_id)
    can_finish = set(terminals)
    pending = deque(terminals)
    while pending:
        pending.extend(reverse[pending.popleft()] - can_finish)
        can_finish.update(pending)
    assert can_finish == set(definition.nodes), path.name


def _satisfying_context(condition: dict) -> tuple[AchievementProfile, str, dict]:
    profile = AchievementProfile()
    kind = condition["type"]
    if kind == "event":
        return profile, condition["event"], dict(condition.get("match", {}))
    if kind == "flag":
        profile.flags.add(condition["flag"])
    elif kind == "counter_at_least":
        profile.counters[condition["counter"]] = condition["value"]
    elif kind == "set_contains_all":
        profile.sets[condition["set"]] = set(condition["values"])
    else:
        for child in condition["conditions"]:
            child_profile, event, payload = _satisfying_context(child)
            profile.flags.update(child_profile.flags)
            profile.counters.update(child_profile.counters)
            profile.sets.update(child_profile.sets)
            if condition["type"] == "any_of":
                return profile, event, payload
        return profile, event, payload
    return profile, "controlled_test", {}


def test_every_achievement_definition_has_a_satisfiable_condition() -> None:
    definitions = load_achievement_definitions(PROJECT_ROOT / "data" / "achievements" / "achievements.json")
    assert len(definitions) == 19
    for definition in definitions:
        profile, event, payload = _satisfying_context(definition.condition)
        assert condition_matches(definition.condition, profile, event, payload), definition.id


@pytest.mark.parametrize(
    "achievement_id",
    [item.id for item in load_achievement_definitions(PROJECT_ROOT / "data" / "achievements" / "achievements.json")],
)
def test_every_authored_achievement_can_unlock(achievement_id, isolated_achievement_manager) -> None:
    manager = isolated_achievement_manager
    definition = manager.by_id[achievement_id]
    profile, event, payload = _satisfying_context(definition.condition)
    manager.profile.flags.update(profile.flags)
    manager.profile.counters.update(profile.counters)
    manager.profile.sets.update(profile.sets)
    manager.emit(event, **payload)
    assert achievement_id in manager.profile.unlocked


def test_audio_catalog_references_existing_files() -> None:
    catalog = json.loads((PROJECT_ROOT / "data" / "audio" / "audio.json").read_text(encoding="utf-8"))
    for section in ("sounds", "music"):
        for item in catalog[section]:
            assert (PROJECT_ROOT / "assets" / item["path"]).is_file(), item["id"]


def test_narrative_catalog_and_npc_references_validate_together() -> None:
    assert validate_narrative_data(PROJECT_ROOT / "data") == (15, 4)
