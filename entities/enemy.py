"""Reusable enemy contract and shared ground movement helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pygame

from entities.entity import Entity
from entities.projectile import Projectile
from settings import ENEMY_GRAVITY, ENEMY_MAX_FALL_SPEED, SHOW_COLLISION_BOXES
from systems.enemy_animation import build_enemy_animation
from systems.enemy_config import EnemyConfig, EnemyType
from world.collision import BLOCKING_KINDS, CollisionEngine
from world.tile import TileKind
from world.tilemap import TileMap


@dataclass(slots=True)
class EnemyUpdateContext:
    player_rect: pygame.Rect
    player_position: pygame.Vector2
    collision: CollisionEngine
    tilemap: TileMap
    spawn_projectile: Callable[[Projectile], None]
    new_projectile_id: Callable[[str], str]


class Enemy(Entity):
    size = (46, 38)
    stompable = True
    affected_by_knockback = True

    def __init__(
        self,
        enemy_id: str,
        kind: EnemyType,
        position: tuple[float, float],
        config: EnemyConfig,
    ) -> None:
        super().__init__(position, self.size)
        self.enemy_id = enemy_id
        self.kind = kind
        self.config = config
        self.max_health = config.health
        self.health = self.max_health
        self.damage = config.damage
        self.score_reward = config.score_reward
        self.alive = True
        self.active = True
        self.facing = -1
        self.grounded = False
        self.animation = build_enemy_animation(kind)
        self.hit_cooldown = 0.0
        self.hurt_timer = 0.0
        self.score_claimed = False
        self.previous_rect = self.rect.copy()

    @property
    def visual_rect(self) -> pygame.Rect:
        frame = self.animation.current_frame
        return frame.get_rect(midbottom=self.rect.midbottom)

    def update(self, dt: float, context: EnemyUpdateContext) -> None:
        self.previous_rect = self.rect.copy()
        self._tick_common(dt)
        if self.alive:
            self.update_ai(dt, context)
        self._update_animation(dt)

    def update_ai(self, dt: float, context: EnemyUpdateContext) -> None:
        self.animation.play("idle")

    def _tick_common(self, dt: float) -> None:
        self.hit_cooldown = max(0.0, self.hit_cooldown - dt)
        self.hurt_timer = max(0.0, self.hurt_timer - dt)

    def _update_animation(self, dt: float) -> None:
        if not self.alive:
            self.animation.play("death")
        elif self.hurt_timer > 0.0:
            self.animation.play("hurt")
        self.animation.flip_x = self.facing < 0
        self.animation.update(dt)
        if not self.alive and self.animation.finished:
            self.active = False

    def take_damage(self, amount: int, knockback: pygame.Vector2 | None = None) -> bool:
        """Return True only when this call newly kills the enemy."""
        if not self.alive or amount <= 0 or self.hit_cooldown > 0.0:
            return False
        self.health = max(0, self.health - amount)
        self.hit_cooldown = 0.1
        if self.health == 0:
            self.die()
            return True
        self.hurt_timer = 0.2
        self.animation.play("hurt", restart=True)
        if knockback and self.affected_by_knockback:
            self.velocity += knockback
        return False

    def die(self) -> None:
        if not self.alive:
            return
        self.alive = False
        self.velocity.update(0.0, 0.0)
        self.animation.play("death", restart=True)

    def claim_score(self) -> int:
        if self.alive or self.score_claimed:
            return 0
        self.score_claimed = True
        return self.score_reward

    def resist_stomp(self) -> None:
        self.hurt_timer = 0.18
        self.animation.play("hurt", restart=True)

    def draw(self, surface: pygame.Surface, offset: tuple[int, int]) -> None:
        if not self.active:
            return
        frame = self.animation.current_frame
        visual = frame.get_rect(midbottom=self.rect.move(offset).midbottom)
        surface.blit(frame, visual)
        if SHOW_COLLISION_BOXES:
            pygame.draw.rect(surface, (255, 103, 145), self.rect.move(offset), 2)


class GroundEnemy(Enemy):
    def apply_ground_motion(
        self,
        dt: float,
        context: EnemyUpdateContext,
        horizontal_velocity: float,
    ) -> tuple[bool, bool]:
        self.velocity.x = horizontal_velocity
        self.velocity.y = min(self.velocity.y + ENEMY_GRAVITY * dt, ENEMY_MAX_FALL_SPEED)
        result = context.collision.move(self.position, self.velocity, self.rect, dt)
        self.grounded = result.grounded
        return result.hit_wall, result.hit_hazard

    def has_ground_ahead(self, tilemap: TileMap, direction: int) -> bool:
        probe_x = self.rect.right + 3 if direction > 0 else self.rect.left - 7
        probe = pygame.Rect(probe_x, self.rect.bottom + 2, 5, 12)
        kinds = BLOCKING_KINDS | {TileKind.ONE_WAY}
        return any(probe.colliderect(tile.rect) for tile in tilemap.tiles_in_rect(probe, kinds))

