"""Heavy patrol enemy that resists ordinary stomps."""

from __future__ import annotations

from enemies.crawler import GroundCrawler
from systems.enemy_config import EnemyConfig, EnemyType


class ArmoredEnemy(GroundCrawler):
    size = (54, 50)
    stompable = False
    affected_by_knockback = False

    def __init__(self, enemy_id: str, position: tuple[float, float], config: EnemyConfig) -> None:
        super().__init__(enemy_id, position, config, kind=EnemyType.ARMORED)
