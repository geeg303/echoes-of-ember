"""Switches and animated solid doors linked by stable level IDs."""

from __future__ import annotations

import pygame


class Switch:
    def __init__(self, object_id: str, position: tuple[float, float], target_ids: tuple[str, ...]) -> None:
        self.object_id = object_id
        self.target_ids = target_ids
        self.active = False
        self.rect = pygame.Rect(round(position[0]), round(position[1]), 42, 50)

    def can_interact(self, player_rect: pygame.Rect) -> bool:
        return self.rect.inflate(50, 35).colliderect(player_rect)

    def activate(self) -> bool:
        if self.active:
            return False
        self.active = True
        return True

    def draw(self, surface: pygame.Surface, offset: tuple[int, int]) -> None:
        rect = self.rect.move(offset)
        pygame.draw.rect(surface, (62, 66, 92), rect, border_radius=8)
        pygame.draw.circle(surface, (105, 244, 174) if self.active else (245, 153, 78), rect.center, 11)


class Door:
    def __init__(self, object_id: str, position: tuple[float, float], size: tuple[int, int], opening_duration: float) -> None:
        self.object_id = object_id
        self.base_rect = pygame.Rect(round(position[0]), round(position[1]), *size)
        self.rect = self.base_rect.copy()
        self.opening_duration = opening_duration
        self.open_amount = 0.0
        self.opening = False

    @property
    def solid(self) -> bool:
        return self.open_amount < 1.0

    def open(self) -> None:
        self.opening = True

    def update(self, dt: float) -> None:
        if self.opening:
            self.open_amount = min(1.0, self.open_amount + dt / self.opening_duration)
        height = round(self.base_rect.height * (1.0 - self.open_amount))
        self.rect = pygame.Rect(self.base_rect.x, self.base_rect.bottom - height, self.base_rect.width, height)

    def draw(self, surface: pygame.Surface, offset: tuple[int, int]) -> None:
        if not self.solid:
            return
        rect = self.rect.move(offset)
        pygame.draw.rect(surface, (77, 67, 105), rect)
        pygame.draw.rect(surface, (195, 161, 226), rect, 4)
        for y in range(rect.y + 12, rect.bottom, 24):
            pygame.draw.line(surface, (119, 101, 151), (rect.left + 5, y), (rect.right - 5, y), 3)
