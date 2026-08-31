"""External level loading and validation checks."""

from __future__ import annotations

import json

import pytest

from settings import PROJECT_ROOT
from tools.validation import LevelValidationError, load_and_validate_level, validate_level_data
from world.level import Level
from world.tile import TileKind
from systems.progression import CollectibleType


def test_level_01_loads_from_json() -> None:
    level = Level.load(PROJECT_ROOT / "data" / "levels" / "level_01.json")
    assert level.tilemap.width == 108
    assert level.tilemap.pixel_width > 1280
    assert level.tilemap.pixel_height > 720
    assert level.tilemap.tile_at(12, 16).definition.kind is TileKind.HAZARD
    assert level.tilemap.tile_at(9, 11).definition.kind is TileKind.BREAKABLE
    assert len(level.collectible_spawns) == 58
    assert level.metadata.level_id == "verdant_01"
    assert level.goal.kind == "ember_gate"
    assert level.collectible_spawns[0].kind is CollectibleType.EMBER_SHARD


def test_validator_rejects_unknown_tile_and_out_of_bounds_region() -> None:
    data = {
        "name": "Broken",
        "width": 4,
        "height": 4,
        "tile_size": 64,
        "player_spawn": [0, 0],
        "tiles": [{"id": 999, "position": [3, 3], "size": [2, 1]}],
    }
    errors = validate_level_data(data)
    assert any("unknown tile id" in error for error in errors)
    assert any("outside level bounds" in error for error in errors)


def test_loader_reports_malformed_json(tmp_path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(LevelValidationError, match="could not read level"):
        load_and_validate_level(path)


def test_validator_rejects_malformed_collectibles() -> None:
    data = {
        "name": "Broken objects",
        "width": 4,
        "height": 4,
        "tile_size": 64,
        "player_spawn": [0, 0],
        "tiles": [],
        "objects": [
            {"id": "same", "type": "mystery", "x": 20, "y": 20},
            {"id": "same", "type": "ember_shard", "x": "far", "y": 999},
        ],
    }
    errors = validate_level_data(data)
    assert any("unknown collectible type" in error for error in errors)
    assert any("duplicate id" in error for error in errors)
    assert any("x must be a finite number" in error for error in errors)


def test_validator_rejects_non_list_object_section() -> None:
    data = {
        "name": "Broken objects",
        "width": 4,
        "height": 4,
        "tile_size": 64,
        "player_spawn": [0, 0],
        "tiles": [],
        "objects": "not-a-list",
    }
    assert "objects must be a list" in validate_level_data(data)


def test_enemy_validation_rejects_unknown_missing_and_malformed_data() -> None:
    data = {
        "name": "Enemy errors",
        "width": 10,
        "height": 8,
        "tile_size": 50,
        "player_spawn": [0, 0],
        "tiles": [],
        "objects": [
            {"id": "bad", "type": "enemy", "enemy_type": "dragon", "x": 20, "y": 20},
            {"id": "bad", "type": "enemy", "x": 30, "y": 20},
            {
                "id": "props",
                "type": "enemy",
                "enemy_type": "crawler",
                "x": 40,
                "y": 20,
                "properties": {"speed": "fast", "cliff_avoidance": 1},
            },
            {"type": "enemy", "enemy_type": "flyer", "x": 50, "y": 20, "properties": []},
        ],
    }
    errors = validate_level_data(data)
    assert any("unknown enemy type" in error for error in errors)
    assert any("missing enemy_type" in error for error in errors)
    assert any("duplicate id" in error for error in errors)
    assert sum("incorrect type or value" in error for error in errors) == 2
    assert any("id must be" in error for error in errors)
    assert any("properties must be an object" in error for error in errors)
