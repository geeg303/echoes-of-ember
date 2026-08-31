"""Shared projectile lifecycle, visual-event output, and viewport rendering."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from entities.projectile import Faction, Projectile
from world.tilemap import TileMap


@dataclass(frozen=True, slots=True)
class ProjectileEffectEvent:
    effect_id: str
    position: pygame.Vector2


class ProjectileManager:
    def __init__(self) -> None:
        self.projectiles: list[Projectile] = []
        self._next_id = 1
        self.effect_events: list[ProjectileEffectEvent] = []

    def spawn(self, projectile: Projectile) -> None:
        self.projectiles.append(projectile)

    def new_id(self, prefix: str) -> str:
        value = f"{prefix}_{self._next_id}"
        self._next_id += 1
        return value

    def update(self, dt: float, tilemap: TileMap) -> None:
        for projectile in self.projectiles:
            was_active = projectile.active
            projectile.update(dt, tilemap)
            if projectile.break_positions:
                self.effect_events.extend(
                    ProjectileEffectEvent("breakable_destroy", pygame.Vector2(position))
                    for position in projectile.break_positions
                )
                projectile.break_positions.clear()
            elif was_active and not projectile.active and projectile.lifetime > 0:
                effect_id = (
                    "ember_pulse_impact"
                    if projectile.faction is Faction.PLAYER
                    else "warden_bolt_impact"
                )
                self.effect_events.append(
                    ProjectileEffectEvent(effect_id, pygame.Vector2(projectile.rect.center))
                )
        self.projectiles = [projectile for projectile in self.projectiles if projectile.active]

    def consume_effect_events(self) -> tuple[ProjectileEffectEvent, ...]:
        events = tuple(self.effect_events)
        self.effect_events.clear()
        return events

    def draw(
        self,
        surface: pygame.Surface,
        view: pygame.Rect,
        offset: tuple[int, int],
    ) -> None:
        padded = view.inflate(128, 128)
        for projectile in self.projectiles:
            if projectile.active and padded.colliderect(projectile.rect):
                projectile.draw(surface, offset)

    def clear(self) -> None:
        self.projectiles.clear()
        self.effect_events.clear()
