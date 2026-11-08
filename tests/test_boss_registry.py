"""Boss runtime registry: bosses are looked up by ID instead of hardcoded checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from bosses.ashen_warden import AshenWarden
from settings import PROJECT_ROOT
from systems.boss_system import BOSS_RUNTIMES, BossRuntime, BossSystem, register_boss_runtime
from systems.projectile_system import ProjectileManager
from world.boss_arena import BossArenaDefinition
from world.campaign import DEFAULT_WORLD_REGISTRY, WorldRegistry


def _arena(boss_id: str) -> tuple[BossArenaDefinition, list[object]]:
    from dataclasses import replace

    from systems.world_object_system import WorldObjectManager
    from world.level import Level

    level = Level.load(PROJECT_ROOT / "data" / "levels" / "verdant_boss.json")
    doors = WorldObjectManager(level.world_object_spawns, level.player_spawn).doors
    return replace(level.boss_encounter, boss_id=boss_id), doors


def test_ashen_warden_is_registered_with_its_audio_map() -> None:
    runtime = BOSS_RUNTIMES["ashen_warden"]
    assert runtime.boss_class is AshenWarden
    assert runtime.audio_events["ground_slam"] == "warden_ground_slam"
    assert runtime.audio_events["defeat"] == "warden_defeat"


def test_unregistered_boss_is_rejected(tmp_path: Path) -> None:
    config = (PROJECT_ROOT / "data" / "bosses" / "ashen_warden.json").read_text(encoding="utf-8")
    (tmp_path / "mystery_boss.json").write_text(config.replace('"ashen_warden"', '"mystery_boss"'), encoding="utf-8")
    with pytest.raises(ValueError, match="no runtime implementation"):
        BossSystem(*_arena("mystery_boss"), ProjectileManager(), config_root=tmp_path)


def test_registered_boss_runtime_is_constructed_from_its_own_config(tmp_path: Path) -> None:
    class PracticeWarden(AshenWarden):
        pass

    config = (PROJECT_ROOT / "data" / "bosses" / "ashen_warden.json").read_text(encoding="utf-8")
    (tmp_path / "practice_warden.json").write_text(
        config.replace('"ashen_warden"', '"practice_warden"'), encoding="utf-8"
    )
    register_boss_runtime("practice_warden", BossRuntime(PracticeWarden, {}))
    try:
        system = BossSystem(*_arena("practice_warden"), ProjectileManager(), config_root=tmp_path)
        assert isinstance(system.boss, PracticeWarden)
        assert system.boss.boss_id == "practice_warden"
    finally:
        BOSS_RUNTIMES.pop("practice_warden")


def test_registering_a_duplicate_boss_id_fails() -> None:
    with pytest.raises(ValueError, match="already registered"):
        register_boss_runtime("ashen_warden", BossRuntime(AshenWarden, {}))


def test_world_registry_exposes_boss_display_names() -> None:
    registry = WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
    assert registry.boss_display_names == {"ashen_warden": "The Ashen Warden"}


def test_world_complete_rows_name_the_world_and_its_boss(pygame_headless) -> None:
    import pygame

    from states.world_complete import WorldCompleteScreen
    from world.campaign import WorldProgress

    registry = WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
    progress = WorldProgress(registry)
    progress.defeated_bosses.add("ashen_warden")
    font = pygame.font.Font(None, 20)
    screen = WorldCompleteScreen(font, font, font)
    assert screen.heading(progress) == "VERDANT REACHES COMPLETE"
    assert screen.rows(progress)[0] == ("BOSS", "THE ASHEN WARDEN — DEFEATED")


def test_runtime_code_has_no_hardcoded_boss_ids() -> None:
    """Only the boss registry may name a specific boss; everything else looks bosses up by ID."""
    offenders = []
    for folder in ("core", "states", "ui", "world", "systems"):
        for path in (PROJECT_ROOT / folder).rglob("*.py"):
            if path.name == "boss_system.py":
                continue
            if "ashen_warden" in path.read_text(encoding="utf-8").lower().replace(" ", "_"):
                offenders.append(path.relative_to(PROJECT_ROOT).as_posix())
    assert offenders == []
