"""Level-local safe respawn beacon."""

from __future__ import annotations
import pygame


class Checkpoint:
    def __init__(self, object_id: str, position: tuple[float, float]) -> None:
        self.object_id = object_id
        self.respawn_position = pygame.Vector2(position)
        self.rect = pygame.Rect(round(position[0]), round(position[1]), 48, 68)
        self.active = False

    def draw(self, surface: pygame.Surface, offset: tuple[int, int]) -> None:
        rect = self.rect.move(offset)
        color = (255, 191, 88) if self.active else (94, 121, 151)
        pygame.draw.polygon(surface, color, [(rect.centerx, rect.top), (rect.right, rect.centery), (rect.centerx, rect.bottom), (rect.left, rect.centery)])
        pygame.draw.circle(surface, (255, 240, 179) if self.active else (142, 165, 183), rect.center, 8)
