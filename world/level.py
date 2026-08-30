"""Validated level loading and runtime level model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tools.validation import load_and_validate_level
from systems.progression import CollectibleType
from systems.enemy_config import EnemyType
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


@dataclass(slots=True)
class Level:
    name: str
    player_spawn: tuple[float, float]
    tilemap: TileMap
    collectible_spawns: tuple[CollectibleSpawn, ...]
    enemy_spawns: tuple[EnemySpawn, ...]
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
            if entry["type"] != "enemy"
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
        return cls(
            name=str(data["name"]),
            player_spawn=(float(spawn[0]), float(spawn[1])),
            tilemap=TileMap.from_data(data),
            collectible_spawns=collectible_spawns,
            enemy_spawns=enemy_spawns,
            source_path=path,
        )
