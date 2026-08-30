"""Centralized current-level collectible and score tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from settings import COLLECTIBLE_SCORE_VALUES


class CollectibleType(str, Enum):
    EMBER_SHARD = "ember_shard"
    HEALTH_ITEM = "health_item"
    RARE_CRYSTAL = "rare_crystal"
    SECRET_TOKEN = "secret_token"

    @property
    def score_value(self) -> int:
        return COLLECTIBLE_SCORE_VALUES[self.value]


KNOWN_COLLECTIBLE_TYPES = frozenset(kind.value for kind in CollectibleType)


@dataclass(slots=True)
class LevelProgress:
    totals: dict[CollectibleType, int]
    collected: dict[CollectibleType, int] = field(
        default_factory=lambda: {kind: 0 for kind in CollectibleType}
    )
    collected_ids: set[str] = field(default_factory=set)
    score: int = 0

    @classmethod
    def from_types(cls, collectible_types: list[CollectibleType]) -> "LevelProgress":
        totals = {kind: 0 for kind in CollectibleType}
        for kind in collectible_types:
            totals[kind] += 1
        return cls(totals=totals)

    def register(self, collectible_id: str, kind: CollectibleType) -> bool:
        """Record one pickup; return False when an ID was already collected."""
        if collectible_id in self.collected_ids:
            return False
        self.collected_ids.add(collectible_id)
        self.collected[kind] += 1
        self.score += kind.score_value
        return True

    def count(self, kind: CollectibleType) -> int:
        return self.collected[kind]

    def total(self, kind: CollectibleType) -> int:
        return self.totals[kind]

    def award_score(self, amount: int) -> None:
        if amount > 0:
            self.score += amount

