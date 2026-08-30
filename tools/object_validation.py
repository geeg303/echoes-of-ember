"""Structured validation for collectible and enemy level objects."""

from __future__ import annotations

import math
from typing import Any

from systems.enemy_config import (
    COMMON_ENEMY_PROPERTY_TYPES,
    ENEMY_PROPERTY_TYPES,
    EnemyType,
)
from systems.progression import KNOWN_COLLECTIBLE_TYPES


def validate_objects(
    objects: Any,
    pixel_width: int,
    pixel_height: int,
) -> list[str]:
    if not isinstance(objects, list):
        return ["objects must be a list"]
    errors: list[str] = []
    seen_ids: set[str] = set()
    for index, entry in enumerate(objects):
        prefix = f"objects[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be an object")
            continue
        object_type = entry.get("type")
        object_id = entry.get("id", f"object_{index}" if object_type != "enemy" else None)
        if not isinstance(object_id, str) or not object_id.strip():
            errors.append(f"{prefix}.id must be a non-empty string when provided")
        elif object_id in seen_ids:
            errors.append(f"{prefix} has duplicate id: {object_id!r}")
        else:
            seen_ids.add(object_id)
        _validate_coordinates(entry, prefix, pixel_width, pixel_height, errors)
        if object_type == "enemy":
            _validate_enemy(entry, prefix, errors)
        elif object_type not in KNOWN_COLLECTIBLE_TYPES:
            errors.append(f"{prefix} has unknown collectible type: {object_type!r}")
    return errors


def _validate_coordinates(
    entry: dict[str, Any],
    prefix: str,
    pixel_width: int,
    pixel_height: int,
    errors: list[str],
) -> None:
    valid: dict[str, float] = {}
    for coordinate in ("x", "y"):
        value = entry.get(coordinate)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
        ):
            errors.append(f"{prefix}.{coordinate} must be a finite number")
        else:
            valid[coordinate] = float(value)
    if len(valid) == 2 and not (
        0 <= valid["x"] < pixel_width and 0 <= valid["y"] < pixel_height
    ):
        errors.append(f"{prefix} is outside level pixel bounds")


def _validate_enemy(entry: dict[str, Any], prefix: str, errors: list[str]) -> None:
    raw_kind = entry.get("enemy_type")
    try:
        kind = EnemyType(raw_kind)
    except (ValueError, TypeError):
        if raw_kind is None:
            errors.append(f"{prefix} is missing enemy_type")
        else:
            errors.append(f"{prefix} has unknown enemy type: {raw_kind!r}")
        return
    properties = entry.get("properties", {})
    if not isinstance(properties, dict):
        errors.append(f"{prefix}.properties must be an object")
        return
    schema = {**COMMON_ENEMY_PROPERTY_TYPES, **ENEMY_PROPERTY_TYPES[kind]}
    for key, value in properties.items():
        if key not in schema:
            errors.append(f"{prefix}.properties has unknown property: {key!r}")
            continue
        expected = schema[key]
        if expected is bool:
            valid = isinstance(value, bool)
        elif expected is int:
            valid = isinstance(value, int) and not isinstance(value, bool) and value > 0
        else:
            valid = (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
                and value > 0
            )
        if not valid:
            errors.append(
                f"{prefix}.properties.{key} has incorrect type or value"
            )

