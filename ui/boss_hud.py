"""Screen-space, accessible boss health presentation."""

from __future__ import annotations

from dataclasses import dataclass
import pygame


@dataclass(frozen=True, slots=True)
class BossHUDState:
    visible: bool
    name: str = ""
    health: int = 0
    max_health: int = 1
    phase: int = 1


class BossHUD:
    def __init__(self, font: pygame.font.Font, small: pygame.font.Font) -> None:
        self.font = font
        self.small = small

    def draw(self, surface: pygame.Surface, state: BossHUDState) -> None:
        if not state.visible:
            return
        outer = pygame.Rect(330, 24, 620, 58)
        bar = pygame.Rect(350, 53, 580, 16)
        pygame.draw.rect(surface, (13, 16, 30), outer, border_radius=12)
        pygame.draw.rect(surface, (230, 190, 119), outer, 2, border_radius=12)
        ratio = max(0.0, min(1.0, state.health / max(1, state.max_health)))
        pygame.draw.rect(surface, (43, 47, 58), bar, border_radius=6)
        fill = bar.copy(); fill.width = round(bar.width * ratio)
        pygame.draw.rect(surface, (225, 91, 56), fill, border_radius=6)
        pygame.draw.rect(surface, (255, 225, 156), bar, 2, border_radius=6)
        for marker in (1 / 3, 2 / 3):
            x = round(bar.left + bar.width * marker)
            pygame.draw.line(surface, (255, 238, 190), (x, bar.top), (x, bar.bottom), 2)
        title = self.font.render(state.name.upper(), True, (255, 231, 174))
        surface.blit(title, title.get_rect(midtop=(640, 27)))
        phase = self.small.render(f"PHASE {state.phase}", True, (228, 210, 185))
        surface.blit(phase, (bar.right - phase.get_width(), 31))
