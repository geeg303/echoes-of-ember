"""Validated level loading and runtime level model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tools.validation import load_and_validate_level
from world.tilemap import TileMap


@dataclass(slots=True)
class Level:
    name: str
    player_spawn: tuple[float, float]
    tilemap: TileMap
    source_path: Path

    @classmethod
    def load(cls, path: Path) -> "Level":
        data = load_and_validate_level(path)
        spawn = data["player_spawn"]
        return cls(
            name=str(data["name"]),
            player_spawn=(float(spawn[0]), float(spawn[1])),
            tilemap=TileMap.from_data(data),
            source_path=path,
        )

