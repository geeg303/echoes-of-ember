"""Reusable Phase 14A boss framework tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pygame
import pytest

from bosses.boss_base import Boss, BossConfigError, BossState, load_boss_config, validate_boss_config
from entities.player import Player
from entities.projectile import Faction, Projectile
from systems.combat import DamageSource
from systems.powerup_system import PowerUpSystem, PowerUpType
from ui.boss_hud import BossHUDState
from world.boss_arena import BossArena, BossArenaDefinition
from world.trigger import Door

CONFIG_PATH = Path(__file__).parents[1] / "data" / "bosses" / "ashen_warden.json"


@pytest.fixture
def config():
    return load_boss_config(CONFIG_PATH)


def test_config_loads_typed_and_thresholds_are_correct(config) -> None:
    assert config.boss_id == "ashen_warden" and config.max_health == 18
    assert config.phase_for_health(18) == 1
    assert config.phase_for_health(12) == 2
    assert config.phase_for_health(6) == 3


def test_config_validation_rejects_bad_thresholds_and_empty_attacks() -> None:
    raw = json.loads(CONFIG_PATH.read_text())
    bad = copy.deepcopy(raw); bad["phases"][1]["minimum_health"] = 13
    assert any("thresholds" in item for item in validate_boss_config(bad))
    bad = copy.deepcopy(raw); bad["phases"][0]["attacks"] = []
    assert any("attacks" in item for item in validate_boss_config(bad))


def test_bad_config_file_raises_controlled_error(tmp_path: Path) -> None:
    path = tmp_path / "boss.json"; path.write_text('{"id": "bad"}')
    with pytest.raises(BossConfigError):
        load_boss_config(path)


def test_boss_initialization_intro_and_reset(config) -> None:
    boss = Boss(config, (100, 200))
    assert boss.health == boss.max_health == 18
    assert boss.phase == 1 and boss.state is BossState.INTRO and not boss.active
    boss.begin(); boss.update_lifecycle(config.intro_duration)
    boss.reset((50, 60))
    assert boss.rect.topleft == (50, 60) and boss.health == 18 and not boss.active


def test_damage_requires_vulnerability_and_respects_invulnerability(config) -> None:
    boss = Boss(config, (0, 0)); boss.begin()
    assert not boss.take_damage(1)
    boss.set_state(BossState.RECOVER, 1.0, vulnerable=True)
    assert boss.take_damage(1) and boss.health == 17
    assert not boss.take_damage(1)
    boss.update_lifecycle(config.hit_invulnerability)
    assert boss.take_damage(1) and boss.health == 16


def test_phase_transitions_and_defeat_are_one_time(config) -> None:
    boss = Boss(config, (0, 0)); boss.begin(); boss.set_state(BossState.RECOVER, 10, True)
    boss.health = 13; assert boss.take_damage(1); assert boss.phase == 2
    boss.update_lifecycle(config.hit_invulnerability); boss.set_state(BossState.RECOVER, 10, True)
    boss.health = 7; assert boss.take_damage(1); assert boss.phase == 3
    boss.update_lifecycle(config.hit_invulnerability); boss.set_state(BossState.RECOVER, 10, True)
    boss.health = 1; assert boss.take_damage(1)
    assert boss.state is BossState.DEFEATED and boss.claim_score() == 5000
    assert boss.claim_score() == 0 and not boss.take_damage(1)
    boss.update_lifecycle(config.defeat_duration)
    assert boss.defeated


def test_shared_projectile_faction_contract() -> None:
    projectile = Projectile("boss_bolt", (10, 10), pygame.Vector2(100, 0), 1, Faction.ENEMY, 2.0, owner_id="ashen_warden")
    assert projectile.faction is Faction.ENEMY and projectile.owner_id == "ashen_warden"


def test_player_damage_and_stone_guard_use_existing_contract() -> None:
    player = Player((0, 0)); powers = PowerUpSystem(player)
    powers.activate(PowerUpType.STONE_GUARD)
    result = player.apply_damage(1, DamageSource.ENEMY_PROJECTILE)
    assert result.absorbed and player.health == player.max_health and not powers.has(PowerUpType.STONE_GUARD)
    player.invulnerability_timer = 0
    result = player.apply_damage(1, DamageSource.ENEMY)
    assert result.applied and player.health == player.max_health - 1


def test_arena_trigger_lock_finish_reset_and_camera_bounds() -> None:
    left = Door("left", (100, 100), (32, 128), 0.5); right = Door("right", (700, 100), (32, 128), 0.5)
    left.open(); right.open(); left.update(1); right.update(1)
    definition = BossArenaDefinition("ashen_warden", (500, 200), pygame.Rect(100, 100, 632, 400), pygame.Rect(200, 100, 80, 300), ("left", "right"), (300, 300))
    arena = BossArena(definition, [left, right])
    assert arena.try_trigger(pygame.Rect(210, 150, 20, 20))
    assert left.solid and right.solid and arena.camera_bounds == definition.bounds
    assert not arena.try_trigger(pygame.Rect(210, 150, 20, 20))
    arena.finish(); left.update(1); right.update(1)
    assert arena.completed and not left.solid and arena.camera_bounds is None
    arena.reset(); assert not arena.active and not arena.completed


def test_boss_hud_state_is_screen_data_only(config) -> None:
    boss = Boss(config, (9000, 5000)); boss.begin()
    state = BossHUDState(True, boss.display_name, boss.health, boss.max_health, boss.phase)
    assert state.visible and state.health == 18 and not hasattr(state, "position")
    assert not state.vulnerable
