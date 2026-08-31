"""Minimal lifecycle, culling, pickup, and feedback management for collectibles."""

from __future__ import annotations

import pygame

from entities.collectible import Collectible, HealthRecipient, PickupResult, create_collectible
from systems.progression import CollectibleType, LevelProgress
from world.level import CollectibleSpawn


class CollectibleManager:
    def __init__(self, spawns: tuple[CollectibleSpawn, ...]) -> None:
        self.spawns = spawns
        self.collectibles: list[Collectible] = []
        self.reset()

    def reset(self) -> None:
        self.collectibles = [
            create_collectible(spawn.object_id, spawn.kind, spawn.position) for spawn in self.spawns
        ]

    def update(self, dt: float, camera_view: pygame.Rect) -> None:
        update_view = camera_view.inflate(320, 240)
        for collectible in self.collectibles:
            if collectible.active and update_view.colliderect(collectible.pickup_rect):
                collectible.update(dt)

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

    @property
    def active_count(self) -> int:
        return sum(collectible.active for collectible in self.collectibles)

