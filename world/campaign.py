"""Validated campaign registry and in-memory world progress."""

from __future__ import annotations
from dataclasses import dataclass, field
import json
from pathlib import Path
from settings import PROJECT_ROOT
from systems.level_completion import LevelResult
from tools.validation import load_and_validate_level

class WorldRegistryError(ValueError):
    """Invalid campaign data or an unknown registered level."""

@dataclass(frozen=True, slots=True)
class WorldRegistry:
    world_id: str
    display_name: str
    level_ids: tuple[str, ...]
    level_paths: dict[str, Path]

    @classmethod
    def load(cls, path: Path) -> "WorldRegistry":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorldRegistryError(f"could not read world registry: {exc}") from exc
        errors: list[str] = []
        world_id = data.get("id") if isinstance(data, dict) else None
        display_name = data.get("display_name") if isinstance(data, dict) else None
        levels = data.get("levels") if isinstance(data, dict) else None
        if not isinstance(world_id, str) or not world_id.strip(): errors.append("world id must be non-empty")
        if not isinstance(display_name, str) or not display_name.strip(): errors.append("display name must be non-empty")
        if not isinstance(levels, list) or not levels or not all(isinstance(item, str) and item for item in levels):
            errors.append("levels must be a non-empty string list")
            levels = []
        if len(levels) != len(set(levels)): errors.append("duplicate level reference")
        paths: dict[str, Path] = {}
        for level_id in levels:
            level_path = PROJECT_ROOT / "data" / "levels" / f"{level_id}.json"
            if not level_path.is_file():
                errors.append(f"unknown level reference: {level_id}")
                continue
            level_data = load_and_validate_level(level_path)
            if level_data["id"] != level_id: errors.append(f"level id mismatch: {level_id}")
            if level_data["world_id"] != world_id: errors.append(f"wrong world for level: {level_id}")
            paths[level_id] = level_path
        if errors: raise WorldRegistryError("; ".join(errors))
        return cls(world_id, display_name, tuple(levels), paths)

    def next_level(self, level_id: str) -> str | None:
        try: index = self.level_ids.index(level_id)
        except ValueError as exc: raise WorldRegistryError(f"unknown level id: {level_id}") from exc
        return self.level_ids[index + 1] if index + 1 < len(self.level_ids) else None

@dataclass(slots=True)
class WorldProgress:
    """Most recent result per level; replays replace rather than double-count."""
    registry: WorldRegistry
    results: dict[str, LevelResult] = field(default_factory=dict)
    def record(self, result: LevelResult) -> None:
        if result.level_id not in self.registry.level_ids: raise WorldRegistryError(f"result is outside world: {result.level_id}")
        self.results[result.level_id] = result
    @property
    def complete(self) -> bool: return all(item in self.results for item in self.registry.level_ids)
    @property
    def levels_completed(self) -> int: return len(self.results)
    @property
    def score(self) -> int: return sum(item.score for item in self.results.values())
    @property
    def completion_time(self) -> float: return sum(item.completion_time for item in self.results.values())
    @property
    def deaths(self) -> int: return sum(item.deaths for item in self.results.values())
    def aggregate(self, collected: str, total: str) -> tuple[int, int]:
        return sum(getattr(item, collected) for item in self.results.values()), sum(getattr(item, total) for item in self.results.values())


    @property
    def secrets(self) -> tuple[int, int]:
        return self.aggregate("secrets_discovered", "secrets_total")

DEFAULT_WORLD_REGISTRY = PROJECT_ROOT / "data" / "worlds" / "verdant_reaches.json"
