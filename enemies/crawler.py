"""Cliff-aware ground crawler."""

from __future__ import annotations

from entities.enemy import EnemyUpdateContext, GroundEnemy
from systems.enemy_config import EnemyConfig, EnemyType


class GroundCrawler(GroundEnemy):
    size = (46, 36)

    def __init__(
        self,
        enemy_id: str,
        position: tuple[float, float],
        config: EnemyConfig,
        kind: EnemyType = EnemyType.CRAWLER,
    ) -> None:
        super().__init__(enemy_id, kind, position, config)

    def update_ai(self, dt: float, context: EnemyUpdateContext) -> None:
        if self.grounded and self.config.cliff_avoidance:
            if not self.has_ground_ahead(context.tilemap, self.facing):
                self.facing *= -1
        hit_wall, _ = self.apply_ground_motion(dt, context, self.facing * self.config.speed)
        if hit_wall:
            self.facing *= -1
        self.animation.play("move")
