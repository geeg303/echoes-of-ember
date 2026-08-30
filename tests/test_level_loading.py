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
    assert level.tilemap.width == 72
    assert level.tilemap.pixel_width > 1280
    assert level.tilemap.pixel_height > 720
    assert level.tilemap.tile_at(12, 16).definition.kind is TileKind.HAZARD
    assert level.tilemap.tile_at(9, 11).definition.kind is TileKind.BREAKABLE
    assert len(level.collectible_spawns) == 42
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
