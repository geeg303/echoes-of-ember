"""Shared damage results and lightweight combat feedback."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pygame


class DamageSource(str, Enum):
    HAZARD = "hazard"
    ENEMY = "enemy"
    ENEMY_PROJECTILE = "enemy_projectile"
    PLAYER_PROJECTILE = "player_projectile"


@dataclass(frozen=True, slots=True)
class DamageResult:
    applied: bool
    died: bool = False
    amount: int = 0
    absorbed: bool = False


@dataclass(slots=True)
class CombatEffect:
    position: pygame.Vector2
    color: tuple[int, int, int]
    strong: bool = False
    age: float = 0.0
    duration: float = 0.28

    @property
    def active(self) -> bool:
        return self.age < self.duration

    def update(self, dt: float) -> None:
        self.age += dt

    def draw(self, surface: pygame.Surface, offset: tuple[int, int]) -> None:
        life = min(1.0, self.age / self.duration)
        radius = round((25 if self.strong else 15) * life + 4)
        alpha = round(230 * (1.0 - life))
        center = (round(self.position.x + offset[0]), round(self.position.y + offset[1]))
        layer = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(layer, (*self.color, alpha), layer.get_rect().center, radius, 3)
        surface.blit(layer, layer.get_rect(center=center))
