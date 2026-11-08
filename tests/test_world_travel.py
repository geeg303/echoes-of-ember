"""World gates on the map: travelling between worlds in a running game, with per-world saves."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.game import Game
from core.save_manager import SaveManager
from systems.level_completion import CompletionRating, ExitType, LevelResult
from tests.multiworld import WORLD_2, build_two_world_campaign, world_2_map
from world.campaign import CampaignRegistry, WorldRegistryError
from world.world_map import MapDefinitionError, NodeState, NodeType, WorldMapDefinition


def _add_verdant_gate(verdant_map: dict) -> None:
    verdant_map["nodes"].append(
        {
            "id": "glassreach_gate",
            "type": "world_gate",
            "target_world": WORLD_2,
            "title": "To Glassreach",
            "x": 1220,
            "y": 200,
        }
    )
    verdant_map["connections"].append(
        {
            "id": "beacon_to_gate",
            "from": "verdant_beacon",
            "to": "glassreach_gate",
            "unlock": {"type": "world_complete"},
        }
    )


def _world_2_with_return_gate() -> dict:
    return world_2_map(
        extra_nodes=[
            {
                "id": "verdant_gate",
                "type": "world_gate",
                "target_world": "verdant_reaches",
                "title": "Back",
                "x": 120,
                "y": 300,
            }
        ],
        extra_connections=[
            {"id": "landing_to_back", "from": "glass_landing", "to": "verdant_gate", "unlock": {"type": "always"}}
        ],
    )


@pytest.fixture
def campaign(tmp_path: Path) -> CampaignRegistry:
    return CampaignRegistry.load(
        build_two_world_campaign(
            tmp_path, verdant_map_edit=_add_verdant_gate, world_2_map_data=_world_2_with_return_gate()
        )
    )


@pytest.fixture
def manager(tmp_path: Path, campaign: CampaignRegistry) -> SaveManager:
    return SaveManager(campaign, tmp_path / "saves")


def result(level_id: str, exit_id: str = "ember_gate") -> LevelResult:
    return LevelResult(
        level_id, True, 12.5, 100, 3, 10, 1, 3, 1, 1, 2, 4, 1, 2, 3, 1,
        CompletionRating.SILVER, 2, 3, 1, ExitType.NORMAL, exit_id,
    )  # fmt: skip


def _finish_world_1(game: Game) -> None:
    for level_id in ("verdant_01", "verdant_02", "verdant_03", "verdant_04"):
        game.world_progress.record(result(level_id))
    game.world_progress.record_boss_defeat("ashen_warden", result("verdant_boss", "ashen_warden"))


def _campaign_game(campaign, manager, settings, **kwargs) -> Game:
    return Game(
        registry=campaign,
        start_on_map=True,
        save_manager=manager,
        persistence=True,
        slot_id=1,
        settings_manager=settings,
        achievements_enabled=False,
        **kwargs,
    )


# --- data validation -------------------------------------------------------------------------


def test_world_gate_requires_a_target_world() -> None:
    data = world_2_map(extra_nodes=[{"id": "gate", "type": "world_gate", "title": "Gate", "x": 10, "y": 10}])
    with pytest.raises(MapDefinitionError, match="target_world"):
        WorldMapDefinition.from_data(data, ("glass_01", "glass_boss"))


def test_world_gate_cannot_reference_a_level() -> None:
    gate = {
        "id": "gate",
        "type": "world_gate",
        "target_world": "x",
        "level_id": "glass_01",
        "title": "G",
        "x": 1,
        "y": 1,
    }
    with pytest.raises(MapDefinitionError):
        WorldMapDefinition.from_data(world_2_map(extra_nodes=[gate]), ("glass_01", "glass_boss"))


def test_campaign_rejects_gate_to_unknown_world(tmp_path: Path) -> None:
    def bad_gate(verdant_map: dict) -> None:
        _add_verdant_gate(verdant_map)
        verdant_map["nodes"][-1]["target_world"] = "nowhere"

    with pytest.raises(WorldRegistryError, match="nowhere"):
        CampaignRegistry.load(build_two_world_campaign(tmp_path, verdant_map_edit=bad_gate))


def test_campaign_rejects_gate_to_its_own_world(tmp_path: Path) -> None:
    def self_gate(verdant_map: dict) -> None:
        _add_verdant_gate(verdant_map)
        verdant_map["nodes"][-1]["target_world"] = "verdant_reaches"

    with pytest.raises(WorldRegistryError, match="itself"):
        CampaignRegistry.load(build_two_world_campaign(tmp_path, verdant_map_edit=self_gate))


# --- running game -----------------------------------------------------------------------------


def test_gate_is_locked_until_world_1_is_complete(campaign, manager, isolated_settings_manager) -> None:
    game = _campaign_game(campaign, manager, isolated_settings_manager, new_game=True)
    try:
        assert game.world_map_runtime.node_state("glassreach_gate") is NodeState.LOCKED
        assert not game.travel_to_world(WORLD_2)
        assert game.registry.world_id == "verdant_reaches"
    finally:
        game.shutdown()


def test_travel_switches_world_map_theme_and_saves(campaign, manager, isolated_settings_manager) -> None:
    game = _campaign_game(campaign, manager, isolated_settings_manager, new_game=True)
    try:
        _finish_world_1(game)
        game.world_map_runtime.return_to_level_node("verdant_04")
        assert game.world_map_runtime.node_state("glassreach_gate") is NodeState.AVAILABLE
        assert game.travel_to_world(WORLD_2)
        assert game.registry.world_id == WORLD_2
        assert game.world_progress is game.campaign_progress.world(WORLD_2)
        assert game.world_map_runtime.current_node_id == "glass_landing"
        assert game.world_map_screen.theme.land == (118, 160, 184)
    finally:
        game.shutdown()
    raw = json.loads((manager.save_root / "slot_1.json").read_text(encoding="utf-8"))
    assert raw["campaign"]["active_world_id"] == WORLD_2
    assert raw["campaign"]["worlds"]["verdant_reaches"]["current_map_node"] == "node_verdant_04"
    assert raw["campaign"]["worlds"]["verdant_reaches"]["progression"]["world_complete"] is True


def test_confirming_on_a_gate_node_travels(campaign, manager, isolated_settings_manager) -> None:
    import pygame

    game = _campaign_game(campaign, manager, isolated_settings_manager, new_game=True)
    try:
        _finish_world_1(game)
        gate = game.registry.map_definition.nodes["glassreach_gate"]
        game.world_map_runtime.current_node_id = gate.node_id
        game.world_map_runtime.avatar_position.update(gate.position)
        assert game.world_map_screen.activate_current() == ("world_travel", WORLD_2)
        game._handle_map_key(pygame.K_RETURN)
        assert game.registry.world_id == WORLD_2
    finally:
        game.shutdown()


def test_world_2_level_completion_persists_and_resumes_in_world_2(campaign, manager, isolated_settings_manager) -> None:
    game = _campaign_game(campaign, manager, isolated_settings_manager, new_game=True)
    try:
        _finish_world_1(game)
        game.travel_to_world(WORLD_2)
        game.world_map_runtime.return_to_level_node("glass_01")
        game.load_level("glass_01")
        assert game.level.metadata.level_id == "glass_01"
        assert game.background.palette.sky_top == (40, 86, 132)
        game.player.reposition((game.goal.rect.x + 10, game.goal.rect.bottom - game.player.rect.height))
        game._interact_pressed = True
        game.update(0)
        game.update(2)
        game.return_to_world_map()
        assert "glass_01" in game.campaign_progress.world(WORLD_2).completed_levels_once
        assert "glass_01" not in game.campaign_progress.world("verdant_reaches").completed_levels_once
    finally:
        game.shutdown()
    resumed = _campaign_game(campaign, manager, isolated_settings_manager)
    try:
        assert resumed.registry.world_id == WORLD_2
        assert resumed.world_map_runtime.current_node_id == "node_glass_01"
        assert resumed.world_map_runtime.node_state("glass_vault") is NodeState.AVAILABLE
    finally:
        resumed.shutdown()


def test_travel_back_restores_the_previous_world_position(campaign, manager, isolated_settings_manager) -> None:
    game = _campaign_game(campaign, manager, isolated_settings_manager, new_game=True)
    try:
        _finish_world_1(game)
        game.world_map_runtime.return_to_level_node("verdant_02")
        game.travel_to_world(WORLD_2)
        assert game.travel_to_world("verdant_reaches")
        assert game.registry.world_id == "verdant_reaches"
        assert game.world_map_runtime.current_node_id == "node_verdant_02"
    finally:
        game.shutdown()


def test_npcs_and_dialogue_read_the_whole_campaign(campaign, manager, isolated_settings_manager) -> None:
    game = _campaign_game(campaign, manager, isolated_settings_manager, new_game=True)
    try:
        game.load_level("verdant_01")
        assert game.dialogue.progress is game.campaign_progress
        assert game.npcs.progress is game.campaign_progress
    finally:
        game.shutdown()


def test_direct_launch_of_a_world_2_level_is_nonpersistent(campaign, game_factory) -> None:
    game = game_factory(level_id="glass_01", registry=campaign)
    assert game.registry.world_id == WORLD_2
    assert game.level.metadata.level_id == "glass_01"
    assert game.save_session is None


def test_shipped_game_loads_the_campaign_file(game_factory) -> None:
    game = game_factory(level_id="verdant_02")
    assert game.campaign.world_ids[0] == "verdant_reaches"
    assert game.registry.world_id == "verdant_reaches"


def test_world_gate_node_kind_exists() -> None:
    assert NodeType("world_gate") is NodeType.WORLD_GATE
