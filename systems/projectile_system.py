"""Shared projectile lifecycle and viewport rendering."""

from __future__ import annotations

import pygame

from entities.projectile import Projectile
from world.tilemap import TileMap


class ProjectileManager:
    def __init__(self) -> None:
        self.projectiles: list[Projectile] = []
        self._next_id = 1

    def spawn(self, projectile: Projectile) -> None:
        self.projectiles.append(projectile)

    def new_id(self, prefix: str) -> str:
        value = f"{prefix}_{self._next_id}"
        self._next_id += 1
        return value

    def update(self, dt: float, tilemap: TileMap) -> None:
        for projectile in self.projectiles:
            projectile.update(dt, tilemap)
        self.projectiles = [projectile for projectile in self.projectiles if projectile.active]

    def draw(self, surface: pygame.Surface, view: pygame.Rect, offset: tuple[int, int]) -> None:
        padded = view.inflate(128, 128)
        for projectile in self.projectiles:
            if projectile.active and padded.colliderect(projectile.rect):
                projectile.draw(surface, offset)

    def clear(self) -> None:
        self.projectiles.clear()

