"""Procedural enemy frames configured for the shared animation controller."""

from __future__ import annotations

import pygame

from systems.animation import AnimationClip, AnimationController
from systems.enemy_config import EnemyType


ENEMY_COLORS: dict[EnemyType, tuple[int, int, int]] = {
    EnemyType.CRAWLER: (105, 194, 106),
    EnemyType.FLYER: (116, 181, 229),
    EnemyType.JUMPER: (212, 135, 82),
    EnemyType.TURRET: (178, 113, 190),
    EnemyType.ARMORED: (114, 125, 151),
}


def build_enemy_animation(kind: EnemyType) -> AnimationController:
    definitions = (
        ("idle", 2, 3.0, True),
        ("move", 4, 8.0, True),
        ("attack", 3, 9.0, False),
        ("hurt", 2, 10.0, False),
        ("death", 4, 8.0, False),
    )
    clips = [
        AnimationClip.from_surfaces(
            name,
            [_draw_frame(kind, name, frame, count) for frame in range(count)],
            fps,
            loop,
        )
        for name, count, fps, loop in definitions
    ]
    return AnimationController(clips)


def _draw_frame(kind: EnemyType, state: str, index: int, count: int) -> pygame.Surface:
    surface = pygame.Surface((72, 72), pygame.SRCALPHA)
    color = ENEMY_COLORS[kind]
    if state == "hurt":
        color = (255, 235, 188) if index else (238, 92, 111)
    squash = round(index / max(1, count - 1) * 15) if state == "death" else 0
    bob = -2 if state in ("move", "attack") and index % 2 else 0
    body = pygame.Rect(14, 25 + bob + squash, 44, max(16, 32 - squash))
    pygame.draw.ellipse(surface, (*color, 45), body.inflate(16, 14))
    if kind is EnemyType.FLYER:
        pygame.draw.polygon(surface, color, [(13, 36), (2, 21 + index * 3), (27, 33)])
        pygame.draw.polygon(surface, color, [(59, 36), (70, 21 + index * 3), (45, 33)])
        pygame.draw.ellipse(surface, color, body)
    elif kind is EnemyType.TURRET:
        pygame.draw.rect(surface, color, body, border_radius=8)
        pygame.draw.rect(surface, (73, 60, 96), (35, 16, 29 + index * 3, 11), border_radius=5)
    elif kind is EnemyType.ARMORED:
        pygame.draw.ellipse(surface, color, body)
        pygame.draw.arc(surface, (209, 219, 230), body.inflate(-6, -3), 0, 3.2, 5)
        pygame.draw.rect(surface, (67, 73, 93), (17, body.bottom - 8, 38, 10), border_radius=4)
    else:
        pygame.draw.ellipse(surface, color, body)
        if kind is EnemyType.JUMPER:
            pygame.draw.line(surface, color, (25, body.bottom - 4), (17, 65), 7)
            pygame.draw.line(surface, color, (47, body.bottom - 4), (55, 65), 7)
        else:
            leg = 4 if state == "move" and index % 2 else 0
            pygame.draw.line(surface, color, (25, body.bottom - 3), (20 - leg, 63), 6)
            pygame.draw.line(surface, color, (47, body.bottom - 3), (52 + leg, 63), 6)
    eye_color = (255, 236, 133) if state != "death" else (80, 74, 91)
    pygame.draw.circle(surface, eye_color, (47, body.y + 12), 4)
    return surface

