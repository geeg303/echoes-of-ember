"""Validation for external Echoes of Ember level data."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from world.tile import TILE_DEFINITIONS
from systems.progression import KNOWN_COLLECTIBLE_TYPES


class LevelValidationError(ValueError):
    """Raised when external level content cannot be safely loaded."""


def validate_level_data(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["level root must be a JSON object"]

    required = {"name", "width", "height", "tile_size", "player_spawn", "tiles"}
    for field in sorted(required - data.keys()):
        errors.append(f"missing required field: {field}")
    if errors:
        return errors

    width = data.get("width")
    height = data.get("height")
    tile_size = data.get("tile_size")
    if not isinstance(width, int) or isinstance(width, bool) or width <= 0:
        errors.append("width must be a positive integer")
    if not isinstance(height, int) or isinstance(height, bool) or height <= 0:
        errors.append("height must be a positive integer")
    if not isinstance(tile_size, int) or isinstance(tile_size, bool) or tile_size < 8:
        errors.append("tile_size must be an integer of at least 8")

    spawn = data.get("player_spawn")
    if not _numeric_pair(spawn):
        errors.append("player_spawn must contain two numeric coordinates")

    tiles = data.get("tiles")
    if not isinstance(tiles, list):
        errors.append("tiles must be a list")
        return errors
    if not isinstance(width, int) or not isinstance(height, int):
        return errors

    for index, placement in enumerate(tiles):
        prefix = f"tiles[{index}]"
        if not isinstance(placement, dict):
            errors.append(f"{prefix} must be an object")
            continue
        tile_id = placement.get("id")
        if not isinstance(tile_id, int) or isinstance(tile_id, bool) or tile_id not in TILE_DEFINITIONS:
            errors.append(f"{prefix} has unknown tile id: {tile_id!r}")
        position = placement.get("position")
        size = placement.get("size", [1, 1])
        if not _integer_pair(position):
            errors.append(f"{prefix}.position must contain two integers")
            continue
        if not _integer_pair(size) or size[0] <= 0 or size[1] <= 0:
            errors.append(f"{prefix}.size must contain two positive integers")
            continue
        x, y = position
        region_width, region_height = size
        if x < 0 or y < 0 or x + region_width > width or y + region_height > height:
            errors.append(f"{prefix} extends outside level bounds")

    objects = data.get("objects", [])
    if not isinstance(objects, list):
        errors.append("objects must be a list")
        return errors
    seen_ids: set[str] = set()
    pixel_width = width * tile_size if isinstance(tile_size, int) else 0
    pixel_height = height * tile_size if isinstance(tile_size, int) else 0
    for index, entry in enumerate(objects):
        prefix = f"objects[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be an object")
            continue
        collectible_type = entry.get("type")
        if collectible_type not in KNOWN_COLLECTIBLE_TYPES:
            errors.append(f"{prefix} has unknown collectible type: {collectible_type!r}")
        object_id = entry.get("id", f"object_{index}")
        if not isinstance(object_id, str) or not object_id.strip():
            errors.append(f"{prefix}.id must be a non-empty string when provided")
        elif object_id in seen_ids:
            errors.append(f"{prefix} has duplicate id: {object_id!r}")
        else:
            seen_ids.add(object_id)
        for coordinate in ("x", "y"):
            value = entry.get(coordinate)
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
            ):
                errors.append(f"{prefix}.{coordinate} must be a finite number")
        x_value = entry.get("x")
        y_value = entry.get("y")
        if (
            isinstance(x_value, (int, float))
            and not isinstance(x_value, bool)
            and math.isfinite(x_value)
            and isinstance(y_value, (int, float))
            and not isinstance(y_value, bool)
            and math.isfinite(y_value)
            and not (0 <= x_value < pixel_width and 0 <= y_value < pixel_height)
        ):
            errors.append(f"{prefix} is outside level pixel bounds")
    return errors


def load_and_validate_level(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise LevelValidationError(f"could not read level {path}: {exc}") from exc
    errors = validate_level_data(data)
    if errors:
        details = "; ".join(errors)
        raise LevelValidationError(f"invalid level {path}: {details}")
    return data


def _numeric_pair(value: object) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value)
    )


def _integer_pair(value: object) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and all(isinstance(item, int) and not isinstance(item, bool) for item in value)
    )
