"""Tile identities, behavior metadata, and procedural presentation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pygame


class TileKind(str, Enum):
    EMPTY = "empty"
    SOLID = "solid"
    ONE_WAY = "one_way"
    HAZARD = "hazard"
    DECORATIVE = "decorative"
    BREAKABLE = "breakable"
    BOUNCE = "bounce"
    SLIPPERY = "slippery"


@dataclass(frozen=True, slots=True)
class TileDefinition:
    tile_id: int
    kind: TileKind
    name: str
    color: tuple[int, int, int]
    blocks_horizontal: bool = False
    blocks_vertical: bool = False


TILE_DEFINITIONS: dict[int, TileDefinition] = {
    0: TileDefinition(0, TileKind.EMPTY, "Empty", (0, 0, 0)),
    1: TileDefinition(1, TileKind.SOLID, "Verdant stone", (70, 101, 105), True, True),
    2: TileDefinition(2, TileKind.ONE_WAY, "Spirit ledge", (118, 185, 145)),
    3: TileDefinition(3, TileKind.HAZARD, "Thorn bed", (220, 79, 99)),
    4: TileDefinition(4, TileKind.DECORATIVE, "Glow fern", (94, 214, 170)),
    5: TileDefinition(5, TileKind.BREAKABLE, "Cracked amber", (173, 111, 72), True, True),
    6: TileDefinition(6, TileKind.BOUNCE, "Aether bloom", (243, 111, 171), True, True),
    7: TileDefinition(7, TileKind.SLIPPERY, "Glass moss", (104, 203, 220), True, True),
}


def draw_tile(
    surface: pygame.Surface,
    definition: TileDefinition,
    rect: pygame.Rect,
    tile_size: int,
) -> None:
    """Draw readable placeholder tiles without external copyrighted assets."""
    if definition.kind is TileKind.EMPTY:
        return
    if definition.kind is TileKind.DECORATIVE:
        stem_x = rect.centerx
        pygame.draw.line(surface, (53, 122, 105), (stem_x, rect.bottom), (stem_x, rect.y + 20), 5)
        pygame.draw.ellipse(surface, definition.color, (rect.x + 12, rect.y + 14, 26, 15))
        pygame.draw.ellipse(surface, (143, 240, 187), (rect.x + 34, rect.y + 27, 22, 13))
        return
    if definition.kind is TileKind.HAZARD:
        points: list[tuple[int, int]] = [(rect.left, rect.bottom)]
        spike_width = max(8, tile_size // 4)
        for x in range(rect.left, rect.right, spike_width):
            points.extend([(x + spike_width // 2, rect.top + 12), (x + spike_width, rect.bottom)])
        pygame.draw.polygon(surface, definition.color, points)
        pygame.draw.line(surface, (255, 151, 123), rect.bottomleft, rect.bottomright, 4)
        return
    if definition.kind is TileKind.ONE_WAY:
        platform = pygame.Rect(rect.x, rect.y, rect.width, max(12, tile_size // 4))
        pygame.draw.rect(surface, definition.color, platform, border_radius=7)
        pygame.draw.line(surface, (198, 239, 183), platform.topleft, platform.topright, 4)
        return

    pygame.draw.rect(surface, definition.color, rect)
    pygame.draw.rect(surface, tuple(min(255, c + 35) for c in definition.color), rect, 3)
    if definition.kind is TileKind.SOLID:
        pygame.draw.line(surface, (102, 151, 123), rect.topleft, rect.topright, 7)
        pygame.draw.circle(surface, (52, 78, 87), rect.center, max(3, tile_size // 14))
    elif definition.kind is TileKind.BREAKABLE:
        pygame.draw.lines(
            surface,
            (95, 57, 63),
            False,
            [(rect.x + 13, rect.y), rect.center, (rect.x + 25, rect.bottom), (rect.x + 43, rect.y + 43)],
            4,
        )
    elif definition.kind is TileKind.BOUNCE:
        pygame.draw.ellipse(surface, (255, 204, 113), rect.inflate(-12, -30))
        pygame.draw.line(surface, (255, 239, 181), (rect.x + 10, rect.y + 9), (rect.right - 10, rect.y + 9), 5)
    elif definition.kind is TileKind.SLIPPERY:
        pygame.draw.line(surface, (216, 255, 255), (rect.x + 7, rect.y + 10), (rect.right - 7, rect.y + 10), 5)
        pygame.draw.line(surface, (151, 235, 240), (rect.x + 18, rect.y + 27), (rect.right - 10, rect.y + 20), 3)

