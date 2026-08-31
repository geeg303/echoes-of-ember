"""Validation for external Echoes of Ember level data."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from tools.object_validation import validate_objects
from world.tile import TILE_DEFINITIONS


class LevelValidationError(ValueError):
    """Raised when external level content cannot be safely loaded."""


def validate_level_data(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["level root must be a JSON object"]

    core_required = {"name", "width", "height", "tile_size", "player_spawn", "tiles"}
    metadata_required = {
        "id", "name", "world_id", "level_number", "display_name", "description",
        "theme", "time_target", "shard_total", "rare_crystal_total",
        "secret_token_total", "completion_requirements", "rating_thresholds", "goal",
    }
    for field in sorted(core_required - data.keys()):
        errors.append(f"missing required field: {field}")
    if errors:
        return errors
    for field in sorted(metadata_required - data.keys()):
        errors.append(f"missing required field: {field}")
    _validate_metadata(data, errors)

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
    elif isinstance(width, int) and isinstance(height, int) and isinstance(tile_size, int):
        if not all(math.isfinite(float(value)) for value in spawn) or not (0 <= spawn[0] < width * tile_size and 0 <= spawn[1] < height * tile_size):
            errors.append("player_spawn is outside level pixel bounds or non-finite")

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

    pixel_width = width * tile_size if isinstance(tile_size, int) else 0
    pixel_height = height * tile_size if isinstance(tile_size, int) else 0
    errors.extend(validate_objects(data.get("objects", []), pixel_width, pixel_height))
    _validate_goal(data.get("goal"), pixel_width, pixel_height, errors)
    if isinstance(data.get("objects"), list):
        counts = {
            "shard_total": sum(entry.get("type") == "ember_shard" for entry in data["objects"] if isinstance(entry, dict)),
            "rare_crystal_total": sum(entry.get("type") == "rare_crystal" for entry in data["objects"] if isinstance(entry, dict)),
            "secret_token_total": sum(entry.get("type") == "secret_token" for entry in data["objects"] if isinstance(entry, dict)),
        }
        for field, derived in counts.items():
            if data.get(field) != derived:
                errors.append(f"{field} does not match derived object total {derived}")
    return errors


def _validate_metadata(data: dict[str, Any], errors: list[str]) -> None:
    for field in ("id", "world_id", "display_name", "description", "theme"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field} must be a non-empty string")
    world_id = data.get("world_id")
    if isinstance(world_id, str) and (not world_id.replace("_", "").isalnum() or world_id.lower() != world_id):
        errors.append("world_id must use lowercase letters, numbers, and underscores")
    if not isinstance(data.get("level_number"), int) or isinstance(data.get("level_number"), bool) or data["level_number"] <= 0:
        errors.append("level_number must be a positive integer")
    for field in ("time_target",):
        value = data.get(field)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value <= 0:
            errors.append(f"{field} must be positive")
    for field in ("shard_total", "rare_crystal_total", "secret_token_total"):
        value = data.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f"{field} must be a non-negative integer")
    requirements = data.get("completion_requirements")
    if not isinstance(requirements, dict):
        errors.append("completion_requirements must be an object")
    else:
        allowed = {"reach_goal", "minimum_ember_shards"}
        if set(requirements) - allowed:
            errors.append("completion_requirements contains unsupported values")
        if not isinstance(requirements.get("reach_goal"), bool):
            errors.append("completion_requirements.reach_goal must be boolean")
        minimum = requirements.get("minimum_ember_shards", 0)
        if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 0:
            errors.append("completion_requirements.minimum_ember_shards must be non-negative")
    ratings = data.get("rating_thresholds")
    required_ratings = {"silver_score", "gold_score", "gold_shard_ratio", "gold_time"}
    if not isinstance(ratings, dict) or not required_ratings <= ratings.keys():
        errors.append("rating_thresholds is malformed")
    else:
        for field in ("silver_score", "gold_score", "gold_time"):
            value = ratings[field]
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
                errors.append(f"rating_thresholds.{field} must be non-negative")
        ratio = ratings["gold_shard_ratio"]
        if not isinstance(ratio, (int, float)) or isinstance(ratio, bool) or not math.isfinite(ratio) or not 0 <= ratio <= 1:
            errors.append("rating_thresholds.gold_shard_ratio must be between 0 and 1")


def _validate_goal(goal: object, pixel_width: int, pixel_height: int, errors: list[str]) -> None:
    if not isinstance(goal, dict):
        errors.append("goal must be an object")
        return
    if goal.get("type") != "ember_gate":
        errors.append(f"goal has unsupported type: {goal.get('type')!r}")
    if not _numeric_pair([goal.get("x"), goal.get("y")]) or not all(math.isfinite(float(value)) for value in (goal.get("x"), goal.get("y")) if isinstance(value, (int, float))):
        errors.append("goal coordinates must be numeric")
    else:
        x, y = float(goal["x"]), float(goal["y"])
        if not (0 <= x < pixel_width and 0 <= y < pixel_height):
            errors.append("goal is outside level bounds")
    properties = goal.get("properties", {})
    if not isinstance(properties, dict) or any(key != "requires_interact" for key in properties):
        errors.append("goal properties are malformed")
    elif "requires_interact" in properties and not isinstance(properties["requires_interact"], bool):
        errors.append("goal.properties.requires_interact must be boolean")


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


def main() -> int:
    import argparse
    from settings import PROJECT_ROOT
    parser = argparse.ArgumentParser(description="Validate Echoes of Ember level data")
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--all-levels", action="store_true")
    args = parser.parse_args()
    paths = sorted((PROJECT_ROOT / "data" / "levels").glob("*.json")) if args.all_levels else [args.path]
    if not paths or paths == [None]:
        parser.error("provide a level path or --all-levels")
    for path in paths:
        load_and_validate_level(path)
        print(f"valid: {path}")
    if args.all_levels:
        from world.campaign import DEFAULT_WORLD_REGISTRY, WorldRegistry
        registry = WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
        print(f"valid world: {registry.world_id} ({len(registry.level_ids)} levels)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
