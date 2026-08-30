"""Hand-built Phase 1 movement test room."""

from __future__ import annotations

import pygame

from settings import INTERNAL_HEIGHT, INTERNAL_WIDTH, SHOW_COLLISION_BOXES


class TestRoom:
    """A compact floor, wall, and platform course for tuning movement."""

    __test__ = False

    def __init__(self) -> None:
        self.player_spawn = (92.0, 560.0)
        self.solids = [
            pygame.Rect(0, 650, INTERNAL_WIDTH, 70),
            pygame.Rect(0, 0, 36, INTERNAL_HEIGHT),
            pygame.Rect(INTERNAL_WIDTH - 36, 0, 36, INTERNAL_HEIGHT),
            pygame.Rect(210, 540, 210, 28),
            pygame.Rect(510, 455, 190, 28),
            pygame.Rect(790, 365, 180, 28),
            pygame.Rect(1040, 500, 205, 28),
        ]

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((24, 31, 64))
        pygame.draw.circle(surface, (255, 183, 91), (1080, 115), 68)
        pygame.draw.circle(surface, (255, 219, 139), (1080, 115), 47)

        for index in range(7):
            x = index * 230 - 80
            pygame.draw.polygon(
                surface,
                (36, 47, 82),
                [(x, 650), (x + 150, 290 + (index % 2) * 90), (x + 320, 650)],
            )

        for solid in self.solids:
            pygame.draw.rect(surface, (61, 92, 111), solid, border_radius=4)
            cap = pygame.Rect(solid.x, solid.y, solid.width, min(8, solid.height))
            pygame.draw.rect(surface, (115, 185, 141), cap, border_radius=4)
            if SHOW_COLLISION_BOXES:
                pygame.draw.rect(surface, (255, 105, 175), solid, 2)

