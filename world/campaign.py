"""Validated world/campaign registries and in-memory progress for one world or the whole campaign."""

from __future__ import annotations
from dataclasses import dataclass, field
import json
from pathlib import Path
from settings import PROJECT_ROOT
from systems.level_completion import LevelResult
from tools.validation import load_and_validate_level
from world.themes import MAP_THEMES
from world.world_map import MapDefinitionError, WorldMapDefinition, requirement_leaves


DATA_ROOT = PROJECT_ROOT / "data"


class WorldRegistryError(ValueError):
    """Invalid campaign data or an unknown registered level."""


@dataclass(frozen=True, slots=True)
class WorldRegistry:
    world_id: str
    display_name: str
    level_ids: tuple[str, ...]
    level_paths: dict[str, Path]
    map_definition: WorldMapDefinition
    boss_ids: tuple[str, ...]
    boss_level_ids: tuple[str, ...]
    boss_display_names: dict[str, str] = field(default_factory=dict)
    map_theme: str = "verdant"

    @classmethod
    def load(cls, path: Path, data_root: Path | None = None) -> "WorldRegistry":
        data_root = Path(data_root) if data_root is not None else DATA_ROOT
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorldRegistryError(f"could not read world registry: {exc}") from exc
        errors: list[str] = []
        world_id = data.get("id") if isinstance(data, dict) else None
        display_name = data.get("display_name") if isinstance(data, dict) else None
        levels = data.get("levels") if isinstance(data, dict) else None
        if not isinstance(world_id, str) or not world_id.strip():
            errors.append("world id must be non-empty")
        if not isinstance(display_name, str) or not display_name.strip():
            errors.append("display name must be non-empty")
        if not isinstance(levels, list) or not levels or not all(isinstance(item, str) and item for item in levels):
            errors.append("levels must be a non-empty string list")
            levels = []
        if len(levels) != len(set(levels)):
            errors.append("duplicate level reference")
        theme = data.get("map_theme", "verdant") if isinstance(data, dict) else "verdant"
        if theme not in MAP_THEMES:
            errors.append(f"unknown map_theme: {theme!r}")
        paths: dict[str, Path] = {}
        secret_exit_refs: set[tuple[str, str]] = set()
        for level_id in levels:
            level_path = data_root / "levels" / f"{level_id}.json"
            if not level_path.is_file():
                errors.append(f"unknown level reference: {level_id}")
                continue
            level_data = load_and_validate_level(level_path, bosses_root=data_root / "bosses")
            if level_data["id"] != level_id:
                errors.append(f"level id mismatch: {level_id}")
            if level_data["world_id"] != world_id:
                errors.append(f"wrong world for level: {level_id}")
            paths[level_id] = level_path
            secret_exit_refs.update(
                (level_id, item["id"])
                for item in level_data.get("secrets", [])
                if item.get("secret_type") == "secret_exit"
            )
        try:
            map_definition = WorldMapDefinition.from_data(data.get("map"), tuple(levels), secret_exit_refs)
        except MapDefinitionError as exc:
            errors.append(str(exc))
            map_definition = None
        if errors:
            raise WorldRegistryError("; ".join(errors))
        assert map_definition is not None
        boss_nodes = tuple(node for node in map_definition.nodes.values() if node.kind.value == "boss")
        boss_names: dict[str, str] = {}
        for node in boss_nodes:
            boss_names[node.boss_id] = _boss_display_name(node.boss_id, data_root)
        return cls(
            world_id,
            display_name,
            tuple(levels),
            paths,
            map_definition,
            tuple(node.boss_id for node in boss_nodes),
            tuple(node.level_id for node in boss_nodes),
            boss_names,
            theme,
        )


def _boss_display_name(boss_id: str, data_root: Path) -> str:
    path = data_root / "bosses" / f"{boss_id}.json"
    try:
        name = json.loads(path.read_text(encoding="utf-8")).get("display_name")
    except (OSError, json.JSONDecodeError, AttributeError) as exc:
        raise WorldRegistryError(f"boss config missing or unreadable for {boss_id}: {exc}") from exc
    if not isinstance(name, str) or not name.strip():
        raise WorldRegistryError(f"boss config for {boss_id} needs a display_name")
    return name


