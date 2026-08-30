"""Enemy activation, interactions, scoring, projectiles, and cleanup."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from enemies import create_enemy
from entities.enemy import Enemy, EnemyUpdateContext
from entities.player import Player
from entities.projectile import Faction
from settings import PLAYER_ENEMY_KNOCKBACK, PLAYER_STOMP_BOUNCE_SPEED
from systems.combat import CombatEffect, DamageSource
from systems.progression import LevelProgress
from systems.projectile_system import ProjectileManager
from world.collision import CollisionEngine
from world.level import EnemySpawn
from world.tilemap import TileMap


@dataclass(slots=True)
class EnemyUpdateResult:
    player_damaged: bool = False
    player_died: bool = False
    score_awarded: int = 0
    shake: float = 0.0


class EnemyManager:
    def __init__(self, spawns: tuple[EnemySpawn, ...], projectiles: ProjectileManager) -> None:
        self.spawns = spawns
        self.projectiles = projectiles
        self.enemies: list[Enemy] = []
        self.effects: list[CombatEffect] = []
        self.reset()

    def reset(self) -> None:
        self.enemies = [create_enemy(spawn) for spawn in self.spawns]
        self.effects.clear()

    def update(
        self,
        dt: float,
        camera_view: pygame.Rect,
        player: Player,
        collision: CollisionEngine,
        tilemap: TileMap,
        progress: LevelProgress,
    ) -> EnemyUpdateResult:
        outcome = EnemyUpdateResult()
        active_view = camera_view.inflate(900, 600)
        context = EnemyUpdateContext(
            player.rect,
            pygame.Vector2(player.rect.center),
            collision,
            tilemap,
            self.projectiles.spawn,
            self.projectiles.new_id,
        )
        for enemy in self.enemies:
            if not enemy.active:
                continue
            if active_view.colliderect(enemy.rect) or not enemy.alive:
                enemy.update(dt, context)
            if enemy.alive and not player.is_dead and enemy.rect.colliderect(player.rect):
                self._resolve_player_contact(enemy, player, progress, outcome)

        self.projectiles.update(dt, tilemap)
        for projectile in self.projectiles.projectiles:
            if (
                projectile.active
                and projectile.faction is Faction.ENEMY
                and not player.is_dead
                and projectile.rect.colliderect(player.rect)
            ):
                direction = 1 if projectile.velocity.x >= 0 else -1
                damage = player.apply_damage(
                    projectile.damage,
                    DamageSource.ENEMY_PROJECTILE,
                    pygame.Vector2(direction * PLAYER_ENEMY_KNOCKBACK[0], PLAYER_ENEMY_KNOCKBACK[1]),
                )
                projectile.active = False
                if damage.applied:
                    outcome.player_damaged = True
                    outcome.player_died = damage.died
                    outcome.shake = max(outcome.shake, 5.0)
        self.projectiles.projectiles = [p for p in self.projectiles.projectiles if p.active]
        for effect in self.effects:
            effect.update(dt)
        self.effects = [effect for effect in self.effects if effect.active]
        self.enemies = [enemy for enemy in self.enemies if enemy.active]
        return outcome

    def _resolve_player_contact(
        self,
        enemy: Enemy,
        player: Player,
        progress: LevelProgress,
        outcome: EnemyUpdateResult,
    ) -> None:
        descending = player.velocity.y > 80.0
        from_above = player.previous_rect.bottom <= enemy.previous_rect.top + 10
        if descending and from_above:
            player.position.y = enemy.rect.top - player.rect.height
            player.sync_rect()
            player.bounce_from_stomp(PLAYER_STOMP_BOUNCE_SPEED)
            if enemy.stompable:
                newly_dead = enemy.take_damage(1)
                if newly_dead:
                    reward = enemy.claim_score()
                    progress.award_score(reward)
                    outcome.score_awarded += reward
                    outcome.shake = max(outcome.shake, 4.0)
                    self.effects.append(CombatEffect(pygame.Vector2(enemy.rect.center), (255, 183, 78), True))
            else:
                enemy.resist_stomp()
                outcome.shake = max(outcome.shake, 3.0)
                self.effects.append(CombatEffect(pygame.Vector2(enemy.rect.center), (190, 211, 229)))
            return
        direction = -1 if player.rect.centerx < enemy.rect.centerx else 1
        damage = player.apply_damage(
            enemy.damage,
            DamageSource.ENEMY,
            pygame.Vector2(direction * PLAYER_ENEMY_KNOCKBACK[0], PLAYER_ENEMY_KNOCKBACK[1]),
        )
        if damage.applied:
            outcome.player_damaged = True
            outcome.player_died = damage.died
            outcome.shake = max(outcome.shake, 5.0)

    def draw(self, surface: pygame.Surface, view: pygame.Rect, offset: tuple[int, int]) -> None:
        padded = view.inflate(192, 160)
        for enemy in self.enemies:
            if enemy.active and padded.colliderect(enemy.rect):
                enemy.draw(surface, offset)
        self.projectiles.draw(surface, view, offset)
        for effect in self.effects:
            if padded.collidepoint(effect.position):
                effect.draw(surface, offset)

