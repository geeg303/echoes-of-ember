"""Faction-aware world-space projectile foundation."""

from __future__ import annotations

from enum import Enum
import math

import pygame

from world.collision import BLOCKING_KINDS
from world.tilemap import TileMap


class Faction(str, Enum):
    PLAYER = "player"
    ENEMY = "enemy"
    NEUTRAL = "neutral"


class Projectile:
    def __init__(
        self,
        projectile_id: str,
        position: tuple[float, float],
        velocity: pygame.Vector2,
        damage: int,
        faction: Faction,
        lifetime: float,
        owner_id: str | None = None,
        terrain_collision: bool = True,
        size: tuple[int, int] = (16, 16),
    ) -> None:
        self.projectile_id = projectile_id
        self.position = pygame.Vector2(position)
        self.velocity = pygame.Vector2(velocity)
        self.damage = damage
        self.faction = faction
        self.lifetime = lifetime
        self.owner_id = owner_id
        self.terrain_collision = terrain_collision
        self.active = True
        self.rect = pygame.Rect(0, 0, *size)
        self.rect.center = (round(self.position.x), round(self.position.y))

    def update(self, dt: float, tilemap: TileMap) -> None:
        if not self.active:
            return
        self.lifetime -= dt
        if self.lifetime <= 0.0:
            self.active = False
            return
        distance = self.velocity.length() * dt
        steps = max(1, math.ceil(distance / max(6.0, tilemap.tile_size / 4)))
        for _ in range(steps):
            self.position += self.velocity * (dt / steps)
            self.rect.center = (round(self.position.x), round(self.position.y))
            if self.terrain_collision and any(
                self.rect.colliderect(tile.rect)
                for tile in tilemap.tiles_in_rect(self.rect, BLOCKING_KINDS)
            ):
                self.active = False
                break

    def draw(self, surface: pygame.Surface, offset: tuple[int, int]) -> None:
        rect = self.rect.move(offset)
        color = (255, 102, 86) if self.faction is Faction.ENEMY else (255, 190, 72)
        pygame.draw.circle(surface, (*color, 70), rect.center, 12)
        pygame.draw.circle(surface, color, rect.center, 6)
        pygame.draw.circle(surface, (255, 239, 187), rect.center, 2)

