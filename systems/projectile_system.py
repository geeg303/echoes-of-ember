"""Shared projectile lifecycle and viewport rendering."""

from __future__ import annotations

import pygame
from dataclasses import dataclass

from entities.projectile import Projectile
from world.tilemap import TileMap


@dataclass(slots=True)
class BreakEffect:
    position: pygame.Vector2
    age: float = 0.0

    def update(self, dt: float) -> None:
        self.age += dt

    @property
    def active(self) -> bool:
        return self.age < 0.4

    def draw(self, surface: pygame.Surface, offset: tuple[int, int]) -> None:
        center = pygame.Vector2(self.position.x + offset[0], self.position.y + offset[1])
        life = self.age / 0.4
        for index in range(6):
            direction = pygame.Vector2(1, 0).rotate(index * 60)
            point = center + direction * (8 + life * 28)
            pygame.draw.rect(surface, (225, 151, 82), (round(point.x) - 3, round(point.y) - 3, 6, 6))


class ProjectileManager:
    def __init__(self) -> None:
        self.projectiles: list[Projectile] = []
        self._next_id = 1
        self.break_effects: list[BreakEffect] = []

    def spawn(self, projectile: Projectile) -> None:
        self.projectiles.append(projectile)

    def new_id(self, prefix: str) -> str:
        value = f"{prefix}_{self._next_id}"
        self._next_id += 1
        return value

    def update(self, dt: float, tilemap: TileMap) -> None:
        for projectile in self.projectiles:
            projectile.update(dt, tilemap)
            self.break_effects.extend(BreakEffect(position) for position in projectile.break_positions)
            projectile.break_positions.clear()
        self.projectiles = [projectile for projectile in self.projectiles if projectile.active]
        for effect in self.break_effects:
            effect.update(dt)
        self.break_effects = [effect for effect in self.break_effects if effect.active]

    def draw(self, surface: pygame.Surface, view: pygame.Rect, offset: tuple[int, int]) -> None:
        padded = view.inflate(128, 128)
        for projectile in self.projectiles:
            if projectile.active and padded.colliderect(projectile.rect):
                projectile.draw(surface, offset)
        for effect in self.break_effects:
            if padded.collidepoint(effect.position):
                effect.draw(surface, offset)

    def clear(self) -> None:
        self.projectiles.clear()
        self.break_effects.clear()
