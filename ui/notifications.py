"""Lightweight queued screen-space toast notifications."""

from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass(slots=True)
class Notification:
    text: str
    remaining: float = 2.2
    duration: float = 2.2


class NotificationQueue:
    def __init__(self, font: pygame.font.Font) -> None:
        self.font = font
        self.items: list[Notification] = []

    def push(self, text: str, duration: float = 2.2) -> None:
        self.items.append(Notification(text, duration, duration))

    def update(self, dt: float) -> None:
        if not self.items:
            return
        self.items[0].remaining -= dt
        if self.items[0].remaining <= 0:
            self.items.pop(0)

    def clear(self) -> None:
        self.items.clear()

    def draw(self, surface: pygame.Surface) -> None:
        if not self.items:
            return
        item = self.items[0]
        fade = min(1.0, item.remaining / 0.3, (item.duration - item.remaining) / 0.2)
        image = self.font.render(item.text, True, (255, 230, 154))
        panel = pygame.Surface((image.get_width() + 54, image.get_height() + 26), pygame.SRCALPHA)
        pygame.draw.rect(panel, (17, 22, 48, round(220 * fade)), panel.get_rect(), border_radius=14)
        pygame.draw.rect(panel, (225, 154, 84, round(255 * fade)), panel.get_rect(), 2, border_radius=14)
        image.set_alpha(round(255 * fade))
        panel.blit(image, image.get_rect(center=panel.get_rect().center))
        surface.blit(panel, panel.get_rect(center=(surface.get_width() // 2, 126)))

