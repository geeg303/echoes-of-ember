"""Campaign registry, cross-world progress, and save schema 4 (multi-world) with lossless v3 migration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.save_manager import SaveManager, SlotState
from systems.dialogue_system import condition_matches
from systems.level_completion import CompletionRating, ExitType, LevelResult
from systems.save_data import CURRENT_SAVE_VERSION, SaveSession, SaveValidationError, migrate_save
from tests.multiworld import WORLD_2, build_two_world_campaign
from world.campaign import (
    DEFAULT_CAMPAIGN,
    CampaignProgress,
    CampaignRegistry,
    WorldRegistry,
    WorldRegistryError,
)


def result(level_id: str, exit_type: ExitType = ExitType.NORMAL, exit_id: str = "ember_gate", score=100):
    return LevelResult(
        level_id, True, 12.5, score, 3, 10, 1, 3, 1, 1, 2, 4, 1, 2, 3, 1,
        CompletionRating.SILVER, 2, 3, 1, exit_type, exit_id,
    )  # fmt: skip


def finish_world_1(progress) -> None:
    for level_id in ("verdant_01", "verdant_02", "verdant_03", "verdant_04"):
        progress.record(result(level_id))
    progress.record_boss_defeat("ashen_warden", result("verdant_boss", exit_id="ashen_warden"))


@pytest.fixture
def campaign(tmp_path: Path) -> CampaignRegistry:
    return CampaignRegistry.load(build_two_world_campaign(tmp_path))


# --- registry ---------------------------------------------------------------------------------


def test_shipped_campaign_lists_verdant_reaches_first() -> None:
    shipped = CampaignRegistry.load(DEFAULT_CAMPAIGN)
    assert shipped.world_ids[0] == "verdant_reaches"
    assert "verdant_01" in shipped.level_paths


def test_two_world_campaign_finds_each_levels_world(campaign: CampaignRegistry) -> None:
    assert campaign.world_ids == ("verdant_reaches", WORLD_2)
    assert campaign.world_for_level("verdant_03").world_id == "verdant_reaches"
    assert campaign.world_for_level("glass_boss").world_id == WORLD_2
    assert campaign.world(WORLD_2).boss_display_names == {"glass_sentinel": "The Glass Sentinel"}
    assert campaign.world(WORLD_2).map_theme == "glassreach"


def test_unknown_level_lookup_is_a_registry_error(campaign: CampaignRegistry) -> None:
    with pytest.raises(WorldRegistryError, match="unknown level"):
        campaign.world_for_level("nope")


def test_duplicate_world_in_campaign_is_rejected(tmp_path: Path) -> None:
    path = build_two_world_campaign(tmp_path, world_order=("verdant_reaches", "verdant_reaches"))
    with pytest.raises(WorldRegistryError, match="duplicate world"):
        CampaignRegistry.load(path)


def test_missing_world_file_is_rejected(tmp_path: Path) -> None:
    path = build_two_world_campaign(tmp_path, world_order=("verdant_reaches", "no_such_world"))
    with pytest.raises(WorldRegistryError, match="no_such_world"):
        CampaignRegistry.load(path)


def test_level_ids_must_be_unique_across_worlds(tmp_path: Path) -> None:
    path = build_two_world_campaign(tmp_path)
    world_2 = path.parent / "worlds" / f"{WORLD_2}.json"
    data = json.loads(world_2.read_text(encoding="utf-8"))
    level = json.loads((path.parent / "levels" / "verdant_01.json").read_text(encoding="utf-8"))
    level["world_id"] = WORLD_2
    (path.parent / "levels" / "verdant_01.json").write_text(json.dumps(level), encoding="utf-8")
    data["levels"][0] = "verdant_01"
    data["map"]["nodes"][1]["level_id"] = "verdant_01"
    data["map"]["connections"][1]["unlock"]["level_id"] = "verdant_01"
    world_2.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(WorldRegistryError):
        CampaignRegistry.load(path)


def test_single_registry_wraps_into_a_one_world_campaign() -> None:
    registry = WorldRegistry.load(Path(DEFAULT_CAMPAIGN).parent / "worlds" / "verdant_reaches.json")
    single = CampaignRegistry.single(registry)
    assert single.world_ids == ("verdant_reaches",)
    assert CampaignRegistry.coerce(registry).world_ids == ("verdant_reaches",)
    assert CampaignRegistry.coerce(single) is single


# --- cross-world progress ---------------------------------------------------------------------


def test_world_2_unlocks_only_after_world_1_is_truly_complete(campaign: CampaignRegistry) -> None:
    progress = CampaignProgress.fresh(campaign)
    assert progress.world_unlocked("verdant_reaches")
    assert not progress.world_unlocked(WORLD_2)
    for level_id in ("verdant_01", "verdant_02", "verdant_03", "verdant_04"):
        progress.world("verdant_reaches").record(result(level_id))
    assert not progress.world_unlocked(WORLD_2)
    finish_world_1(progress.world("verdant_reaches"))
    assert progress.world_unlocked(WORLD_2)


def test_cannot_activate_a_locked_world(campaign: CampaignRegistry) -> None:
    progress = CampaignProgress.fresh(campaign)
    with pytest.raises(WorldRegistryError, match="locked"):
        progress.set_active_world(WORLD_2)


def test_dialogue_flags_are_shared_by_every_world(campaign: CampaignRegistry) -> None:
    progress = CampaignProgress.fresh(campaign)
    progress.world("verdant_reaches").dialogue_flags.add("met_mira")
    assert "met_mira" in progress.world(WORLD_2).dialogue_flags
    assert progress.dialogue_flags == {"met_mira"}


def test_dialogue_conditions_see_earlier_worlds(campaign: CampaignRegistry) -> None:
    progress = CampaignProgress.fresh(campaign)
    finish_world_1(progress.world("verdant_reaches"))
    progress.set_active_world(WORLD_2)
    assert condition_matches({"type": "boss_defeated", "value": "ashen_warden"}, progress)
    assert condition_matches({"type": "level_completed", "value": "verdant_02"}, progress)
    assert condition_matches({"type": "world_completed", "value": "verdant_reaches"}, progress)
    # A boolean world_completed still means "the world Nova is currently in".
    assert condition_matches({"type": "world_completed", "value": False}, progress)
    assert not condition_matches({"type": "world_completed", "value": WORLD_2}, progress)


# --- save schema 4 ----------------------------------------------------------------------------


def test_current_save_version_is_4() -> None:
    assert CURRENT_SAVE_VERSION == 4


def test_fresh_v4_save_lists_every_world_with_its_own_map_node(campaign: CampaignRegistry) -> None:
    data = SaveSession.fresh(1, campaign).to_dict()
    assert data["schema_version"] == 4
    assert data["campaign"]["active_world_id"] == "verdant_reaches"
    assert data["campaign"]["dialogue_flags"] == []
    worlds = data["campaign"]["worlds"]
    assert set(worlds) == {"verdant_reaches", WORLD_2}
    assert worlds["verdant_reaches"]["current_map_node"] == "starting_grove"
    assert worlds[WORLD_2]["current_map_node"] == "glass_landing"


def test_two_world_progress_round_trips(campaign: CampaignRegistry, tmp_path: Path) -> None:
    manager = SaveManager(campaign, tmp_path / "saves")
    session = manager.new_game(2)
    world_1 = session.campaign_progress.world("verdant_reaches")
    finish_world_1(world_1)
    world_1.record(result("verdant_04", ExitType.SECRET, "v04_secret_exit"))
    world_1.dialogue_flags.add("met_vesper")
    session.current_map_node = "verdant_beacon"
    session.campaign_progress.set_active_world(WORLD_2)
    session.progress.record(result("glass_01", score=777))
    session.current_map_node = "node_glass_01"
    manager.save(session)
    loaded = manager.load(2).session
    assert loaded is not None
    assert loaded.campaign_progress.active_world_id == WORLD_2
    assert loaded.current_map_node == "node_glass_01"
    assert loaded.progress.results["glass_01"].score == 777
    restored_1 = loaded.campaign_progress.world("verdant_reaches")
    assert restored_1.world_completed_once and restored_1.defeated_bosses == {"ashen_warden"}
    assert "ember_veil" in restored_1.revealed_map_nodes
    assert loaded.map_nodes["verdant_reaches"] == "verdant_beacon"
    assert loaded.campaign_progress.dialogue_flags == {"met_vesper"}


def test_slot_summary_aggregates_all_worlds(campaign: CampaignRegistry, tmp_path: Path) -> None:
    manager = SaveManager(campaign, tmp_path / "saves")
    session = manager.new_game(1)
    finish_world_1(session.progress)
    session.campaign_progress.set_active_world(WORLD_2)
    session.progress.record(result("glass_01", score=50))
    manager.save(session)
    summary = manager.inspect_slot(1)
    assert summary.levels_completed == 6
    assert summary.score == 5 * 100 + 50


def _v3_save(registry: WorldRegistry) -> dict:
    """A v3 save exactly as the 0.1.0-alpha game wrote it."""
    return {
        "schema_version": 3,
        "metadata": {
            "slot_id": 1,
            "created_at": "2026-09-01T10:00:00Z",
            "updated_at": "2026-09-02T11:30:00Z",
            "play_time_seconds": 5432.25,
        },
        "campaign": {
            "active_world_id": "verdant_reaches",
            "current_map_node": "verdant_beacon",
            "level_results": {
                "verdant_01": {**_result_dict(result("verdant_01", score=1200))},
                "verdant_04": {**_result_dict(result("verdant_04", ExitType.SECRET, "v04_secret_exit"))},
                "verdant_boss": {**_result_dict(result("verdant_boss", exit_id="ashen_warden"))},
            },
            "progression": {
                "completed_levels_once": ["verdant_01", "verdant_02", "verdant_03", "verdant_04", "verdant_boss"],
                "discovered_secret_exits": [{"level_id": "verdant_04", "exit_id": "v04_secret_exit"}],
                "revealed_map_nodes": ["ember_veil"],
                "defeated_bosses": ["ashen_warden"],
                "dialogue_flags": ["met_mira", "orin_warned"],
                "completed_worlds_once": ["verdant_reaches"],
            },
        },
    }


def _result_dict(item: LevelResult) -> dict:
    from systems.save_data import _result_to_dict

    return _result_to_dict(item)


def test_v3_save_migrates_losslessly_into_v4(campaign: CampaignRegistry, tmp_path: Path) -> None:
    manager = SaveManager(campaign, tmp_path / "saves")
    path = manager.save_root / "slot_1.json"
    path.write_text(json.dumps(_v3_save(campaign.world("verdant_reaches"))), encoding="utf-8")
    outcome = manager.load(1)
    assert outcome.state is SlotState.VALID and outcome.session is not None
    session = outcome.session
    world_1 = session.campaign_progress.world("verdant_reaches")
    assert session.created_at == "2026-09-01T10:00:00Z"
    assert session.updated_at == "2026-09-02T11:30:00Z"
    assert session.play_time_seconds == pytest.approx(5432.25)
    assert session.campaign_progress.active_world_id == "verdant_reaches"
    assert session.current_map_node == "verdant_beacon"
    assert world_1.results["verdant_01"].score == 1200
    assert world_1.results["verdant_04"].exit_type is ExitType.SECRET
    assert world_1.completed_levels_once == {"verdant_01", "verdant_02", "verdant_03", "verdant_04", "verdant_boss"}
    assert world_1.discovered_secret_exits == {("verdant_04", "v04_secret_exit")}
    assert world_1.revealed_map_nodes == {"ember_veil"}
    assert world_1.defeated_bosses == {"ashen_warden"}
    assert world_1.world_completed_once
    assert session.campaign_progress.dialogue_flags == {"met_mira", "orin_warned"}
    # The newly added world starts fresh and is unlocked because World 1 was finished.
    assert session.campaign_progress.world(WORLD_2).results == {}
    assert session.campaign_progress.world_unlocked(WORLD_2)
    manager.save(session)
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 4


def test_v3_migration_works_against_the_shipped_single_world_campaign(tmp_path: Path) -> None:
    shipped = CampaignRegistry.load(DEFAULT_CAMPAIGN)
    manager = SaveManager(shipped, tmp_path / "saves")
    (manager.save_root / "slot_1.json").write_text(
        json.dumps(_v3_save(shipped.world("verdant_reaches"))), encoding="utf-8"
    )
    session = manager.load(1).session
    assert session is not None and session.progress.world_completed_once


def test_v3_migration_rejects_an_unknown_completed_world() -> None:
    data = _v3_save(None)
    data["campaign"]["progression"]["completed_worlds_once"] = ["verdant_reaches", "mystery"]
    with pytest.raises(SaveValidationError):
        migrate_save(data)


def test_older_save_written_before_a_world_existed_still_loads(campaign: CampaignRegistry) -> None:
    """Adding World 2 in a game update must not invalidate v4 saves made with only World 1."""
    shipped = CampaignRegistry.load(DEFAULT_CAMPAIGN)
    one_world = SaveSession.fresh(1, shipped)
    finish_world_1(one_world.progress)
    restored = SaveSession.from_dict(one_world.to_dict(), campaign, 1)
    assert restored.campaign_progress.world("verdant_reaches").world_completed_once
    assert restored.map_nodes[WORLD_2] == "glass_landing"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda data: data["campaign"].update(active_world_id="mystery"),
        lambda data: data["campaign"]["worlds"].update(mystery={}),
        lambda data: data["campaign"]["worlds"]["verdant_reaches"].update(current_map_node="glass_landing"),
        lambda data: data["campaign"]["worlds"][WORLD_2]["progression"].update(completed_levels_once=["verdant_01"]),
        lambda data: data["campaign"].update(dialogue_flags=["Not A Flag"]),
        lambda data: data["campaign"].update(dialogue_flags="met_mira"),
    ],
)
def test_invalid_v4_data_is_rejected(campaign: CampaignRegistry, mutation) -> None:
    data = SaveSession.fresh(1, campaign).to_dict()
    mutation(data)
    with pytest.raises(SaveValidationError):
        SaveSession.from_dict(data, campaign, 1)


def test_active_world_must_be_unlocked(campaign: CampaignRegistry) -> None:
    data = SaveSession.fresh(1, campaign).to_dict()
    data["campaign"]["active_world_id"] = WORLD_2
    with pytest.raises(SaveValidationError, match="locked"):
        SaveSession.from_dict(data, campaign, 1)


@pytest.mark.parametrize(("value", "ok"), [(True, True), ("verdant_reaches", True), ("", False), (3, False)])
def test_dialogue_world_completed_accepts_bool_or_world_id(tmp_path: Path, value, ok: bool) -> None:
    from systems.dialogue_system import DialogueDataError, load_dialogue

    data = {
        "id": "test_talk",
        "start": "start",
        "nodes": [
            {
                "id": "start",
                "type": "choice",
                "speaker": "Nova",
                "text": "Which way?",
                "responses": [
                    {"label": "Onward", "target": "end", "conditions": [{"type": "world_completed", "value": value}]}
                ],
            },
            {"id": "end", "type": "end", "speaker": "Nova", "text": "Then onward."},
        ],
    }
    path = tmp_path / "test_talk.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    if ok:
        load_dialogue(path)
    else:
        with pytest.raises(DialogueDataError):
            load_dialogue(path)
