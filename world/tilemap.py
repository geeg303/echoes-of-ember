"""Sparse-load, dense-query tile map with collision/render separation."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import math

import pygame

from world.tile import TILE_DEFINITIONS, TileDefinition, TileKind, draw_tile


@dataclass(frozen=True, slots=True)
class TileInstance:
    grid_x: int
    grid_y: int
    definition: TileDefinition
    rect: pygame.Rect


class TileMap:
    CHUNK_COLUMNS = 16
    CHUNK_ROWS = 8

    def __init__(self, width: int, height: int, tile_size: int, grid: list[list[int]]) -> None:
        self.width = width
        self.height = height
        self.tile_size = tile_size
        self.grid = grid
        self.pixel_width = width * tile_size
        self.pixel_height = height * tile_size
        self._chunk_cache: dict[tuple[int, int], pygame.Surface] = {}

    @property
    def cached_chunk_count(self) -> int:
        return len(self._chunk_cache)

    @property
    def maximum_chunk_count(self) -> int:
        return math.ceil(self.width / self.CHUNK_COLUMNS) * math.ceil(self.height / self.CHUNK_ROWS)

    @classmethod
    def from_data(cls, data: dict[str, object]) -> "TileMap":
        width = int(data["width"])
        height = int(data["height"])
        tile_size = int(data["tile_size"])
        grid = [[0 for _ in range(width)] for _ in range(height)]
        for placement in data["tiles"]:  # type: ignore[union-attr]
            tile = dict(placement)
            tile_id = int(tile["id"])
            x, y = (int(value) for value in tile["position"])
            region_width, region_height = (int(value) for value in tile.get("size", [1, 1]))
            for row in range(y, y + region_height):
                for column in range(x, x + region_width):
                    grid[row][column] = tile_id
        return cls(width, height, tile_size, grid)

    def tile_at(self, grid_x: int, grid_y: int) -> TileInstance | None:
        if not (0 <= grid_x < self.width and 0 <= grid_y < self.height):
            return None
        tile_id = self.grid[grid_y][grid_x]
        if tile_id == 0:
            return None
        definition = TILE_DEFINITIONS[tile_id]
        rect = pygame.Rect(
            grid_x * self.tile_size,
            grid_y * self.tile_size,
            self.tile_size,
            self.tile_size,
        )
        return TileInstance(grid_x, grid_y, definition, rect)

    def tiles_in_rect(
        self,
        rect: pygame.Rect,
        kinds: set[TileKind] | None = None,
    ) -> Iterator[TileInstance]:
        left = max(0, math.floor(rect.left / self.tile_size))
        right = min(self.width - 1, math.floor((rect.right - 1) / self.tile_size))
        top = max(0, math.floor(rect.top / self.tile_size))
        bottom = min(self.height - 1, math.floor((rect.bottom - 1) / self.tile_size))
        if right < left or bottom < top:
            return
        for grid_y in range(top, bottom + 1):
            for grid_x in range(left, right + 1):
                tile = self.tile_at(grid_x, grid_y)
                if tile and (kinds is None or tile.definition.kind in kinds):
                    yield tile

    def draw(
        self,
        surface: pygame.Surface,
        viewport: pygame.Rect | None = None,
        offset: tuple[int, int] = (0, 0),
    ) -> None:
        view = viewport or pygame.Rect(0, 0, surface.get_width(), surface.get_height())
        chunk_width = self.CHUNK_COLUMNS * self.tile_size
        chunk_height = self.CHUNK_ROWS * self.tile_size
        left = max(0, view.left // chunk_width)
        right = min(math.ceil(self.width / self.CHUNK_COLUMNS) - 1, max(0, (view.right - 1) // chunk_width))
        top = max(0, view.top // chunk_height)
        bottom = min(math.ceil(self.height / self.CHUNK_ROWS) - 1, max(0, (view.bottom - 1) // chunk_height))
        for chunk_y in range(top, bottom + 1):
            for chunk_x in range(left, right + 1):
                chunk = self._chunk_surface(chunk_x, chunk_y)
                surface.blit(chunk, (chunk_x * chunk_width + offset[0], chunk_y * chunk_height + offset[1]))

    def _chunk_surface(self, chunk_x: int, chunk_y: int) -> pygame.Surface:
        key = (chunk_x, chunk_y)
        cached = self._chunk_cache.get(key)
        if cached is not None:
            return cached
        width = self.CHUNK_COLUMNS * self.tile_size
        height = self.CHUNK_ROWS * self.tile_size
        chunk = pygame.Surface((width, height), pygame.SRCALPHA)
        first_x = chunk_x * self.CHUNK_COLUMNS
        first_y = chunk_y * self.CHUNK_ROWS
        for grid_y in range(first_y, min(self.height, first_y + self.CHUNK_ROWS)):
            for grid_x in range(first_x, min(self.width, first_x + self.CHUNK_COLUMNS)):
                tile = self.tile_at(grid_x, grid_y)
                if tile is None:
                    continue
                local = pygame.Rect((grid_x - first_x) * self.tile_size, (grid_y - first_y) * self.tile_size, self.tile_size, self.tile_size)
                draw_tile(chunk, tile.definition, local, self.tile_size)
        self._chunk_cache[key] = chunk
        return chunk

    def invalidate_tile(self, grid_x: int, grid_y: int) -> None:
        self._chunk_cache.pop((grid_x // self.CHUNK_COLUMNS, grid_y // self.CHUNK_ROWS), None)

    def destroy_breakables(self, rect: pygame.Rect) -> tuple[pygame.Vector2, ...]:
        destroyed: list[pygame.Vector2] = []
        for tile in tuple(self.tiles_in_rect(rect, {TileKind.BREAKABLE})):
            if rect.colliderect(tile.rect):
                self.grid[tile.grid_y][tile.grid_x] = 0
                self.invalidate_tile(tile.grid_x, tile.grid_y)
                destroyed.append(pygame.Vector2(tile.rect.center))
        return tuple(destroyed)
