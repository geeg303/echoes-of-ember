"""Sub-stepped axis-separated collision resolution for tile maps."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from settings import BOUNCE_PAD_SPEED
from world.tile import TileKind
from world.tilemap import TileInstance, TileMap

BLOCKING_KINDS = {TileKind.SOLID, TileKind.BREAKABLE, TileKind.BOUNCE, TileKind.SLIPPERY}


@dataclass(slots=True)
class CollisionResult:
    grounded: bool = False
    hit_wall: bool = False
    hit_ceiling: bool = False
    hit_hazard: bool = False
    bounced: bool = False
    on_slippery: bool = False


class CollisionEngine:
    """Move bodies safely through a tile map without tying physics to visuals."""

    def __init__(self, tilemap: TileMap) -> None:
        self.tilemap = tilemap

    def move(
        self,
        position: pygame.Vector2,
        velocity: pygame.Vector2,
        rect: pygame.Rect,
        dt: float,
    ) -> CollisionResult:
        result = CollisionResult()
        self._depenetrate(position, rect)
        maximum_step = max(4.0, self.tilemap.tile_size / 3.0)
        distance = max(abs(velocity.x * dt), abs(velocity.y * dt))
        steps = max(1, math.ceil(distance / maximum_step))
        step_dt = dt / steps

        for _ in range(steps):
            self._move_horizontal(position, velocity, rect, step_dt, result)
            self._move_vertical(position, velocity, rect, step_dt, result)
            if any(True for _tile in self.tilemap.tiles_in_rect(rect, {TileKind.HAZARD})):
                result.hit_hazard = True
        if not result.grounded and not result.bounced and velocity.y >= 0.0:
            self._detect_support(position, velocity, rect, result)
        if result.bounced:
            result.grounded = False
        return result

    def _detect_support(
        self,
        position: pygame.Vector2,
        velocity: pygame.Vector2,
        rect: pygame.Rect,
        result: CollisionResult,
    ) -> None:
        """Preserve grounded state when sub-pixel motion rounds to exact contact."""
        probe = rect.move(0, 1)
        supported = [
            tile for tile in self.tilemap.tiles_in_rect(
                probe, {TileKind.SOLID, TileKind.BREAKABLE, TileKind.SLIPPERY, TileKind.ONE_WAY}
            )
            if probe.colliderect(tile.rect) and rect.bottom <= tile.rect.top
        ]
        if not supported:
            return
        top = min(tile.rect.top for tile in supported)
        landed = [tile for tile in supported if tile.rect.top == top]
        rect.bottom = top
        position.y = float(rect.y)
        velocity.y = 0.0
        result.grounded = True
        result.on_slippery = any(tile.definition.kind is TileKind.SLIPPERY for tile in landed)

    def _move_horizontal(
        self,
        position: pygame.Vector2,
        velocity: pygame.Vector2,
        rect: pygame.Rect,
        dt: float,
        result: CollisionResult,
    ) -> None:
        position.x += velocity.x * dt
        rect.x = round(position.x)
        collisions = [
            tile for tile in self.tilemap.tiles_in_rect(rect, BLOCKING_KINDS) if rect.colliderect(tile.rect)
        ]
        if not collisions:
            return
        if velocity.x > 0.0:
            rect.right = min(tile.rect.left for tile in collisions)
        elif velocity.x < 0.0:
            rect.left = max(tile.rect.right for tile in collisions)
        position.x = float(rect.x)
        velocity.x = 0.0
        result.hit_wall = True

    def _move_vertical(
        self,
        position: pygame.Vector2,
        velocity: pygame.Vector2,
        rect: pygame.Rect,
        dt: float,
        result: CollisionResult,
    ) -> None:
        previous_bottom = rect.bottom
        position.y += velocity.y * dt
        rect.y = round(position.y)
        candidates = list(self.tilemap.tiles_in_rect(rect, BLOCKING_KINDS | {TileKind.ONE_WAY}))
        collisions: list[TileInstance] = []
        for tile in candidates:
            if not rect.colliderect(tile.rect):
                continue
            if tile.definition.kind is TileKind.ONE_WAY:
                if velocity.y < 0.0 or previous_bottom > tile.rect.top + 2:
                    continue
            collisions.append(tile)
        if not collisions:
            return

        if velocity.y > 0.0:
            landing_top = min(tile.rect.top for tile in collisions)
            landed = [tile for tile in collisions if tile.rect.top == landing_top]
            rect.bottom = landing_top
            if any(tile.definition.kind is TileKind.BOUNCE for tile in landed):
                velocity.y = -BOUNCE_PAD_SPEED
                result.bounced = True
            else:
                velocity.y = 0.0
                result.grounded = True
                result.on_slippery = any(
                    tile.definition.kind is TileKind.SLIPPERY for tile in landed
                )
        elif velocity.y < 0.0:
            solid_collisions = [
                tile for tile in collisions if tile.definition.kind is not TileKind.ONE_WAY
            ]
            if not solid_collisions:
                return
            rect.top = max(tile.rect.bottom for tile in solid_collisions)
            velocity.y = 0.0
            result.hit_ceiling = True
        position.y = float(rect.y)

    def _depenetrate(self, position: pygame.Vector2, rect: pygame.Rect) -> None:
        """Eject a body from malformed/spawn overlap instead of trapping it forever."""
        for _ in range(4):
            overlaps = [
                tile for tile in self.tilemap.tiles_in_rect(rect, BLOCKING_KINDS) if rect.colliderect(tile.rect)
            ]
            if not overlaps:
                return
            tile_rect = overlaps[0].rect
            pushes = (
                (abs(rect.right - tile_rect.left), "left", tile_rect.left),
                (abs(tile_rect.right - rect.left), "right", tile_rect.right),
                (abs(rect.bottom - tile_rect.top), "up", tile_rect.top),
                (abs(tile_rect.bottom - rect.top), "down", tile_rect.bottom),
            )
            _, direction, boundary = min(pushes, key=lambda item: item[0])
            if direction == "left":
                rect.right = boundary
            elif direction == "right":
                rect.left = boundary
            elif direction == "up":
                rect.bottom = boundary
            else:
                rect.top = boundary
            position.update(rect.x, rect.y)
