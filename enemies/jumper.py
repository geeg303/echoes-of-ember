"""Ground enemy that periodically leaps toward nearby Nova."""

from __future__ import annotations

from entities.enemy import EnemyUpdateContext, GroundEnemy
from systems.enemy_config import EnemyConfig, EnemyType


class Jumper(GroundEnemy):
    size = (46, 48)

    def __init__(self, enemy_id: str, position: tuple[float, float], config: EnemyConfig) -> None:
        super().__init__(enemy_id, EnemyType.JUMPER, position, config)
        self.cooldown = config.attack_cooldown * 0.5

    def update_ai(self, dt: float, context: EnemyUpdateContext) -> None:
        self.cooldown = max(0.0, self.cooldown - dt)
        horizontal = self.velocity.x if not self.grounded else 0.0
        distance = abs(context.player_rect.centerx - self.rect.centerx)
        if self.grounded and self.cooldown <= 0.0 and distance <= self.config.detection_radius:
            self.facing = 1 if context.player_rect.centerx > self.rect.centerx else -1
            self.velocity.y = -self.config.jump_force
            horizontal = self.facing * self.config.horizontal_speed
            self.cooldown = self.config.attack_cooldown
            self.animation.play("attack", restart=True)
        self.apply_ground_motion(dt, context, horizontal)
        if self.grounded:
            self.velocity.x = 0.0
            if self.animation.current_name != "attack" or self.animation.finished:
                self.animation.play("idle")
        else:
            self.animation.play("move")