@dataclass(slots=True)
class WorldProgress:
    """Most recent result per level; replays replace rather than double-count."""

    registry: WorldRegistry
    results: dict[str, LevelResult] = field(default_factory=dict)
    completed_levels_once: set[str] = field(default_factory=set)
    discovered_secret_exits: set[tuple[str, str]] = field(default_factory=set)
    revealed_map_nodes: set[str] = field(default_factory=set)
    world_completed_once: bool = False
    defeated_bosses: set[str] = field(default_factory=set)
    dialogue_flags: set[str] = field(default_factory=set)

    def record(self, result: LevelResult) -> None:
        if result.level_id not in self.registry.level_ids:
            raise WorldRegistryError(f"result is outside world: {result.level_id}")
        self.results[result.level_id] = result
        self.completed_levels_once.add(result.level_id)
        if result.exit_type.value == "secret_exit":
            discovery = (result.level_id, result.exit_id)
            self.discovered_secret_exits.add(discovery)
            for connection in self.registry.map_definition.connections:
                if any(
                    requirement.kind.value == "secret_exit_discovered"
                    and (requirement.level_id, requirement.exit_id) == discovery
                    for requirement in requirement_leaves(connection.unlock)
                ):
                    self.revealed_map_nodes.add(connection.target)

    def record_boss_defeat(self, boss_id: str, result: LevelResult) -> None:
        if boss_id not in self.registry.boss_ids:
            raise WorldRegistryError(f"unknown boss: {boss_id}")
        self.record(result)
        self.defeated_bosses.add(boss_id)
        self.world_completed_once = bool(self.registry.boss_ids) and set(self.registry.boss_ids) <= self.defeated_bosses

    @property
    def complete(self) -> bool:
        return self.world_completed_once

    @property
    def progression_flags(self) -> frozenset[str]:
        flags = {f"level_complete:{item}" for item in self.completed_levels_once}
        flags.update(f"secret_exit:{level}:{exit_id}" for level, exit_id in self.discovered_secret_exits)
        flags.update(f"node_revealed:{item}" for item in self.revealed_map_nodes)
        flags.update(f"boss_defeated:{item}" for item in self.defeated_bosses)
        if self.world_completed_once:
            flags.add("world_complete")
        return frozenset(flags)

    @property
    def levels_completed(self) -> int:
        return len(self.results)

    @property
    def score(self) -> int:
        return sum(item.score for item in self.results.values())

    @property
    def completion_time(self) -> float:
        return sum(item.completion_time for item in self.results.values())

    @property
    def deaths(self) -> int:
        return sum(item.deaths for item in self.results.values())

    def aggregate(self, collected: str, total: str) -> tuple[int, int]:
        return sum(getattr(item, collected) for item in self.results.values()), sum(
            getattr(item, total) for item in self.results.values()
        )

    @property
    def secrets(self) -> tuple[int, int]:
        return self.aggregate("secrets_discovered", "secrets_total")


DEFAULT_WORLD_REGISTRY = DATA_ROOT / "worlds" / "verdant_reaches.json"
DEFAULT_CAMPAIGN = DATA_ROOT / "campaign.json"


@dataclass(frozen=True, slots=True)
class CampaignRegistry:
    """Ordered worlds of the whole game. World N unlocks once world N-1 is truly complete."""

    worlds: tuple[WorldRegistry, ...]

    @classmethod
    def load(cls, path: Path = DEFAULT_CAMPAIGN) -> "CampaignRegistry":
        path = Path(path)
        data_root = path.parent
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorldRegistryError(f"could not read campaign: {exc}") from exc
        world_ids = data.get("worlds") if isinstance(data, dict) else None
        if not isinstance(world_ids, list) or not world_ids or not all(isinstance(x, str) and x for x in world_ids):
            raise WorldRegistryError("campaign.worlds must be a non-empty list of world IDs")
        if len(world_ids) != len(set(world_ids)):
            raise WorldRegistryError("campaign contains a duplicate world")
        worlds = []
        for world_id in world_ids:
            world_path = data_root / "worlds" / f"{world_id}.json"
            if not world_path.is_file():
                raise WorldRegistryError(f"campaign references missing world file: {world_id}")
            try:
                registry = WorldRegistry.load(world_path, data_root)
            except WorldRegistryError as exc:
                raise WorldRegistryError(f"world {world_id}: {exc}") from exc
            if registry.world_id != world_id:
                raise WorldRegistryError(f"world file {world_id}.json declares id {registry.world_id}")
            worlds.append(registry)
        return cls._validated(tuple(worlds))

    @classmethod
    def single(cls, registry: WorldRegistry) -> "CampaignRegistry":
        return cls._validated((registry,))

    @classmethod
    def coerce(cls, value: "CampaignRegistry | WorldRegistry") -> "CampaignRegistry":
        """Accept either a campaign or a single world (older call sites and tests pass one world)."""
        return value if isinstance(value, CampaignRegistry) else cls.single(value)

    @classmethod
    def _validated(cls, worlds: tuple[WorldRegistry, ...]) -> "CampaignRegistry":
        seen_levels: dict[str, str] = {}
        seen_bosses: dict[str, str] = {}
        for world in worlds:
            for level_id in world.level_ids:
                if level_id in seen_levels:
                    raise WorldRegistryError(
                        f"level {level_id} appears in {seen_levels[level_id]} and {world.world_id}"
                    )
                seen_levels[level_id] = world.world_id
            for boss_id in world.boss_ids:
                if boss_id in seen_bosses:
                    raise WorldRegistryError(f"boss {boss_id} appears in {seen_bosses[boss_id]} and {world.world_id}")
                seen_bosses[boss_id] = world.world_id
        return cls(worlds)

    @property
    def world_ids(self) -> tuple[str, ...]:
        return tuple(world.world_id for world in self.worlds)

    @property
    def level_paths(self) -> dict[str, Path]:
        merged: dict[str, Path] = {}
        for world in self.worlds:
            merged.update(world.level_paths)
        return merged

    def world(self, world_id: str) -> WorldRegistry:
        for world in self.worlds:
            if world.world_id == world_id:
                return world
        raise WorldRegistryError(f"unknown world: {world_id}")

    def world_for_level(self, level_id: str) -> WorldRegistry:
        for world in self.worlds:
            if level_id in world.level_paths:
                return world
        raise WorldRegistryError(f"unknown level id: {level_id}")

    def previous_world_id(self, world_id: str) -> str | None:
        index = self.world_ids.index(world_id)
        return self.world_ids[index - 1] if index > 0 else None


