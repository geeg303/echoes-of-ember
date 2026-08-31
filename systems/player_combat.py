"""Temporary debug-enabled Ember Pulse ownership and firing policy."""

from __future__ import annotations

import pygame

from entities.player import Player
from entities.projectile import EmberPulseProjectile, Faction
from settings import (
    EMBER_PULSE_COOLDOWN,
    EMBER_PULSE_DAMAGE,
    EMBER_PULSE_LIFETIME,
    EMBER_PULSE_MAX_ACTIVE,
    EMBER_PULSE_SPEED,
)
from systems.projectile_system import ProjectileManager


class PlayerCombatController:
    """Own attack cooldown/count rules without placing combat in Player movement."""

    def __init__(self, ember_pulse_enabled: bool = False) -> None:
        self.ember_pulse_enabled = ember_pulse_enabled
        self.cooldown_timer = 0.0

    def update(self, dt: float) -> None:
        self.cooldown_timer = max(0.0, self.cooldown_timer - dt)

    def try_attack(self, player: Player, projectiles: ProjectileManager) -> bool:
        active_count = sum(
            projectile.active and projectile.faction is Faction.PLAYER
            for projectile in projectiles.projectiles
        )
        if (
            not self.ember_pulse_enabled
            or player.is_dead
            or self.cooldown_timer > 0.0
            or active_count >= EMBER_PULSE_MAX_ACTIVE
        ):
            return False
        direction = 1 if player.facing >= 0 else -1
        origin = (
            player.rect.centerx + direction * (player.rect.width // 2 + 13),
            player.rect.centery - 5,
        )
        projectiles.spawn(
            EmberPulseProjectile(
                projectiles.new_id("ember_pulse"),
                origin,
                pygame.Vector2(direction * EMBER_PULSE_SPEED, 0),
                EMBER_PULSE_DAMAGE,
                Faction.PLAYER,
                EMBER_PULSE_LIFETIME,
                owner_id="player",
                terrain_collision=True,
                size=(18, 14),
            )
        )
        self.cooldown_timer = EMBER_PULSE_COOLDOWN
        player.trigger_attack()
        return True
