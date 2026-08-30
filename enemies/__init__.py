"""Enemy archetypes and spawn factory."""

from enemies.armored_enemy import ArmoredEnemy
from enemies.crawler import GroundCrawler
from enemies.flyer import FlyingEnemy
from enemies.jumper import Jumper
from enemies.turret import Turret
from entities.enemy import Enemy
from systems.enemy_config import EnemyType, configured_enemy
from world.level import EnemySpawn

ENEMY_CLASSES: dict[EnemyType, type[Enemy]] = {
    EnemyType.CRAWLER: GroundCrawler,
    EnemyType.FLYER: FlyingEnemy,
    EnemyType.JUMPER: Jumper,
    EnemyType.TURRET: Turret,
    EnemyType.ARMORED: ArmoredEnemy,
}


def create_enemy(spawn: EnemySpawn) -> Enemy:
    return ENEMY_CLASSES[spawn.kind](
        spawn.object_id,
        spawn.position,
        configured_enemy(spawn.kind, spawn.properties),
    )


__all__ = ["create_enemy"]

