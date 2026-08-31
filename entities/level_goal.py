"""Procedural Ember Gate level goal in world coordinates."""

from __future__ import annotations

import math
import pygame


class EmberGate:
    def __init__(self, position: tuple[float, float], requires_interact: bool = True) -> None:
        self.position = pygame.Vector2(position)
        self.rect = pygame.Rect(round(position[0]), round(position[1]), 92, 128)
        self.requires_interact = requires_interact
        self.nearby = False
        self.activated = False
        self.age = 0.0

    def update(self, dt: float, player_rect: pygame.Rect) -> None:
        self.age += dt
        self.nearby = self.rect.inflate(96, 60).colliderect(player_rect)

    def try_activate(self, player_rect: pygame.Rect, interact_pressed: bool) -> bool:
        if self.activated:
            return False
        self.nearby = self.rect.inflate(96, 60).colliderect(player_rect)
        if self.nearby and (interact_pressed or not self.requires_interact):
            self.activated = True
            return True
        return False

    def draw(self, surface: pygame.Surface, offset: tuple[int, int], interact_prompt: str = "E") -> None:
        rect = self.rect.move(offset)
        pulse = (math.sin(self.age * 4.0) + 1.0) * 0.5
        color = (255, 213, 102) if self.activated or self.nearby else (201, 118, 70)
        pygame.draw.arc(surface, color, rect, 0, math.pi, 12)
        pygame.draw.line(surface, color, (rect.left + 5, rect.centery), (rect.left + 5, rect.bottom), 12)
        pygame.draw.line(surface, color, (rect.right - 5, rect.centery), (rect.right - 5, rect.bottom), 12)
        inner = rect.inflate(-30, -28)
        pygame.draw.ellipse(surface, (84, 45, 111), inner)
        pygame.draw.ellipse(surface, (255, 158 + round(55 * pulse), 93), inner, 4)
        if self.nearby and not self.activated:
            font = pygame.font.Font(None, 25)
            label = font.render(f"[{interact_prompt}]  ENTER EMBER GATE", True, (255, 244, 196))
            surface.blit(label, label.get_rect(midbottom=(rect.centerx, rect.top - 8)))
