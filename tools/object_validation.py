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
from systems.powerup_system import PowerUpType

WORLD_OBJECT_TYPES = frozenset({"moving_platform", "falling_platform", "disappearing_platform", "switch", "door", "checkpoint"})


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
        object_id = entry.get(
            "id",
            f"object_{index}" if object_type in KNOWN_COLLECTIBLE_TYPES else None,
        )
        if not isinstance(object_id, str) or not object_id.strip():
            errors.append(f"{prefix}.id must be a non-empty string when provided")
        elif object_id in seen_ids:
            errors.append(f"{prefix} has duplicate id: {object_id!r}")
        else:
            seen_ids.add(object_id)
        _validate_coordinates(entry, prefix, pixel_width, pixel_height, errors)
        if object_type == "enemy":
            _validate_enemy(entry, prefix, errors)
        elif object_type == "powerup":
            _validate_powerup(entry, prefix, errors)
        elif object_type in WORLD_OBJECT_TYPES:
            _validate_world_object(entry, prefix, errors)
        elif object_type not in KNOWN_COLLECTIBLE_TYPES:
            errors.append(f"{prefix} has unknown collectible type: {object_type!r}")
    _validate_references(objects, errors)
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


def _validate_powerup(entry: dict[str, Any], prefix: str, errors: list[str]) -> None:
    raw_kind = entry.get("powerup_type")
    try:
        PowerUpType(raw_kind)
    except (ValueError, TypeError):
        errors.append(
            f"{prefix} is missing powerup_type" if raw_kind is None
            else f"{prefix} has unknown power-up type: {raw_kind!r}"
        )
    properties = entry.get("properties", {})
    if not isinstance(properties, dict):
        errors.append(f"{prefix}.properties must be an object")
        return
    for key, value in properties.items():
        if key != "duration":
            errors.append(f"{prefix}.properties has unknown property: {key!r}")
        elif not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value <= 0:
            errors.append(f"{prefix}.properties.duration has incorrect type or value")


WORLD_PROPERTY_SCHEMAS: dict[str, dict[str, type]] = {
    "moving_platform": {"movement": str, "distance": float, "speed": float, "width": int, "height": int},
    "falling_platform": {"activation_delay": float, "fall_acceleration": float, "reset_delay": float, "width": int, "height": int},
    "disappearing_platform": {"visible_duration": float, "warning_duration": float, "hidden_duration": float, "width": int, "height": int},
    "switch": {"target_id": str, "target_ids": list},
    "door": {"opening_duration": float, "width": int, "height": int},
    "checkpoint": {},
}


def _validate_world_object(entry: dict[str, Any], prefix: str, errors: list[str]) -> None:
    kind = entry["type"]
    properties = entry.get("properties", {})
    if not isinstance(properties, dict):
        errors.append(f"{prefix}.properties must be an object")
        return
    required = {"moving_platform": {"movement", "distance", "speed"}, "switch": set()}.get(kind, set())
    if kind == "switch" and not ({"target_id", "target_ids"} & properties.keys()):
        errors.append(f"{prefix}.properties requires target_id or target_ids")
    for key in sorted(required - properties.keys()):
        errors.append(f"{prefix}.properties is missing {key}")
    schema = WORLD_PROPERTY_SCHEMAS[kind]
    for key, value in properties.items():
        if key not in schema:
            errors.append(f"{prefix}.properties has unknown property: {key!r}")
            continue
        expected = schema[key]
        if key == "movement":
            valid = value in {"horizontal", "vertical"}
        elif key == "target_ids":
            valid = isinstance(value, list) and bool(value) and all(isinstance(item, str) and item for item in value)
        elif expected is str:
            valid = isinstance(value, str) and bool(value)
        elif expected is int:
            valid = isinstance(value, int) and not isinstance(value, bool) and value > 0
        else:
            valid = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0
        if not valid:
            errors.append(f"{prefix}.properties.{key} has incorrect type or value")


def _validate_references(objects: list[Any], errors: list[str]) -> None:
    ids = {entry.get("id"): entry.get("type") for entry in objects if isinstance(entry, dict) and isinstance(entry.get("id"), str)}
    for index, entry in enumerate(objects):
        if not isinstance(entry, dict) or entry.get("type") != "switch" or not isinstance(entry.get("properties", {}), dict):
            continue
        properties = entry["properties"]
        targets = properties.get("target_ids", [properties.get("target_id")])
        if not isinstance(targets, list):
            continue
        for target in targets:
            if isinstance(target, str) and ids.get(target) != "door":
                errors.append(f"objects[{index}] references missing or incompatible door: {target!r}")
