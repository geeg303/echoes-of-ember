"""Small shared base for position-based game objects."""

from __future__ import annotations

import pygame


class Entity:
    def __init__(self, position: tuple[float, float], size: tuple[int, int]) -> None:
        self.position = pygame.Vector2(position)
        self.velocity = pygame.Vector2()
        self.size = size
        self.rect = pygame.Rect(round(position[0]), round(position[1]), *size)

    def sync_rect(self) -> None:
        self.rect.topleft = (round(self.position.x), round(self.position.y))

