"""Stationary range-limited projectile turret."""

from __future__ import annotations

import pygame

from entities.enemy import Enemy, EnemyUpdateContext
from entities.projectile import Faction, Projectile
from systems.enemy_config import EnemyConfig, EnemyType


class Turret(Enemy):
    size = (50, 56)
    affected_by_knockback = False

    def __init__(self, enemy_id: str, position: tuple[float, float], config: EnemyConfig) -> None:
        super().__init__(enemy_id, EnemyType.TURRET, position, config)
        self.cooldown = config.attack_cooldown * 0.35
        self.attack_visual_timer = 0.0
        self.telegraph_timer = 0.0
        self.telegraph_duration = min(0.24, max(0.12, config.attack_cooldown * 0.2))

    def update_ai(self, dt: float, context: EnemyUpdateContext) -> None:
        self.cooldown = max(0.0, self.cooldown - dt)
        self.attack_visual_timer = max(0.0, self.attack_visual_timer - dt)
        origin = pygame.Vector2(self.rect.center)
        delta = context.player_position - origin
        if delta.length() <= self.config.detection_radius:
            self.facing = 1 if delta.x >= 0 else -1
            if self.cooldown <= 0.0 and self.telegraph_timer <= 0.0:
                self.telegraph_timer = self.telegraph_duration
                self.animation.play("attack", restart=True)
            elif self.telegraph_timer > 0.0:
                self.telegraph_timer = max(0.0, self.telegraph_timer - dt)
            if self.telegraph_timer <= 0.0 and self.cooldown <= 0.0 and delta.length_squared() > 0:
                velocity = delta.normalize() * self.config.projectile_speed
                context.spawn_projectile(
                    Projectile(
                        context.new_projectile_id("enemy_bolt"),
                        (origin.x + self.facing * 28, origin.y - 7),
                        velocity,
                        self.damage,
                        Faction.ENEMY,
                        lifetime=3.0,
                        owner_id=self.enemy_id,
                    )
                )
                self.cooldown = self.config.attack_cooldown
                self.attack_visual_timer = 0.3
                self.animation.play("attack", restart=True)
        else:
            self.telegraph_timer = 0.0
        self.animation.play("attack" if self.attack_visual_timer > 0.0 or self.telegraph_timer > 0.0 else "idle")

    def draw(self, surface: pygame.Surface, offset: tuple[int, int]) -> None:
        super().draw(surface, offset)
        if not self.active or self.telegraph_timer <= 0.0:
            return
        center = self.rect.move(offset).midtop
        progress = 1.0 - self.telegraph_timer / self.telegraph_duration
        radius = 6 + round(progress * 8)
        pygame.draw.circle(surface, (255, 224, 113), (center[0] + self.facing * 25, center[1] + 12), radius, 2)
