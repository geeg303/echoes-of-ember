"""Versioned JSON-safe campaign snapshots and runtime reconstruction."""

from __future__ import annotations

from dataclasses import dataclass
import copy
from datetime import datetime, timezone
import math
import re
from typing import Any

from systems.level_completion import CompletionRating, ExitType, LevelResult
from world.campaign import WorldProgress, WorldRegistry


CURRENT_SAVE_VERSION = 3
_DIALOGUE_FLAG_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


class SaveValidationError(ValueError):
    """A save cannot be reconstructed safely."""


class UnsupportedSaveVersion(SaveValidationError):
    """A newer or unmigratable schema was encountered."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(slots=True)
class SaveSession:
    slot_id: int
    progress: WorldProgress
    current_map_node: str
    created_at: str
    updated_at: str
    play_time_seconds: float = 0.0
    dirty: bool = False

    @classmethod
    def fresh(cls, slot_id: int, registry: WorldRegistry) -> "SaveSession":
        now = utc_now()
        return cls(slot_id, WorldProgress(registry), registry.map_definition.start_node, now, now)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": CURRENT_SAVE_VERSION,
            "metadata": {
                "slot_id": self.slot_id,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
                "play_time_seconds": round(self.play_time_seconds, 3),
            },
            "campaign": {
                "active_world_id": self.progress.registry.world_id,
                "current_map_node": self.current_map_node,
                "level_results": {
                    level_id: _result_to_dict(result)
                    for level_id, result in sorted(self.progress.results.items())
                },
                "progression": {
                    "completed_levels_once": sorted(self.progress.completed_levels_once),
                    "discovered_secret_exits": [
                        {"level_id": level_id, "exit_id": exit_id}
                        for level_id, exit_id in sorted(self.progress.discovered_secret_exits)
                    ],
                    "revealed_map_nodes": sorted(self.progress.revealed_map_nodes),
                    "defeated_bosses": sorted(self.progress.defeated_bosses),
                    "dialogue_flags": sorted(self.progress.dialogue_flags),
                    "completed_worlds_once": (
                        [self.progress.registry.world_id] if self.progress.world_completed_once else []
                    ),
                },
            },
        }

    @classmethod
    def from_dict(cls, raw: object, registry: WorldRegistry, expected_slot: int) -> "SaveSession":
        data = migrate_save(raw)
        metadata = _mapping(data.get("metadata"), "metadata")
        campaign = _mapping(data.get("campaign"), "campaign")
        slot_id = _integer(metadata.get("slot_id"), "metadata.slot_id", minimum=1)
        if slot_id != expected_slot:
            raise SaveValidationError("save slot ID does not match requested slot")
        created = _timestamp(metadata.get("created_at"), "metadata.created_at")
        updated = _timestamp(metadata.get("updated_at"), "metadata.updated_at")
        play_time = _number(metadata.get("play_time_seconds"), "metadata.play_time_seconds", minimum=0)
        if campaign.get("active_world_id") != registry.world_id:
            raise SaveValidationError("save references an unknown active world")
        current_node = campaign.get("current_map_node")
        if current_node not in registry.map_definition.nodes:
            raise SaveValidationError("save references an unknown current map node")
        valid_exits = {
            (connection.unlock.level_id, connection.unlock.exit_id)
            for connection in registry.map_definition.connections
            if connection.unlock.exit_id is not None
        }
        boss_exit_ids = dict(zip(registry.boss_level_ids, registry.boss_ids, strict=True))
        raw_results = _mapping(campaign.get("level_results"), "campaign.level_results")
        progress = WorldProgress(registry)
        for level_id, result_raw in raw_results.items():
            if level_id not in registry.level_ids:
                raise SaveValidationError(f"save references unknown level: {level_id}")
            result = _result_from_dict(result_raw, level_id)
            if result.exit_type is ExitType.SECRET and (level_id, result.exit_id) not in valid_exits:
                raise SaveValidationError(f"level result {level_id} references an unknown secret exit")
            valid_normal_exit = result.exit_id == "ember_gate" or boss_exit_ids.get(level_id) == result.exit_id
            if result.exit_type is ExitType.NORMAL and not valid_normal_exit:
                raise SaveValidationError(f"level result {level_id} references an unknown normal exit")
            progress.results[level_id] = result
        progression = _mapping(campaign.get("progression"), "campaign.progression")
        progress.completed_levels_once = _unique_known_strings(
            progression.get("completed_levels_once"), set(registry.level_ids), "completed_levels_once"
        )
        exits = progression.get("discovered_secret_exits")
        if not isinstance(exits, list):
            raise SaveValidationError("discovered_secret_exits must be a list")
        parsed_exits: set[tuple[str, str]] = set()
        for entry in exits:
            item = _mapping(entry, "discovered_secret_exits entry")
            pair = (item.get("level_id"), item.get("exit_id"))
            if pair not in valid_exits:
                raise SaveValidationError("save references an unknown secret exit")
            if pair in parsed_exits:
                raise SaveValidationError("duplicate discovered secret exit")
            parsed_exits.add(pair)
        progress.discovered_secret_exits = parsed_exits
        progress.revealed_map_nodes = _unique_known_strings(
            progression.get("revealed_map_nodes"), set(registry.map_definition.nodes), "revealed_map_nodes"
        )
        progress.defeated_bosses = _unique_known_strings(
            progression.get("defeated_bosses"), set(registry.boss_ids), "defeated_bosses"
        )
        progress.dialogue_flags = _unique_dialogue_flags(
            progression.get("dialogue_flags"), "dialogue_flags"
        )
        worlds = _unique_known_strings(
            progression.get("completed_worlds_once"), {registry.world_id}, "completed_worlds_once"
        )
        progress.world_completed_once = registry.world_id in worlds
        boss_complete = bool(registry.boss_ids) and set(registry.boss_ids) <= progress.defeated_bosses
        if progress.world_completed_once != boss_complete:
            raise SaveValidationError("world completion does not match defeated bosses")
        return cls(slot_id, progress, str(current_node), created, updated, play_time)


def migrate_save(raw: object) -> dict[str, Any]:
    source = _mapping(raw, "save root")
    data = copy.deepcopy(source)
    version = data.get("schema_version")
    if not isinstance(version, int) or isinstance(version, bool):
        raise SaveValidationError("schema_version must be an integer")
    if version > CURRENT_SAVE_VERSION:
        raise UnsupportedSaveVersion("save was created by a newer game version")
    if version < 1:
        raise UnsupportedSaveVersion(f"no migration path from save version {version}")
    while version < CURRENT_SAVE_VERSION:
        if version == 1:
            data = _migrate_v1_to_v2(data)
        elif version == 2:
            data = _migrate_v2_to_v3(data)
        else:
            raise UnsupportedSaveVersion(f"no migration path from save version {version}")
        version = data["schema_version"]
    return data


def _migrate_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    campaign = _mapping(data.get("campaign"), "campaign")
    progression = _mapping(campaign.get("progression"), "campaign.progression")
    progression["defeated_bosses"] = []
    # V1 treated completion of the four platform stages as world completion.
    # V2 deliberately requires a real boss defeat, so the legacy flag is cleared.
    progression["completed_worlds_once"] = []
    data["schema_version"] = 2
    return data


def _migrate_v2_to_v3(data: dict[str, Any]) -> dict[str, Any]:
    campaign = _mapping(data.get("campaign"), "campaign")
    progression = _mapping(campaign.get("progression"), "campaign.progression")
    progression["dialogue_flags"] = []
    data["schema_version"] = 3
    return data


def _result_to_dict(result: LevelResult) -> dict[str, object]:
    return {
        "completed": result.completed,
        "completion_time": result.completion_time,
        "score": result.score,
        "ember_shards_collected": result.ember_shards_collected,
        "ember_shards_total": result.ember_shards_total,
        "rare_crystals_collected": result.rare_crystals_collected,
        "rare_crystals_total": result.rare_crystals_total,
        "secret_tokens_collected": result.secret_tokens_collected,
        "secret_tokens_total": result.secret_tokens_total,
        "enemies_defeated": result.enemies_defeated,
        "enemies_total": result.enemies_total,
        "deaths": result.deaths,
        "lives_remaining": result.lives_remaining,
        "health_remaining": result.health_remaining,
        "checkpoints_activated": result.checkpoints_activated,
        "rating": result.rating.value,
        "secrets_discovered": result.secrets_discovered,
        "secrets_total": result.secrets_total,
        "secret_rooms_completed": result.secret_rooms_completed,
        "exit_type": result.exit_type.value,
        "exit_id": result.exit_id,
    }


def _result_from_dict(raw: object, level_id: str) -> LevelResult:
    data = _mapping(raw, f"level result {level_id}")
    try:
        rating = CompletionRating(data.get("rating"))
        exit_type = ExitType(data.get("exit_type"))
    except (TypeError, ValueError) as exc:
        raise SaveValidationError(f"level result {level_id} has invalid enum values") from exc
    exit_id = data.get("exit_id")
    if not isinstance(exit_id, str) or not exit_id:
        raise SaveValidationError(f"level result {level_id} has invalid exit ID")
    completed = data.get("completed")
    if not isinstance(completed, bool):
        raise SaveValidationError(f"level result {level_id}.completed must be boolean")
    result = LevelResult(
        level_id=level_id,
        completed=completed,
        completion_time=_number(data.get("completion_time"), "completion_time", minimum=0),
        score=_integer(data.get("score"), "score", minimum=0),
        ember_shards_collected=_integer(data.get("ember_shards_collected"), "ember_shards_collected", minimum=0),
        ember_shards_total=_integer(data.get("ember_shards_total"), "ember_shards_total", minimum=0),
        rare_crystals_collected=_integer(data.get("rare_crystals_collected"), "rare_crystals_collected", minimum=0),
        rare_crystals_total=_integer(data.get("rare_crystals_total"), "rare_crystals_total", minimum=0),
        secret_tokens_collected=_integer(data.get("secret_tokens_collected"), "secret_tokens_collected", minimum=0),
        secret_tokens_total=_integer(data.get("secret_tokens_total"), "secret_tokens_total", minimum=0),
        enemies_defeated=_integer(data.get("enemies_defeated"), "enemies_defeated", minimum=0),
        enemies_total=_integer(data.get("enemies_total"), "enemies_total", minimum=0),
        deaths=_integer(data.get("deaths"), "deaths", minimum=0),
        lives_remaining=_integer(data.get("lives_remaining"), "lives_remaining", minimum=0),
        health_remaining=_integer(data.get("health_remaining"), "health_remaining", minimum=0),
        checkpoints_activated=_integer(data.get("checkpoints_activated"), "checkpoints_activated", minimum=0),
        rating=rating,
        secrets_discovered=_integer(data.get("secrets_discovered"), "secrets_discovered", minimum=0),
        secrets_total=_integer(data.get("secrets_total"), "secrets_total", minimum=0),
        secret_rooms_completed=_integer(data.get("secret_rooms_completed"), "secret_rooms_completed", minimum=0),
        exit_type=exit_type,
        exit_id=exit_id,
    )
    if not result.completed:
        raise SaveValidationError(f"level result {level_id} must represent a completed run")
    for collected_name, total_name in (
        ("ember_shards_collected", "ember_shards_total"),
        ("rare_crystals_collected", "rare_crystals_total"),
        ("secret_tokens_collected", "secret_tokens_total"),
        ("enemies_defeated", "enemies_total"),
        ("secrets_discovered", "secrets_total"),
        ("secret_rooms_completed", "secrets_total"),
    ):
        if getattr(result, collected_name) > getattr(result, total_name):
            raise SaveValidationError(
                f"level result {level_id}.{collected_name} exceeds {total_name}"
            )
    return result


def _mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SaveValidationError(f"{name} must be an object")
    return value


def _number(value: object, name: str, minimum: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < minimum:
        raise SaveValidationError(f"{name} must be a finite number of at least {minimum}")
    return float(value)


def _integer(value: object, name: str, minimum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise SaveValidationError(f"{name} must be an integer of at least {minimum}")
    return value


def _timestamp(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise SaveValidationError(f"{name} must be an ISO-8601 string")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SaveValidationError(f"{name} must be an ISO-8601 string") from exc
    return value


def _unique_known_strings(value: object, known: set[str], name: str) -> set[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SaveValidationError(f"{name} must be a string list")
    if len(value) != len(set(value)):
        raise SaveValidationError(f"{name} contains duplicates")
    unknown = set(value) - known
    if unknown:
        raise SaveValidationError(f"{name} contains unknown IDs: {sorted(unknown)}")
    return set(value)


def _unique_dialogue_flags(value: object, name: str) -> set[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SaveValidationError(f"{name} must be a string list")
    if len(value) != len(set(value)):
        raise SaveValidationError(f"{name} contains duplicates")
    invalid = sorted(item for item in value if not _DIALOGUE_FLAG_RE.fullmatch(item))
    if invalid:
        raise SaveValidationError(f"{name} contains invalid flags: {invalid}")
    return set(value)
