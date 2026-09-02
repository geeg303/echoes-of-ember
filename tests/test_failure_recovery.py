"""Persistence and configuration failure matrices using isolated paths."""
from __future__ import annotations

import json
import math

import pytest

from core.achievement_manager import AchievementManager, AchievementStore
from core.settings_manager import ApplicationSettings, SettingsManager
from settings import PROJECT_ROOT


@pytest.mark.parametrize(
    "mutate",
    [
        lambda data: data["audio"].update(master_volume=math.nan),
        lambda data: data["audio"].update(muted="yes"),
        lambda data: data["visual"].update(effects_quality="cinematic"),
        lambda data: data["display"].update(fullscreen=1),
        lambda data: data["input"].update(vibration_enabled=None),
        lambda data: data.update(schema_version=99),
    ],
)
def test_invalid_settings_fall_back_without_overwriting_source(tmp_path, mutate) -> None:
    path = tmp_path / "settings.json"
    data = ApplicationSettings().to_dict()
    mutate(data)
    path.write_text(json.dumps(data), encoding="utf-8")
    before = path.read_bytes()
    manager = SettingsManager(path)
    assert manager.load() == ApplicationSettings()
    assert manager.last_warning
    assert path.read_bytes() == before


def test_schema_one_settings_migrate_in_memory_with_safe_defaults(tmp_path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "audio": {"master_volume": 0.4},
        "visual": {"effects_quality": "reduced"},
        "display": {"fullscreen": True},
    }), encoding="utf-8")
    settings = SettingsManager(path).load()
    assert settings.audio.master_volume == 0.4
    assert settings.effects_quality == "reduced"
    assert settings.fullscreen
    assert settings.vibration_enabled


@pytest.mark.parametrize(
    "progress",
    [
        {"counters": {}, "sets": {}, "flags": ["bad flag"]},
        {"counters": {"ember_shards_collected": -1}, "sets": {}, "flags": []},
        {"counters": {}, "sets": {"npc_ids_met": ["mira", "mira"]}, "flags": []},
    ],
)
def test_invalid_achievement_progress_is_preserved_and_disabled(tmp_path, progress) -> None:
    path = tmp_path / "achievements.json"
    path.write_text(json.dumps({"schema_version": 1, "unlocked": {}, "progress": progress}), encoding="utf-8")
    before = path.read_bytes()
    manager = AchievementManager.create(PROJECT_ROOT / "data" / "achievements" / "achievements.json", path)
    assert manager.store.status == "corrupt"
    assert not manager.store.writable
    manager.emit("ember_shard_collected")
    assert path.read_bytes() == before


def test_invalid_achievement_timestamp_is_rejected(tmp_path) -> None:
    path = tmp_path / "achievements.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "unlocked": {"first_light": {"unlocked_at": "not-a-time"}},
        "progress": {"counters": {}, "sets": {}, "flags": []},
    }), encoding="utf-8")
    store = AchievementStore(path)
    manager = AchievementManager.create(PROJECT_ROOT / "data" / "achievements" / "achievements.json", path)
    assert manager.store.status == "corrupt" and not manager.profile.unlocked


def test_save_replace_failure_keeps_last_valid_primary(isolated_save_manager, monkeypatch) -> None:
    manager = isolated_save_manager
    session = manager.new_game(1)
    primary = manager.save_root / "slot_1.json"
    before = primary.read_bytes()
    session.play_time_seconds = 999
    session.dirty = True
    real_replace = __import__("core.save_manager", fromlist=["os"]).os.replace

    def fail_primary(source, destination):
        if destination == primary:
            raise OSError("simulated install failure")
        return real_replace(source, destination)

    monkeypatch.setattr("core.save_manager.os.replace", fail_primary)
    with pytest.raises(OSError, match="simulated"):
        manager.save(session)
    assert primary.read_bytes() == before
    assert session.dirty

