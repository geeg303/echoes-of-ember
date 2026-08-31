"""Ashen Warden encounter, reset, progression, and softlock-safety tests."""

from __future__ import annotations

import copy
import pygame

from bosses.boss_base import BossState
from core.game import Game
from core.save_manager import SaveManager
from entities.projectile import Faction, Projectile
from systems.level_completion import CompletionRating, GameplayPhase, LevelResult
from systems.powerup_system import PowerUpType
from tools.validation import load_and_validate_level, validate_level_data
from world.campaign import DEFAULT_WORLD_REGISTRY, WorldProgress, WorldRegistry
from world.world_map import NodeState, WorldMapRuntime


def result(level_id: str, exit_id: str = "ember_gate") -> LevelResult:
    return LevelResult(level_id, True, 90, 5000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 3, 1, CompletionRating.SILVER, 0, 0, 0, exit_id=exit_id)


def trigger(game: Game) -> None:
    bounds = game.level.boss_encounter.trigger
    game.player.reposition((bounds.centerx - game.player.rect.width / 2, bounds.bottom - game.player.rect.height))
    game.update(0)


def player_shot(game: Game) -> Projectile:
    shot = Projectile("test_pulse", game.boss_system.boss.rect.center, pygame.Vector2(), 1, Faction.PLAYER, 2, owner_id="player", terrain_collision=False)
    game.projectiles.spawn(shot)
    return shot


def test_boss_level_loads_with_valid_arena_and_required_safety_objects() -> None:
    registry = WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
    data = load_and_validate_level(registry.level_paths["verdant_boss"])
    assert data["boss_encounter"]["boss_id"] == "ashen_warden"
    assert any(item["type"] == "checkpoint" for item in data["objects"])
    assert any(item.get("powerup_type") == "ember_pulse" for item in data["objects"])


def test_boss_level_validation_rejects_missing_door_bad_spawn_and_missing_pulse() -> None:
    registry = WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
    data = load_and_validate_level(registry.level_paths["verdant_boss"])
    bad = copy.deepcopy(data); bad["boss_encounter"]["door_ids"] = ["missing"]
    assert any("missing door" in item for item in validate_level_data(bad))
    bad = copy.deepcopy(data); bad["boss_encounter"]["boss_spawn"] = [10, 10]
    assert any("inside arena" in item for item in validate_level_data(bad))
    bad = copy.deepcopy(data); bad["objects"] = [item for item in bad["objects"] if item.get("powerup_type") != "ember_pulse"]
    assert any("Ember Pulse" in item for item in validate_level_data(bad))


def test_zero_powerup_entry_grants_encounter_pulse_and_locks_arena() -> None:
    game = Game(level_id="verdant_boss")
    try:
        assert game.powerups.active is None and not game.powerups.grants_ranged_attack
        trigger(game)
        assert game.boss_system.active and game.powerups.grants_ranged_attack
        assert all(door.solid for door in game.boss_system.arena.doors)
        assert game.camera.bounds == game.level.boss_encounter.bounds
    finally: game.shutdown()


def test_normal_pulse_expiration_does_not_remove_encounter_attack_permission() -> None:
    game = Game(level_id="verdant_boss")
    try:
        game.powerups.activate(PowerUpType.EMBER_PULSE, 0.01)
        trigger(game); game.powerups.update(1.0)
        assert game.powerups.active is None
        assert game.powerups.grants_ranged_attack
    finally: game.shutdown()


def test_intro_precedes_telegraph_and_attack_spawns_shared_enemy_projectiles() -> None:
    game = Game(level_id="verdant_boss")
    try:
        trigger(game); boss = game.boss_system.boss
        assert boss.state is BossState.INTRO and not game.projectiles.projectiles
        boss.update(boss.config.intro_duration, game.player.rect, game.level.boss_encounter.bounds, game.projectiles.spawn, game.projectiles.new_id)
        boss.update(0.5, game.player.rect, game.level.boss_encounter.bounds, game.projectiles.spawn, game.projectiles.new_id)
        assert boss.state is BossState.TELEGRAPH and not game.projectiles.projectiles
        boss.update(1.0, game.player.rect, game.level.boss_encounter.bounds, game.projectiles.spawn, game.projectiles.new_id)
        assert game.projectiles.projectiles
        assert all(item.faction is Faction.ENEMY and item.owner_id == "ashen_warden" for item in game.projectiles.projectiles)
    finally: game.shutdown()


