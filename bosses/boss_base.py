"""Reusable health, state, phase, and vulnerability contract for bosses."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import math
from pathlib import Path

import pygame


class BossConfigError(ValueError):
    """Authored boss configuration cannot be used safely."""


class BossState(str, Enum):
    INTRO = "intro"
    IDLE = "idle"
    MOVE = "move"
    TELEGRAPH = "telegraph"
    ATTACK = "attack"
    RECOVER = "recover"
    STAGGERED = "staggered"
    PHASE_TRANSITION = "phase_transition"
    DEFEATED = "defeated"


@dataclass(frozen=True, slots=True)
class BossPhaseConfig:
    phase: int
    minimum_health: int
    attacks: tuple[str, ...]
    attack_cooldown: float


@dataclass(frozen=True, slots=True)
class BossConfig:
    boss_id: str
    display_name: str
    max_health: int
    size: tuple[int, int]
    movement_speed: float
    contact_damage: int
    hit_invulnerability: float
    stagger_duration: float
    intro_duration: float
    defeat_duration: float
    score_reward: int
    phases: tuple[BossPhaseConfig, ...]
    timings: dict[str, float]
    projectile_speed: float

    def phase_for_health(self, health: int) -> int:
        for phase in self.phases:
            if health >= phase.minimum_health:
                return phase.phase
        return self.phases[-1].phase

    def phase_config(self, phase: int) -> BossPhaseConfig:
        return next(item for item in self.phases if item.phase == phase)


def load_boss_config(path: Path) -> BossConfig:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BossConfigError(f"could not read boss config: {exc}") from exc
    errors = validate_boss_config(raw)
    if errors:
        raise BossConfigError("; ".join(errors))
    phases = tuple(
        BossPhaseConfig(
            int(item["phase"]), int(item["minimum_health"]),
            tuple(str(attack) for attack in item["attacks"]), float(item["attack_cooldown"]),
        )
        for item in raw["phases"]
    )
    return BossConfig(
        str(raw["id"]), str(raw["display_name"]), int(raw["max_health"]),
        (int(raw["size"][0]), int(raw["size"][1])), float(raw["movement_speed"]),
        int(raw["contact_damage"]), float(raw["hit_invulnerability"]),
        float(raw["stagger_duration"]), float(raw["intro_duration"]),
        float(raw["defeat_duration"]), int(raw["score_reward"]), phases,
        {str(key): float(value) for key, value in raw["timings"].items()},
        float(raw["projectile_speed"]),
    )


def validate_boss_config(raw: object) -> list[str]:
    if not isinstance(raw, dict):
        return ["boss config root must be an object"]
    errors: list[str] = []
    for key in ("id", "display_name"):
        if not isinstance(raw.get(key), str) or not raw[key].strip():
            errors.append(f"{key} must be a non-empty string")
    for key in ("max_health", "contact_damage", "score_reward"):
        value = raw.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            errors.append(f"{key} must be a positive integer")
    for key in ("movement_speed", "hit_invulnerability", "stagger_duration", "intro_duration", "defeat_duration", "projectile_speed"):
        value = raw.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
            errors.append(f"{key} must be finite and non-negative")
    size = raw.get("size")
    if not isinstance(size, list) or len(size) != 2 or not all(isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in size):
        errors.append("size must contain two positive integers")
    timings = raw.get("timings")
    if not isinstance(timings, dict) or not timings:
        errors.append("timings must be a non-empty object")
    elif any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v < 0 for v in timings.values()):
        errors.append("timings must contain finite non-negative numbers")
    phases = raw.get("phases")
    if not isinstance(phases, list) or not phases:
        errors.append("phases must be a non-empty list")
        return errors
    parsed: list[tuple[int, int]] = []
    for index, phase in enumerate(phases):
        if not isinstance(phase, dict):
            errors.append(f"phases[{index}] must be an object")
            continue
        number, minimum = phase.get("phase"), phase.get("minimum_health")
        if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
            errors.append(f"phases[{index}].phase must be positive")
        if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum <= 0:
            errors.append(f"phases[{index}].minimum_health must be positive")
        if isinstance(number, int) and isinstance(minimum, int):
            parsed.append((number, minimum))
        attacks = phase.get("attacks")
        if not isinstance(attacks, list) or not attacks or not all(isinstance(v, str) and v for v in attacks) or len(attacks) != len(set(attacks or [])):
            errors.append(f"phases[{index}].attacks must be a unique non-empty string list")
        cooldown = phase.get("attack_cooldown")
        if not isinstance(cooldown, (int, float)) or isinstance(cooldown, bool) or not math.isfinite(cooldown) or cooldown < 0:
            errors.append(f"phases[{index}].attack_cooldown must be non-negative")
    if parsed:
        numbers = [item[0] for item in parsed]
        thresholds = [item[1] for item in parsed]
        if numbers != list(range(1, len(numbers) + 1)):
            errors.append("phase numbers must be consecutive from 1")
        if thresholds != sorted(thresholds, reverse=True) or len(thresholds) != len(set(thresholds)):
            errors.append("phase thresholds must be unique and descending")
        maximum = raw.get("max_health")
        if isinstance(maximum, int) and thresholds and thresholds[0] > maximum:
            errors.append("first phase threshold exceeds max_health")
    return errors


class Boss:
    """Framework-owned lifecycle; subclasses own movement and attack execution."""

    def __init__(self, config: BossConfig, position: tuple[float, float]) -> None:
        self.config = config
        self.boss_id = config.boss_id
        self.display_name = config.display_name
        self.position = pygame.Vector2(position)
        self.rect = pygame.Rect(round(position[0]), round(position[1]), *config.size)
        self.previous_rect = self.rect.copy()
        self.max_health = config.max_health
        self.health = self.max_health
        self.phase = 1
        self.state = BossState.INTRO
        self.state_timer = config.intro_duration
        self.invulnerability_timer = 0.0
        self.vulnerable = False
        self.active = False
        self.defeat_claimed = False
        self.score_claimed = False

    @property
    def alive(self) -> bool:
        return self.state is not BossState.DEFEATED

    @property
    def defeated(self) -> bool:
        return self.state is BossState.DEFEATED and self.state_timer <= 0.0

    def begin(self) -> None:
        self.active = True
        self.state = BossState.INTRO
        self.state_timer = self.config.intro_duration
        self.vulnerable = False

    def set_state(self, state: BossState, duration: float = 0.0, vulnerable: bool = False) -> None:
        if self.state is BossState.DEFEATED:
            return
        self.state = state
        self.state_timer = max(0.0, duration)
        self.vulnerable = vulnerable

    def update_lifecycle(self, dt: float) -> None:
        dt = max(0.0, dt)
        self.invulnerability_timer = max(0.0, self.invulnerability_timer - dt)
        self.state_timer = max(0.0, self.state_timer - dt)

    def take_damage(self, amount: int) -> bool:
        if amount <= 0 or not self.active or not self.alive or not self.vulnerable or self.invulnerability_timer > 0.0:
            return False
        old_phase = self.phase
        self.health = max(0, self.health - amount)
        self.invulnerability_timer = self.config.hit_invulnerability
        if self.health == 0:
            self._begin_defeat()
            return True
        self.phase = self.config.phase_for_health(self.health)
        if self.phase != old_phase:
            self.set_state(BossState.PHASE_TRANSITION, self.config.timings["phase_transition"], False)
        return True

    def _begin_defeat(self) -> None:
        if self.defeat_claimed:
            return
        self.defeat_claimed = True
        self.state = BossState.DEFEATED
        self.state_timer = self.config.defeat_duration
        self.vulnerable = False

    def claim_score(self) -> int:
        if not self.defeat_claimed or self.score_claimed:
            return 0
        self.score_claimed = True
        return self.config.score_reward

    def reset(self, position: tuple[float, float] | None = None) -> None:
        if position is not None:
            self.position.update(position)
        self.rect.topleft = (round(self.position.x), round(self.position.y))
        self.previous_rect = self.rect.copy()
        self.health = self.max_health
        self.phase = 1
        self.state = BossState.INTRO
        self.state_timer = self.config.intro_duration
        self.invulnerability_timer = 0.0
        self.vulnerable = False
        self.active = False
        self.defeat_claimed = False
        self.score_claimed = False
