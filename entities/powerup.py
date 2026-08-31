"""Procedural world pickups for player power-ups."""

from __future__ import annotations

import math
import pygame

from systems.powerup_system import POWERUP_DEFINITIONS, PowerUpSystem, PowerUpType


class PowerUpPickup:
    def __init__(self, object_id: str, kind: PowerUpType, position: tuple[float, float], duration: float | None = None) -> None:
        self.object_id = object_id
        self.kind = kind
        self.position = pygame.Vector2(position)
        self.duration = duration
        self.active = True
        self.age = 0.0
        self.pickup_rect = pygame.Rect(round(position[0] - 18), round(position[1] - 18), 36, 36)

    def update(self, dt: float) -> None:
        self.age += dt

    def try_collect(self, player_rect: pygame.Rect, system: PowerUpSystem) -> bool:
        if not self.active or not self.pickup_rect.colliderect(player_rect):
            return False
        self.active = False
        system.activate(self.kind, self.duration)
        return True

    def draw(self, surface: pygame.Surface, offset: tuple[int, int]) -> None:
        definition = POWERUP_DEFINITIONS[self.kind]
        bob = math.sin(self.age * 3.4) * 5
        center = (round(self.position.x + offset[0]), round(self.position.y + offset[1] + bob))
        pygame.draw.circle(surface, tuple(c // 3 for c in definition.color), center, 25)
        pygame.draw.circle(surface, definition.color, center, 18, 4)
        if self.kind is PowerUpType.EMBER_PULSE:
            pygame.draw.circle(surface, (255, 238, 170), center, 8)
        elif self.kind is PowerUpType.WIND_BOOTS:
            pygame.draw.lines(surface, (230, 255, 255), False, [(center[0]-12, center[1]-7), (center[0]+3, center[1]+7), (center[0]+13, center[1]+7)], 5)
        elif self.kind is PowerUpType.AETHER_WING:
            pygame.draw.arc(surface, (245, 225, 255), pygame.Rect(center[0]-15, center[1]-12, 14, 24), 1.2, 5.2, 4)
            pygame.draw.arc(surface, (245, 225, 255), pygame.Rect(center[0]+1, center[1]-12, 14, 24), -2.0, 2.0, 4)
        else:
            pygame.draw.polygon(surface, (226, 235, 241), [(center[0], center[1]-12), (center[0]+11, center[1]-5), (center[0]+8, center[1]+11), (center[0]-8, center[1]+11), (center[0]-11, center[1]-5)], 3)