def test_controlled_attack_selector_never_immediately_repeats() -> None:
    game = Game(level_id="verdant_boss")
    try:
        trigger(game); boss = game.boss_system.boss; boss.skip_intro()
        chosen = []
        for _ in range(6):
            boss.set_state(BossState.IDLE, 0)
            boss.update(0, game.player.rect, game.level.boss_encounter.bounds, game.projectiles.spawn, game.projectiles.new_id)
            chosen.append(boss.current_attack)
        assert all(left != right for left, right in zip(chosen, chosen[1:]))
    finally: game.shutdown()


def test_damage_windows_drive_three_phases() -> None:
    game = Game(level_id="verdant_boss")
    try:
        trigger(game); boss = game.boss_system.boss
        boss.health = 13; boss.set_state(BossState.RECOVER, 1, True); assert boss.take_damage(1); assert boss.phase == 2
        boss.update_lifecycle(boss.config.hit_invulnerability); boss.health = 7; boss.set_state(BossState.RECOVER, 1, True); assert boss.take_damage(1); assert boss.phase == 3
    finally: game.shutdown()


def test_boss_defeat_sequence_awards_once_clears_danger_and_completes_world() -> None:
    game = Game(level_id="verdant_boss")
    try:
        trigger(game); boss = game.boss_system.boss
        boss.health = 1; boss.set_state(BossState.RECOVER, 2, True); player_shot(game)
        game.update(0)
        assert boss.defeat_claimed and game.progress.score == 5000
        assert not any(item.faction is Faction.ENEMY for item in game.projectiles.projectiles)
        game.update(boss.config.defeat_duration + 0.1)
        assert game.gameplay_phase is GameplayPhase.COMPLETION_SEQUENCE
        assert "ashen_warden" in game.world_progress.defeated_bosses
        assert game.world_progress.world_completed_once
        game.update(2)
        assert game.gameplay_phase is GameplayPhase.LEVEL_COMPLETE
    finally: game.shutdown()


def test_simultaneous_committed_boss_death_stabilizes_player() -> None:
    game = Game(level_id="verdant_boss")
    try:
        trigger(game); boss = game.boss_system.boss
        game.player.health = 0; game.player.trigger_death()
        boss.health = 1; boss.set_state(BossState.RECOVER, 2, True); player_shot(game)
        outcome = game.boss_system.update(0, game.player, game.powerups, game.progress)
        assert outcome.boss_defeated and not game.player.is_dead and game.player.health == 1
    finally: game.shutdown()


def test_life_loss_and_f7_reconstruct_clean_phase_one_encounter() -> None:
    game = Game(level_id="verdant_boss")
    try:
        trigger(game); boss = game.boss_system.boss; boss.health = 8; boss.phase = 2
        game.boss_system.reset_encounter(game.powerups)
        assert boss.health == 18 and boss.phase == 1 and not game.boss_system.active and not game.projectiles.projectiles
        trigger(game); old = game.boss_system
        game.reset_level()
        assert game.boss_system is not old and game.boss_system.boss.health == 18 and game.boss_system.boss.phase == 1
    finally: game.shutdown()


def test_ruins_unlocks_boss_but_only_boss_defeat_completes_world() -> None:
    registry = WorldRegistry.load(DEFAULT_WORLD_REGISTRY); progress = WorldProgress(registry); runtime = WorldMapRuntime(registry.map_definition, progress)
    progress.record(result("verdant_04"))
    assert runtime.node_state("first_flame_sanctum") is NodeState.AVAILABLE
    assert not progress.world_completed_once
    progress.record_boss_defeat("ashen_warden", result("verdant_boss", "ashen_warden"))
    assert runtime.node_state("first_flame_sanctum") is NodeState.COMPLETED
    assert progress.world_completed_once


