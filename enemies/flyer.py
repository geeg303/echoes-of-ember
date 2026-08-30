"""Bounded hovering flyer with fair local pursuit."""

from __future__ import annotations

import math

import pygame

from entities.enemy import Enemy, EnemyUpdateContext
from systems.enemy_config import EnemyConfig, EnemyType


class FlyingEnemy(Enemy):
    size = (48, 38)

    def __init__(self, enemy_id: str, position: tuple[float, float], config: EnemyConfig) -> None:
        super().__init__(enemy_id, EnemyType.FLYER, position, config)
        self.home = pygame.Vector2(position)
        self.elapsed = 0.0

    def update_ai(self, dt: float, context: EnemyUpdateContext) -> None:
        self.elapsed += dt
        player_center = pygame.Vector2(context.player_rect.center)
        distance = player_center.distance_to(self.rect.center)
        hover = self.home + pygame.Vector2(math.sin(self.elapsed * 1.35) * 70, math.sin(self.elapsed * 2.4) * 26)
        target = hover
        if distance <= self.config.detection_radius:
            pursuit = player_center - pygame.Vector2(self.rect.center)
            if pursuit.length_squared() > 0:
                pursuit.scale_to_length(min(95.0, pursuit.length() * 0.28))
            target = hover + pursuit
        delta = target - self.position
        if delta.length_squared() > 1:
            desired = delta.normalize() * min(self.config.speed, delta.length() * 3.0)
            self.velocity += (desired - self.velocity) * min(1.0, dt * 4.0)
            self.position += self.velocity * dt
            self.sync_rect()
            if abs(self.velocity.x) > 2:
                self.facing = 1 if self.velocity.x > 0 else -1
        self.animation.play("move")

