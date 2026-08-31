"""Data definitions and runtime state for optional exploration content."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pygame


class SecretType(str, Enum):
    CACHE = "secret_cache"
    ROOM = "secret_room"
    CHALLENGE = "challenge_room"
    ALTERNATE_ROUTE = "alternate_route"
    EXIT = "secret_exit"


class SecretTrigger(str, Enum):
    ENTER_REGION = "enter_region"
    INTERACT = "interact"
    DEFEAT_ALL = "defeat_all"
    REACH_TARGET = "reach_target"


class SecretState(str, Enum):
    UNDISCOVERED = "undiscovered"
    DISCOVERED = "discovered"
    ENTERED = "entered"
    COMPLETED = "completed"


SECRET_SCORE_VALUES = {
    SecretType.CACHE: 250,
    SecretType.ROOM: 500,
    SecretType.CHALLENGE: 750,
    SecretType.ALTERNATE_ROUTE: 500,
    SecretType.EXIT: 1000,
}


@dataclass(frozen=True, slots=True)
class SecretDefinition:
    secret_id: str
    kind: SecretType
    trigger: SecretTrigger
    bounds: tuple[float, float, float, float]
    enemy_ids: tuple[str, ...] = ()
    reward_score: int | None = None
    clue: str = ""


@dataclass(slots=True)
class SecretArea:
    definition: SecretDefinition
    state: SecretState = SecretState.UNDISCOVERED
    reward_claimed: bool = False

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(*(round(value) for value in self.definition.bounds))

    @property
    def score_value(self) -> int:
        return (self.definition.reward_score if self.definition.reward_score is not None else SECRET_SCORE_VALUES[self.definition.kind])

