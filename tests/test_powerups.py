"""Power-up validation, lifecycle, movement, jumps, shield, and reset rules."""

from __future__ import annotations

import copy
import json

import pygame

from core.game import Game
from entities.player import Player, PlayerControls
from settings import POWERUP_DURATIONS
from systems.combat import DamageSource
from systems.player_combat import PlayerCombatController
from systems.powerup_system import PowerUpSystem, PowerUpType
from systems.projectile_system import ProjectileManager
from tools.validation import validate_level_data
from world.collision import CollisionEngine
from world.tilemap import TileMap


def level_data() -> dict[str, object]:
    with open("data/levels/verdant_01.json", encoding="utf-8") as handle:
        return json.load(handle)


def empty_collision() -> CollisionEngine:
    return CollisionEngine(TileMap.from_data({"width": 20, "height": 20, "tile_size": 64, "tiles": []}))


def test_powerup_validation_unknown_properties_and_duplicate_ids() -> None:
    data = level_data()
    invalid = copy.deepcopy(data)
    invalid["objects"].append({"id": "bad_power", "type": "powerup", "powerup_type": "mystery", "x": 100, "y": 100})
    invalid["objects"].append({"id": "shard_01", "type": "powerup", "powerup_type": "ember_pulse", "x": 120, "y": 100, "properties": {"duration": -2, "other": 1}})
    errors = validate_level_data(invalid)
    assert any("unknown power-up" in error for error in errors)
    assert any("duplicate id" in error for error in errors)
    assert any("duration" in error for error in errors)
    assert any("unknown property" in error for error in errors)


def test_activation_expiration_refresh_and_replacement() -> None:
    player = Player((0, 0))
    system = PowerUpSystem(player)
    system.activate(PowerUpType.EMBER_PULSE)
    system.update(3.0)
    assert system.active and system.active.remaining == POWERUP_DURATIONS["ember_pulse"] - 3
    system.activate(PowerUpType.EMBER_PULSE)
    assert system.active and system.active.remaining == POWERUP_DURATIONS["ember_pulse"]
    system.activate(PowerUpType.WIND_BOOTS)
    assert system.has(PowerUpType.WIND_BOOTS) and not system.grants_ranged_attack
    system.update(POWERUP_DURATIONS["wind_boots"] + 0.1)
    assert system.active is None


def test_ember_pulse_permission_and_inflight_projectile_survives_expiration() -> None:
    player = Player((100, 100))
    system = PowerUpSystem(player)
    combat = PlayerCombatController()
    projectiles = ProjectileManager()
    assert not combat.try_attack(player, projectiles)
    system.activate(PowerUpType.EMBER_PULSE, 0.01)
    combat.ember_pulse_enabled = system.grants_ranged_attack
    assert combat.try_attack(player, projectiles)
    system.update(0.02)
    combat.ember_pulse_enabled = system.grants_ranged_attack
    assert not combat.try_attack(player, projectiles)
    assert len(projectiles.projectiles) == 1


def test_wind_boots_modifiers_return_exactly_to_baseline() -> None:
    player = Player((0, 0))
    system = PowerUpSystem(player)
    baseline = system.movement_modifiers
    system.activate(PowerUpType.WIND_BOOTS)
    boosted = system.movement_modifiers
    assert boosted.speed == 1.2 and boosted.acceleration == 1.15 and boosted.jump == 1.05
    system.clear()
    assert system.movement_modifiers == baseline


def test_aether_wing_allows_only_one_extra_jump_and_ground_resets_it() -> None:
    player = Player((100, 100))
    system = PowerUpSystem(player)
    system.activate(PowerUpType.AETHER_WING)
    player.grounded = False
    player.coyote_timer = 0.0
    player.extra_jump_available = True
    collision = empty_collision()
    player.update(0.0, PlayerControls(jump_pressed=True), collision, system.movement_modifiers)
    assert player.velocity.y < 0 and not player.extra_jump_available
    velocity = player.velocity.y
    player.update(0.0, PlayerControls(jump_pressed=True), collision, system.movement_modifiers)
    assert player.velocity.y == velocity
    player.grounded = True
    player.update(0.0, PlayerControls(), collision, system.movement_modifiers)
    assert player.extra_jump_available


def test_stone_guard_absorbs_one_hit_without_health_loss() -> None:
    player = Player((0, 0))
    system = PowerUpSystem(player)
    system.activate(PowerUpType.STONE_GUARD)
    result = player.apply_damage(1, DamageSource.HAZARD)
    assert result.absorbed and not result.applied and player.health == player.max_health
    assert system.active is None and player.invulnerability_timer > 0
    second = player.apply_damage(1, DamageSource.HAZARD)
    assert second.applied and player.health == player.max_health - 1


def test_life_loss_and_f7_remove_active_powerup() -> None:
    game = Game()
    try:
        game.powerups.activate(PowerUpType.WIND_BOOTS)
        game.player.trigger_death()
        game.player.animation.play("death")
        game.player.animation.update(2.0)
        game.update(0.0)
        assert game.powerups.active is None
        game.powerups.activate(PowerUpType.EMBER_PULSE)
        game.reset_level()
        assert game.powerups.active is None
        assert len(game.powerup_pickups.pickups) == 4
    finally:
        game.shutdown()
