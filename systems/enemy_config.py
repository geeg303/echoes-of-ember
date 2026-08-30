"""Central enemy identities, defaults, and data-property schemas."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Any


class EnemyType(str, Enum):
    CRAWLER = "crawler"
    FLYER = "flyer"
    JUMPER = "jumper"
    TURRET = "turret"
    ARMORED = "armored"


@dataclass(frozen=True, slots=True)
class EnemyConfig:
    health: int
    damage: int
    score_reward: int
    speed: float = 0.0
    detection_radius: float = 0.0
    attack_cooldown: float = 0.0
    projectile_speed: float = 0.0
    jump_force: float = 0.0
    horizontal_speed: float = 0.0
    cliff_avoidance: bool = False


ENEMY_CONFIGS: dict[EnemyType, EnemyConfig] = {
    EnemyType.CRAWLER: EnemyConfig(1, 1, 200, speed=82.0, cliff_avoidance=True),
    EnemyType.FLYER: EnemyConfig(1, 1, 300, speed=92.0, detection_radius=360.0),
    EnemyType.JUMPER: EnemyConfig(
        2, 1, 350, detection_radius=480.0, attack_cooldown=1.65,
        jump_force=720.0, horizontal_speed=155.0,
    ),
    EnemyType.TURRET: EnemyConfig(
        2, 1, 500, detection_radius=590.0, attack_cooldown=1.35,
        projectile_speed=350.0,
    ),
    EnemyType.ARMORED: EnemyConfig(4, 1, 750, speed=58.0, cliff_avoidance=True),
}

ENEMY_PROPERTY_TYPES: dict[EnemyType, dict[str, type]] = {
    EnemyType.CRAWLER: {"speed": float, "cliff_avoidance": bool},
    EnemyType.FLYER: {"speed": float, "detection_radius": float},
    EnemyType.JUMPER: {
        "jump_force": float,
        "horizontal_speed": float,
        "attack_cooldown": float,
        "detection_radius": float,
    },
    EnemyType.TURRET: {
        "attack_cooldown": float,
        "detection_radius": float,
        "projectile_speed": float,
    },
    EnemyType.ARMORED: {"speed": float, "cliff_avoidance": bool},
}

COMMON_ENEMY_PROPERTY_TYPES: dict[str, type] = {
    "health": int,
    "damage": int,
    "score_reward": int,
}


def configured_enemy(kind: EnemyType, properties: dict[str, Any]) -> EnemyConfig:
    """Return immutable defaults with validated JSON overrides applied."""
    config = ENEMY_CONFIGS[kind]
    converted: dict[str, Any] = {}
    for key, value in properties.items():
        expected = COMMON_ENEMY_PROPERTY_TYPES.get(key) or ENEMY_PROPERTY_TYPES[kind].get(key)
        if expected is float:
            converted[key] = float(value)
        else:
            converted[key] = value
    return replace(config, **converted)

