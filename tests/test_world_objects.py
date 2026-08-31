"""Interactive platform, breakable, switch, door, and checkpoint contracts."""

from __future__ import annotations

import copy
import json

import pygame

from core.game import Game
from entities.player import Player
from entities.projectile import Faction, Projectile
from systems.projectile_system import ProjectileManager
from systems.world_object_system import WorldObjectManager
from tools.validation import validate_level_data
from world.level import WorldObjectSpawn
from world.moving_platform import DisappearingPlatform, FallingPlatform, MovingPlatform, PlatformState
from world.tile import TileKind
from world.tilemap import TileMap


def empty_map() -> TileMap:
    return TileMap.from_data({"width": 20, "height": 20, "tile_size": 64, "tiles": []})


def spawn(object_id: str, kind: str, position: tuple[float, float], **properties: object) -> WorldObjectSpawn:
    return WorldObjectSpawn(object_id, kind, position, properties)


def test_moving_platform_interpolation_reversal_and_passenger_displacement() -> None:
    platform = MovingPlatform("m", (100, 200), "horizontal", 20, 100)
    platform.update(0.1)
    assert platform.position.x == 110 and platform.delta.x == 10
    platform.update(0.2)
    assert platform.position.x == 120 and platform.direction == -1

    manager = WorldObjectManager((spawn("ride", "moving_platform", (100, 200), movement="horizontal", distance=100, speed=100),), (0, 0))
    player = Player((120, 138))
    manager.riding_id = "ride"
    manager.update_before_player(0.1, player, empty_map())
    assert player.position.x == 130


def test_player_lands_on_dynamic_platform_and_detaches_when_jumping() -> None:
    manager = WorldObjectManager((spawn("ride", "moving_platform", (100, 200), movement="horizontal", distance=100, speed=50),), (0, 0))
    platform = manager.platforms[0]
    player = Player((125, 130))
    player.previous_rect = player.rect.copy()
    player.rect.bottom = platform.rect.top + 5
    player.position.y = player.rect.y
    player.velocity.y = 200
    manager.resolve_after_player(player, False, empty_map())
    assert manager.riding_id == "ride" and player.grounded and player.rect.bottom == platform.rect.top
    player.velocity.y = -500
    player.grounded = False
    player.previous_rect = player.rect.copy()
    player.rect.y -= 10
    manager.resolve_after_player(player, False, empty_map())
    assert manager.riding_id is None


def test_falling_platform_warns_falls_hides_and_resets() -> None:
    platform = FallingPlatform("fall", (100, 100), 0.2, 1000, 0.3)
    platform.trigger()
    platform.update(0.2)
    assert platform.state is PlatformState.FALLING
    for _ in range(20):
        platform.update(0.1)
        if platform.state is PlatformState.HIDDEN:
            break
    assert platform.state is PlatformState.HIDDEN and not platform.solid
    platform.update(0.31)
    assert platform.state is PlatformState.STABLE and platform.solid
    assert platform.position == platform.origin


def test_disappearing_platform_collision_matches_visual_cycle() -> None:
    platform = DisappearingPlatform("fade", (0, 0), 0.2, 0.1, 0.3)
    platform.update(0.2)
    assert platform.state is PlatformState.WARNING and platform.solid
    platform.update(0.1)
    assert platform.state is PlatformState.HIDDEN and not platform.solid
    platform.update(0.3)
    assert platform.state is PlatformState.STABLE and platform.solid


def test_only_player_projectile_destroys_breakable_tile() -> None:
    data = {"width": 8, "height": 8, "tile_size": 50, "tiles": [{"id": 5, "position": [3, 3]}]}
    tilemap = TileMap.from_data(data)
    enemy_bolt = Projectile("enemy", (130, 175), pygame.Vector2(300, 0), 1, Faction.ENEMY, 1)
    enemy_bolt.update(0.1, tilemap)
    assert tilemap.tile_at(3, 3).definition.kind is TileKind.BREAKABLE

    pulse = Projectile("player", (130, 175), pygame.Vector2(300, 0), 1, Faction.PLAYER, 1)
    pulse.update(0.1, tilemap)
    assert tilemap.tile_at(3, 3) is None and not pulse.active


def test_switch_opens_referenced_door_and_removes_collision() -> None:
    spawns = (
        spawn("switch", "switch", (100, 100), target_ids=["door"]),
        spawn("door", "door", (220, 60), width=48, height=128, opening_duration=0.5),
    )
    manager = WorldObjectManager(spawns, (0, 0))
    player = Player((100, 100))
    assert manager.resolve_after_player(player, True, empty_map())
    assert manager.switches[0].active and manager.doors[0].opening
    manager.update_before_player(0.5, player, empty_map())
    assert not manager.doors[0].solid


def test_checkpoint_updates_respawn_and_f7_restores_initial_spawn() -> None:
    manager = WorldObjectManager((spawn("cp", "checkpoint", (100, 100)),), (10, 20))
    player = Player((100, 100))
    assert manager.resolve_after_player(player, False, empty_map())
    assert manager.respawn_position == pygame.Vector2(100, 100)

    game = Game()
    try:
        initial = pygame.Vector2(game.level.player_spawn)
        game.world_objects.respawn_position.update(500, 500)
        game.reset_level()
        assert game.world_objects.respawn_position == initial
    finally:
        game.shutdown()


def test_hazard_respawn_uses_active_checkpoint_and_keeps_world_state() -> None:
    game = Game()
    try:
        checkpoint = game.world_objects.checkpoints[0]
        game.player.reposition(checkpoint.respawn_position)
        game.update(0.0)
        assert checkpoint.active
        expected = checkpoint.respawn_position.copy()
        game.player.reposition((12 * 64 + 10, 16 * 64 + 8))
        game.update(1 / 60)
        assert game.player.position == expected and game.player.health == 2
        game.player.trigger_death()
        game.player.animation.update(2.0)
        game.update(0.0)
        assert game.player.position == expected and game.player.lives == 2
    finally:
        game.shutdown()


def test_f7_restores_destroyed_breakable_tile() -> None:
    game = Game()
    try:
        tile = game.level.tilemap.tile_at(62, 15)
        assert tile and tile.definition.kind is TileKind.BREAKABLE
        assert game.level.tilemap.destroy_breakables(tile.rect)
        assert game.level.tilemap.tile_at(62, 15) is None
        game.reset_level()
        assert game.level.tilemap.tile_at(62, 15).definition.kind is TileKind.BREAKABLE
    finally:
        game.shutdown()


def test_world_object_validation_rejects_malformed_values_and_references() -> None:
    with open("data/levels/verdant_01.json", encoding="utf-8") as handle:
        data = json.load(handle)
    invalid = copy.deepcopy(data)
    invalid["objects"].append({"id": "bad_platform", "type": "moving_platform", "x": 10, "y": 10, "properties": {"movement": "diagonal", "distance": -1}})
    invalid["objects"].append({"id": "bad_switch", "type": "switch", "x": 20, "y": 20, "properties": {"target_id": "missing_door"}})
    invalid["objects"].append({"type": "checkpoint", "x": 30, "y": 30})
    errors = validate_level_data(invalid)
    assert any("movement" in error for error in errors)
    assert any("speed" in error for error in errors)
    assert any("distance" in error for error in errors)
    assert any("missing or incompatible door" in error for error in errors)
    assert any("id must be a non-empty string" in error for error in errors)
