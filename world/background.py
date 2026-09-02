"""Original procedural multi-layer scenery for the prototype world."""

from __future__ import annotations

import math
import random

import pygame


class ParallaxBackground:
    """Deterministic twilight scenery that needs no external bitmap assets."""

    def __init__(self, world_width: int, world_height: int, seed: int = 17) -> None:
        self.world_width = world_width
        self.world_height = world_height
        randomizer = random.Random(seed)
        self.stars = [
            (randomizer.randrange(0, world_width), randomizer.randrange(30, 390), randomizer.choice((1, 1, 2)))
            for _ in range(max(45, world_width // 55))
        ]
        self.clouds = [
            (randomizer.randrange(-200, world_width + 200), randomizer.randrange(90, 330), randomizer.randrange(70, 150))
            for _ in range(max(12, world_width // 300))
        ]
        self.tree_positions = [
            (x, randomizer.randrange(75, 145)) for x in range(-100, world_width + 300, 155)
        ]
        self._gradient: pygame.Surface | None = None
        self._gradient_size = (0, 0)

    def draw(self, surface: pygame.Surface, camera_position: pygame.Vector2) -> None:
        self._draw_gradient(surface)
        self._draw_stars(surface, camera_position)
        self._draw_clouds(surface, camera_position)
        self._draw_mountains(surface, camera_position)
        self._draw_cave_silhouettes(surface, camera_position)
        self._draw_trees(surface, camera_position)

    def _draw_gradient(self, surface: pygame.Surface) -> None:
        size = surface.get_size()
        if self._gradient is None or self._gradient_size != size:
            self._gradient_size = size
            self._gradient = pygame.Surface(size)
            height = size[1]
            for y in range(0, height, 4):
                blend = y / max(1, height)
                color = (
                    round(25 + 25 * blend),
                    round(32 + 31 * blend),
                    round(72 + 31 * blend),
                )
                pygame.draw.rect(self._gradient, color, (0, y, size[0], 4))
        surface.blit(self._gradient, (0, 0))

    def _draw_stars(self, surface: pygame.Surface, camera: pygame.Vector2) -> None:
        width = surface.get_width()
        for world_x, world_y, radius in self.stars:
            x = round(world_x - camera.x * 0.04)
            x = ((x + 20) % (width + 40)) - 20
            y = round(world_y - camera.y * 0.025)
            glow = 190 + round(55 * math.sin(world_x * 0.017))
            pygame.draw.circle(surface, (glow, glow, 222), (x, y), radius)

    def _draw_clouds(self, surface: pygame.Surface, camera: pygame.Vector2) -> None:
        width = surface.get_width()
        for world_x, world_y, cloud_width in self.clouds:
            x = round(world_x - camera.x * 0.12)
            x = ((x + 180) % (width + 360)) - 180
            y = round(world_y - camera.y * 0.08)
            color = (92, 102, 149)
            pygame.draw.ellipse(surface, color, (x, y, cloud_width, 34))
            pygame.draw.ellipse(surface, color, (x + cloud_width // 5, y - 18, cloud_width // 2, 48))

    def _draw_mountains(self, surface: pygame.Surface, camera: pygame.Vector2) -> None:
        base_y = round(620 - camera.y * 0.14)
        width = surface.get_width()
        offset = -int(camera.x * 0.2) % 310
        for x in range(offset - 620, width + 620, 310):
            pygame.draw.polygon(
                surface,
                (42, 50, 87),
                [(x - 260, base_y), (x, base_y - 330), (x + 285, base_y)],
            )
            pygame.draw.polygon(
                surface,
                (70, 74, 112),
                [(x - 40, base_y - 280), (x, base_y - 330), (x + 62, base_y - 255)],
            )

    def _draw_cave_silhouettes(self, surface: pygame.Surface, camera: pygame.Vector2) -> None:
        base_y = round(700 - camera.y * 0.22)
        width = surface.get_width()
        offset = -int(camera.x * 0.3) % 430
        for x in range(offset - 500, width + 500, 430):
            pygame.draw.ellipse(surface, (30, 37, 66), (x, base_y - 205, 360, 270))
            pygame.draw.ellipse(surface, (45, 51, 80), (x + 78, base_y - 138, 205, 205))

    def _draw_trees(self, surface: pygame.Surface, camera: pygame.Vector2) -> None:
        base_y = round(704 - camera.y * 0.36)
        width = surface.get_width()
        for world_x, tree_height in self.tree_positions:
            x = round(world_x - camera.x * 0.46)
            x = ((x + 130) % (width + 260)) - 130
            pygame.draw.rect(surface, (41, 57, 65), (x - 8, base_y - tree_height, 16, tree_height))
            pygame.draw.circle(surface, (48, 78, 74), (x, base_y - tree_height), 45)
            pygame.draw.circle(surface, (57, 94, 80), (x - 25, base_y - tree_height + 25), 34)
