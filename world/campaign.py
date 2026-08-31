"""Validated campaign registry and in-memory world progress."""

from __future__ import annotations
from dataclasses import dataclass, field
import json
from pathlib import Path
from settings import PROJECT_ROOT
from systems.level_completion import LevelResult
from tools.validation import load_and_validate_level
from world.world_map import MapDefinitionError, WorldMapDefinition

class WorldRegistryError(ValueError):
    """Invalid campaign data or an unknown registered level."""

@dataclass(frozen=True, slots=True)
class WorldRegistry:
    world_id: str
    display_name: str
    level_ids: tuple[str, ...]
    level_paths: dict[str, Path]
    map_definition: WorldMapDefinition

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
        secret_exit_refs: set[tuple[str, str]] = set()
        for level_id in levels:
            level_path = PROJECT_ROOT / "data" / "levels" / f"{level_id}.json"
            if not level_path.is_file():
                errors.append(f"unknown level reference: {level_id}")
                continue
            level_data = load_and_validate_level(level_path)
            if level_data["id"] != level_id: errors.append(f"level id mismatch: {level_id}")
            if level_data["world_id"] != world_id: errors.append(f"wrong world for level: {level_id}")
            paths[level_id] = level_path
            secret_exit_refs.update((level_id, item["id"]) for item in level_data.get("secrets", []) if item.get("secret_type") == "secret_exit")
        try:
            map_definition = WorldMapDefinition.from_data(data.get("map"), tuple(levels), secret_exit_refs)
        except MapDefinitionError as exc:
            errors.append(str(exc))
            map_definition = None
        if errors:
            raise WorldRegistryError("; ".join(errors))
        assert map_definition is not None
        return cls(world_id, display_name, tuple(levels), paths, map_definition)

@dataclass(slots=True)
class WorldProgress:
    """Most recent result per level; replays replace rather than double-count."""
    registry: WorldRegistry
    results: dict[str, LevelResult] = field(default_factory=dict)
    completed_levels_once: set[str] = field(default_factory=set)
    discovered_secret_exits: set[tuple[str, str]] = field(default_factory=set)
    revealed_map_nodes: set[str] = field(default_factory=set)
    world_completed_once: bool = False
    def record(self, result: LevelResult) -> None:
        if result.level_id not in self.registry.level_ids: raise WorldRegistryError(f"result is outside world: {result.level_id}")
        self.results[result.level_id] = result
        self.completed_levels_once.add(result.level_id)
        if result.exit_type.value == "secret_exit":
            discovery = (result.level_id, result.exit_id)
            self.discovered_secret_exits.add(discovery)
            for connection in self.registry.map_definition.connections:
                requirement = connection.unlock
                if requirement.kind.value == "secret_exit_discovered" and (requirement.level_id, requirement.exit_id) == discovery:
                    self.revealed_map_nodes.add(connection.target)
        if all(level_id in self.completed_levels_once for level_id in self.registry.level_ids):
            self.world_completed_once = True
    @property
    def complete(self) -> bool: return self.world_completed_once
    @property
    def progression_flags(self) -> frozenset[str]:
        flags = {f"level_complete:{item}" for item in self.completed_levels_once}
        flags.update(f"secret_exit:{level}:{exit_id}" for level, exit_id in self.discovered_secret_exits)
        flags.update(f"node_revealed:{item}" for item in self.revealed_map_nodes)
        if self.world_completed_once:
            flags.add("world_complete")
        return frozenset(flags)
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