@dataclass(slots=True)
class CampaignProgress:
    """Progress for every world plus campaign-wide story flags.

    Each WorldProgress shares one dialogue-flag set, so a flag set in World 1 is visible everywhere.
    The aggregate properties below give dialogue/NPC conditions a whole-campaign view.
    """

    campaign: CampaignRegistry
    worlds: dict[str, WorldProgress]
    active_world_id: str

    @classmethod
    def fresh(cls, campaign: CampaignRegistry, dialogue_flags: set[str] | None = None) -> "CampaignProgress":
        flags = dialogue_flags if dialogue_flags is not None else set()
        worlds = {world.world_id: WorldProgress(world, dialogue_flags=flags) for world in campaign.worlds}
        return cls(campaign, worlds, campaign.world_ids[0])

    @property
    def active(self) -> WorldProgress:
        return self.worlds[self.active_world_id]

    @property
    def registry(self) -> WorldRegistry:
        return self.active.registry

    @property
    def dialogue_flags(self) -> set[str]:
        return self.worlds[self.campaign.world_ids[0]].dialogue_flags

    def world(self, world_id: str) -> WorldProgress:
        try:
            return self.worlds[world_id]
        except KeyError:
            raise WorldRegistryError(f"unknown world: {world_id}") from None

    def replace_world(self, progress: WorldProgress) -> None:
        world_id = progress.registry.world_id
        self.world(world_id)
        shared = self.dialogue_flags
        shared.update(progress.dialogue_flags)
        progress.dialogue_flags = shared
        self.worlds[world_id] = progress

    def world_unlocked(self, world_id: str) -> bool:
        previous = self.campaign.previous_world_id(self.world(world_id).registry.world_id)
        return previous is None or self.worlds[previous].world_completed_once

    def set_active_world(self, world_id: str) -> None:
        self.world(world_id)
        if not self.world_unlocked(world_id):
            raise WorldRegistryError(f"world {world_id} is locked until the previous world is complete")
        self.active_world_id = world_id

    # Whole-campaign views used by dialogue and NPC conditions.
    @property
    def completed_levels_once(self) -> set[str]:
        return set().union(*(item.completed_levels_once for item in self.worlds.values()))

    @property
    def defeated_bosses(self) -> set[str]:
        return set().union(*(item.defeated_bosses for item in self.worlds.values()))

    @property
    def discovered_secret_exits(self) -> set[tuple[str, str]]:
        return set().union(*(item.discovered_secret_exits for item in self.worlds.values()))

    @property
    def results(self) -> dict[str, LevelResult]:
        merged: dict[str, LevelResult] = {}
        for item in self.worlds.values():
            merged.update(item.results)
        return merged

    @property
    def world_completed_once(self) -> bool:
        return self.active.world_completed_once

    @property
    def completed_world_ids(self) -> set[str]:
        return {world_id for world_id, item in self.worlds.items() if item.world_completed_once}

    @property
    def levels_completed(self) -> int:
        return sum(item.levels_completed for item in self.worlds.values())

    @property
    def score(self) -> int:
        return sum(item.score for item in self.worlds.values())

    def aggregate(self, collected: str, total: str) -> tuple[int, int]:
        pairs = [item.aggregate(collected, total) for item in self.worlds.values()]
        return sum(a for a, _ in pairs), sum(b for _, b in pairs)

    @property
    def secrets(self) -> tuple[int, int]:
        return self.aggregate("secrets_discovered", "secrets_total")