def test_secret_branch_and_boss_progression_coexist_and_replay_is_monotonic() -> None:
    from systems.level_completion import ExitType
    registry = WorldRegistry.load(DEFAULT_WORLD_REGISTRY); progress = WorldProgress(registry); runtime = WorldMapRuntime(registry.map_definition, progress)
    secret = LevelResult("verdant_04", True, 90, 5000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 3, 1, CompletionRating.SILVER, 0, 0, 0, ExitType.SECRET, "v04_secret_exit")
    progress.record(secret)
    progress.record_boss_defeat("ashen_warden", result("verdant_boss", "ashen_warden"))
    progress.record(result("verdant_boss", "ashen_warden"))
    assert runtime.node_state("ember_veil") is NodeState.AVAILABLE
    assert "ashen_warden" in progress.defeated_bosses and progress.world_completed_once

def test_game_boss_defeat_autosaves_and_restores_completed_sanctum(tmp_path) -> None:
    registry = WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
    manager = SaveManager(registry, tmp_path)
    session = manager.new_game(1)
    for level_id in registry.level_ids[:4]:
        session.progress.record(result(level_id))
    manager.save(session)
    game = Game(start_on_map=True, registry=registry, save_manager=manager, persistence=True, slot_id=1)
    try:
        game.world_map_runtime.return_to_level_node("verdant_boss")
        game.load_level("verdant_boss")
        trigger(game)
        boss = game.boss_system.boss
        boss.health = 1; boss.set_state(BossState.RECOVER, 2, True); player_shot(game)
        game.update(0); game.update(boss.config.defeat_duration + 0.1)
        assert game.world_progress.world_completed_once
    finally:
        game.shutdown()
    restored = Game(start_on_map=True, registry=registry, save_manager=manager, persistence=True, slot_id=1)
    try:
        assert "ashen_warden" in restored.world_progress.defeated_bosses
        assert restored.world_progress.world_completed_once
        assert restored.world_map_runtime.node_state("first_flame_sanctum") is NodeState.COMPLETED
        assert restored.world_progress.results["verdant_boss"].exit_id == "ashen_warden"
    finally:
        restored.shutdown()


def test_stone_guard_absorbs_boss_contact_exactly_once() -> None:
    game = Game(level_id="verdant_boss")
    try:
        game.powerups.activate(PowerUpType.STONE_GUARD)
        trigger(game)
        game.boss_system.boss.skip_intro()
        game.player.reposition(game.boss_system.boss.rect.topleft)
        health = game.player.health
        first = game.boss_system.update(0, game.player, game.powerups, game.progress)
        assert first.player_damaged and game.player.health == health
        assert not game.powerups.has(PowerUpType.STONE_GUARD)
        game.player.invulnerability_timer = 0
        second = game.boss_system.update(0, game.player, game.powerups, game.progress)
        assert second.player_damaged and game.player.health == health - 1
    finally:
        game.shutdown()

def test_available_sanctum_map_node_launches_registered_boss_level() -> None:
    game = Game(start_on_map=True)
    try:
        game.world_progress.record(result("verdant_04"))
        game.world_map_runtime.current_node_id = "first_flame_sanctum"
        action, level_id = game.world_map_screen.activate_current()
        assert action == "level" and level_id == "verdant_boss"
        game.load_level(level_id)
        assert game.level.metadata.level_id == "verdant_boss" and game.boss_system is not None
    finally:
        game.shutdown()


def test_f7_reconstruction_is_safe_during_transition_and_defeat() -> None:
    for state in (BossState.PHASE_TRANSITION, BossState.DEFEATED):
        game = Game(level_id="verdant_boss")
        try:
            trigger(game)
            old = game.boss_system
            old.boss.state = state
            old.boss.health = 6 if state is BossState.PHASE_TRANSITION else 0
            game.reset_level()
            assert game.boss_system is not old
            assert game.boss_system.boss.state is BossState.INTRO
            assert game.boss_system.boss.health == 18
            assert not game.projectiles.projectiles and not game.boss_system.active
        finally:
            game.shutdown()

