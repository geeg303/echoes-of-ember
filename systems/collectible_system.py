"""Minimal lifecycle, culling, pickup, and feedback management for collectibles."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from entities.collectible import Collectible, HealthRecipient, PickupResult, create_collectible
from systems.progression import CollectibleType, LevelProgress
from world.level import CollectibleSpawn


PICKUP_COLORS: dict[CollectibleType, tuple[int, int, int]] = {
    CollectibleType.EMBER_SHARD: (255, 151, 63),
    CollectibleType.HEALTH_ITEM: (117, 242, 159),
    CollectibleType.RARE_CRYSTAL: (97, 229, 255),
    CollectibleType.SECRET_TOKEN: (255, 218, 83),
}


@dataclass(slots=True)
class PickupEffect:
    position: pygame.Vector2
    color: tuple[int, int, int]
    age: float = 0.0
    duration: float = 0.42

    @property
    def active(self) -> bool:
        return self.age < self.duration

    def update(self, dt: float) -> None:
        self.age += dt

    def draw(self, surface: pygame.Surface, offset: tuple[int, int]) -> None:
        life = min(1.0, self.age / self.duration)
        center = pygame.Vector2(self.position.x + offset[0], self.position.y + offset[1])
        radius = round(8 + 28 * life)
        alpha = round(210 * (1.0 - life))
        layer = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
        layer_center = (layer.get_width() // 2, layer.get_height() // 2)
        pygame.draw.circle(layer, (*self.color, alpha), layer_center, radius, 3)
        for index in range(6):
            angle = index * math.tau / 6
            distance = 9 + 24 * life
            point = (
                round(layer_center[0] + math.cos(angle) * distance),
                round(layer_center[1] + math.sin(angle) * distance),
            )
            pygame.draw.circle(layer, (*self.color, alpha), point, 3)
        surface.blit(layer, layer.get_rect(center=(round(center.x), round(center.y))))


class CollectibleManager:
    def __init__(self, spawns: tuple[CollectibleSpawn, ...]) -> None:
        self.spawns = spawns
        self.collectibles: list[Collectible] = []
        self.effects: list[PickupEffect] = []
        self.reset()

    def reset(self) -> None:
        self.collectibles = [
            create_collectible(spawn.object_id, spawn.kind, spawn.position) for spawn in self.spawns
        ]
        self.effects.clear()

    def update(self, dt: float, camera_view: pygame.Rect) -> None:
        update_view = camera_view.inflate(320, 240)
        for collectible in self.collectibles:
            if collectible.active and update_view.colliderect(collectible.pickup_rect):
                collectible.update(dt)
        for effect in self.effects:
            effect.update(dt)
        self.effects = [effect for effect in self.effects if effect.active]

    def collect_overlaps(
        self,
        player_rect: pygame.Rect,
        recipient: HealthRecipient,
        progress: LevelProgress,
    ) -> tuple[PickupResult, ...]:
        results: list[PickupResult] = []
        for collectible in self.collectibles:
            result = collectible.try_collect(player_rect, recipient, progress)
            if result:
                results.append(result)
                self.effects.append(
                    PickupEffect(pygame.Vector2(result.position), PICKUP_COLORS[result.kind])
                )
        return tuple(results)

    def draw(
        self,
        surface: pygame.Surface,
        camera_view: pygame.Rect,
        offset: tuple[int, int],
    ) -> None:
        draw_view = camera_view.inflate(192, 160)
        for collectible in self.collectibles:
            if collectible.active and draw_view.colliderect(collectible.pickup_rect):
                collectible.draw(surface, offset)
        for effect in self.effects:
            if draw_view.collidepoint(effect.position):
                effect.draw(surface, offset)

    @property
    def active_count(self) -> int:
        return sum(collectible.active for collectible in self.collectibles)

