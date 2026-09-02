"""Small shared visual vocabulary for player-facing screen-space UI."""
from __future__ import annotations

import pygame

SAFE_MARGIN_X = 40
SAFE_MARGIN_Y = 32
COLOR_PANEL = (16, 23, 43)
COLOR_PANEL_DEEP = (11, 17, 34)
COLOR_BORDER = (229, 158, 77)
COLOR_TITLE = (255, 218, 143)
COLOR_TEXT = (220, 225, 237)
COLOR_MUTED = (172, 188, 214)
COLOR_FOCUS = (255, 190, 82)


def safe_area(surface: pygame.Surface) -> pygame.Rect:
    return pygame.Rect(
        SAFE_MARGIN_X,
        SAFE_MARGIN_Y,
        surface.get_width() - SAFE_MARGIN_X * 2,
        surface.get_height() - SAFE_MARGIN_Y * 2,
    )


def dim_screen(surface: pygame.Surface, alpha: int = 150) -> None:
    shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    shade.fill((5, 8, 18, max(0, min(220, alpha))))
    surface.blit(shade, (0, 0))


def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    fill: tuple[int, int, int] = COLOR_PANEL,
    border: tuple[int, int, int] = COLOR_BORDER,
    radius: int = 20,
    width: int = 3,
) -> None:
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(surface, border, rect, width, border_radius=radius)

