"""Validated level loading and runtime level model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tools.validation import load_and_validate_level
from systems.progression import CollectibleType
from systems.enemy_config import EnemyType
from systems.powerup_system import PowerUpType
from systems.level_completion import CompletionRequirements, RatingThresholds
from world.tilemap import TileMap
from world.secret_area import SecretDefinition, SecretTrigger, SecretType
from world.boss_arena import BossArenaDefinition


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


@dataclass(frozen=True, slots=True)
class GoalDefinition:
    kind: str
    position: tuple[float, float]
    requires_interact: bool


@dataclass(frozen=True, slots=True)
class LevelMetadata:
    level_id: str
    world_id: str
    level_number: int
    display_name: str
    description: str
    theme: str
    time_target: float
    declared_shards: int
    declared_rare_crystals: int
    declared_secret_tokens: int
    requirements: CompletionRequirements
    ratings: RatingThresholds


@dataclass(slots=True)
class Level:
    name: str
    metadata: LevelMetadata
    goal: GoalDefinition
    player_spawn: tuple[float, float]
    tilemap: TileMap
    collectible_spawns: tuple[CollectibleSpawn, ...]
    enemy_spawns: tuple[EnemySpawn, ...]
    powerup_spawns: tuple[PowerUpSpawn, ...]
    world_object_spawns: tuple[WorldObjectSpawn, ...]
    secret_definitions: tuple[SecretDefinition, ...]
    boss_encounter: BossArenaDefinition | None
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
        secret_definitions = tuple(
            SecretDefinition(
                secret_id=str(entry["id"]), kind=SecretType(entry["secret_type"]),
                trigger=SecretTrigger(entry["properties"]["trigger_type"]),
                bounds=tuple(float(value) for value in entry["properties"]["bounds"]),
                enemy_ids=tuple(entry["properties"].get("enemy_ids", [])),
                reward_score=entry["properties"].get("reward_score"),
                clue=str(entry["properties"].get("clue", "")),
            )
            for entry in data.get("secrets", [])
        )
        requirements = data["completion_requirements"]
        ratings = data["rating_thresholds"]
        metadata = LevelMetadata(
            level_id=str(data["id"]), world_id=str(data["world_id"]),
            level_number=int(data["level_number"]), display_name=str(data["display_name"]),
            description=str(data["description"]), theme=str(data["theme"]),
            time_target=float(data["time_target"]), declared_shards=int(data["shard_total"]),
            declared_rare_crystals=int(data["rare_crystal_total"]),
            declared_secret_tokens=int(data["secret_token_total"]),
            requirements=CompletionRequirements(bool(requirements["reach_goal"]), int(requirements.get("minimum_ember_shards", 0))),
            ratings=RatingThresholds(int(ratings["silver_score"]), int(ratings["gold_score"]), float(ratings["gold_shard_ratio"]), float(ratings["gold_time"])),
        )
        goal_data = data["goal"]
        goal = GoalDefinition(str(goal_data["type"]), (float(goal_data["x"]), float(goal_data["y"])), bool(goal_data.get("properties", {}).get("requires_interact", True)))
        boss_data = data.get("boss_encounter")
        boss_encounter = None
        if boss_data is not None:
            boss_encounter = BossArenaDefinition(
                boss_id=str(boss_data["boss_id"]),
                spawn=(float(boss_data["boss_spawn"][0]), float(boss_data["boss_spawn"][1])),
                bounds=__import__("pygame").Rect(*[round(value) for value in boss_data["arena_bounds"]]),
                trigger=__import__("pygame").Rect(*[round(value) for value in boss_data["trigger_bounds"]]),
                door_ids=tuple(str(value) for value in boss_data["door_ids"]),
                pulse_source=(float(boss_data["pulse_source"][0]), float(boss_data["pulse_source"][1])),
            )
        return cls(
            name=str(data["name"]),
            metadata=metadata,
            goal=goal,
            player_spawn=(float(spawn[0]), float(spawn[1])),
            tilemap=TileMap.from_data(data),
            collectible_spawns=collectible_spawns,
            enemy_spawns=enemy_spawns,
            powerup_spawns=powerup_spawns,
            world_object_spawns=world_object_spawns,
            secret_definitions=secret_definitions,
            boss_encounter=boss_encounter,
            source_path=path,
        )


def _world_properties(entry: dict[str, object]) -> dict[str, object]:
    properties = dict(entry.get("properties", {}))
    if entry["type"] == "switch":
        target = properties.pop("target_id", None)
        if target is not None:
            properties["target_ids"] = [target]
    return properties
