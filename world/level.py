"""Validated level loading and runtime level model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tools.validation import load_and_validate_level
from systems.progression import CollectibleType
from systems.enemy_config import EnemyType
from systems.powerup_system import PowerUpType
from world.tilemap import TileMap


@dataclass(frozen=True, slots=True)
class CollectibleSpawn:
    object_id: str
    kind: CollectibleType
    position: tuple[float, float]


@dataclass(frozen=True, slots=True)
class EnemySpawn:
    object_id: str
    kind: EnemyType
    position: tuple[float, float]
    properties: dict[str, object]


@dataclass(frozen=True, slots=True)
class PowerUpSpawn:
    object_id: str
    kind: PowerUpType
    position: tuple[float, float]
    duration: float | None = None


@dataclass(frozen=True, slots=True)
class WorldObjectSpawn:
    object_id: str
    kind: str
    position: tuple[float, float]
    properties: dict[str, object]


@dataclass(slots=True)
class Level:
    name: str
    player_spawn: tuple[float, float]
    tilemap: TileMap
    collectible_spawns: tuple[CollectibleSpawn, ...]
    enemy_spawns: tuple[EnemySpawn, ...]
    powerup_spawns: tuple[PowerUpSpawn, ...]
    world_object_spawns: tuple[WorldObjectSpawn, ...]
    source_path: Path

    @classmethod
    def load(cls, path: Path) -> "Level":
        data = load_and_validate_level(path)
        spawn = data["player_spawn"]
        collectible_spawns = tuple(
            CollectibleSpawn(
                object_id=str(entry.get("id", f"object_{index}")),
                kind=CollectibleType(entry["type"]),
                position=(float(entry["x"]), float(entry["y"])),
            )
            for index, entry in enumerate(data.get("objects", []))
            if entry["type"] not in {"enemy", "powerup", "moving_platform", "falling_platform", "disappearing_platform", "switch", "door", "checkpoint"}
        )
        enemy_spawns = tuple(
            EnemySpawn(
                object_id=str(entry["id"]),
                kind=EnemyType(entry["enemy_type"]),
                position=(float(entry["x"]), float(entry["y"])),
                properties=dict(entry.get("properties", {})),
            )
            for entry in data.get("objects", [])
            if entry["type"] == "enemy"
        )
        powerup_spawns = tuple(
            PowerUpSpawn(
                object_id=str(entry["id"]),
                kind=PowerUpType(entry["powerup_type"]),
                position=(float(entry["x"]), float(entry["y"])),
                duration=float(entry["properties"]["duration"]) if "duration" in entry.get("properties", {}) else None,
            )
            for entry in data.get("objects", [])
            if entry["type"] == "powerup"
        )
        world_kinds = {"moving_platform", "falling_platform", "disappearing_platform", "switch", "door", "checkpoint"}
        world_object_spawns = tuple(
            WorldObjectSpawn(
                object_id=str(entry["id"]),
                kind=str(entry["type"]),
                position=(float(entry["x"]), float(entry["y"])),
                properties=_world_properties(entry),
            )
            for entry in data.get("objects", [])
            if entry["type"] in world_kinds
        )
        return cls(
            name=str(data["name"]),
            player_spawn=(float(spawn[0]), float(spawn[1])),
            tilemap=TileMap.from_data(data),
            collectible_spawns=collectible_spawns,
            enemy_spawns=enemy_spawns,
            powerup_spawns=powerup_spawns,
            world_object_spawns=world_object_spawns,
            source_path=path,
        )


def _world_properties(entry: dict[str, object]) -> dict[str, object]:
    properties = dict(entry.get("properties", {}))
    if entry["type"] == "switch":
        target = properties.pop("target_id", None)
        if target is not None:
            properties["target_ids"] = [target]
    return properties
