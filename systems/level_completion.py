"""Reusable level lifecycle, requirements, frozen results, and ratings."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from systems.progression import CollectibleType, LevelProgress


class GameplayPhase(str, Enum):
    PLAYING = "playing"
    GOAL_TRIGGERED = "goal_triggered"
    COMPLETION_SEQUENCE = "completion_sequence"
    LEVEL_COMPLETE = "level_complete"
    WORLD_COMPLETE = "world_complete"


class CompletionRating(str, Enum):
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"


class ExitType(str, Enum):
    NORMAL = "normal_exit"
    SECRET = "secret_exit"


@dataclass(frozen=True, slots=True)
class CompletionRequirements:
    reach_goal: bool = True
    minimum_ember_shards: int = 0

    def evaluate(self, reached_goal: bool, progress: LevelProgress) -> bool:
        return (
            (reached_goal or not self.reach_goal)
            and progress.count(CollectibleType.EMBER_SHARD) >= self.minimum_ember_shards
        )


@dataclass(frozen=True, slots=True)
class RatingThresholds:
    silver_score: int
    gold_score: int
    gold_shard_ratio: float
    gold_time: float


@dataclass(frozen=True, slots=True)
class LevelResult:
    level_id: str
    completed: bool
    completion_time: float
    score: int
    ember_shards_collected: int
    ember_shards_total: int
    rare_crystals_collected: int
    rare_crystals_total: int
    secret_tokens_collected: int
    secret_tokens_total: int
    enemies_defeated: int
    enemies_total: int
    deaths: int
    lives_remaining: int
    health_remaining: int
    checkpoints_activated: int
    rating: CompletionRating
    secrets_discovered: int = 0
    secrets_total: int = 0
    secret_rooms_completed: int = 0
    exit_type: ExitType = ExitType.NORMAL
    exit_id: str = "ember_gate"


def calculate_rating(
    score: int,
    shards_collected: int,
    shards_total: int,
    completion_time: float,
    thresholds: RatingThresholds,
) -> CompletionRating:
    ratio = shards_collected / shards_total if shards_total else 1.0
    if score >= thresholds.gold_score and ratio >= thresholds.gold_shard_ratio and completion_time <= thresholds.gold_time:
        return CompletionRating.GOLD
    if score >= thresholds.silver_score:
        return CompletionRating.SILVER
    return CompletionRating.BRONZE


def format_time(seconds: float) -> str:
    minutes = int(seconds // 60)
    remainder = seconds - minutes * 60
    return f"{minutes:02d}:{remainder:05.2f}"
