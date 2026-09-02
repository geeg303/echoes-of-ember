"""Polished screen-space HUD for health, collectibles, score, and level status."""

from __future__ import annotations

import math
from collections import OrderedDict

import pygame

from entities.collectible import PickupResult
from settings import PLAYER_NAME, PRIMARY_COLLECTIBLE_NAME
from systems.progression import CollectibleType, LevelProgress
from systems.level_completion import format_time


class HUD:
    def __init__(
        self,
        font: pygame.font.Font,
        small_font: pygame.font.Font,
        title_font: pygame.font.Font,
    ) -> None:
        self.font = font
        self.small_font = small_font
        self.title_font = title_font
        self.shard_pulse = 0.0
        self.score_pulse = 0.0
        self.health_flash = 0.0
        self._panel_cache: dict[tuple[tuple[int, int], int], pygame.Surface] = {}
        self._text_cache: OrderedDict[tuple[int, str, tuple[int, int, int]], pygame.Surface] = OrderedDict()
        self._text_cache_limit = 96

    @property
    def text_cache_size(self) -> int:
        return len(self._text_cache)

    def _render_cached(self, font: pygame.font.Font, text: str, color: tuple[int, int, int]) -> pygame.Surface:
        key = (id(font), text, color)
        image = self._text_cache.get(key)
        if image is not None:
            self._text_cache.move_to_end(key)
            return image
        image = font.render(text, True, color)
        self._text_cache[key] = image
        if len(self._text_cache) > self._text_cache_limit:
            self._text_cache.popitem(last=False)
        return image

    def update(self, dt: float) -> None:
        self.shard_pulse = max(0.0, self.shard_pulse - dt)
        self.score_pulse = max(0.0, self.score_pulse - dt)
        self.health_flash = max(0.0, self.health_flash - dt)

    def notify_pickup(self, result: PickupResult) -> None:
        if result.kind is CollectibleType.EMBER_SHARD:
            self.shard_pulse = 0.28
        if result.score_value:
            self.score_pulse = 0.3
        if result.kind is CollectibleType.HEALTH_ITEM:
            self.health_flash = 0.35

    def notify_health_changed(self) -> None:
        self.health_flash = 0.42

    def notify_score_changed(self) -> None:
        self.score_pulse = 0.3

    def reset_feedback(self) -> None:
        self.shard_pulse = 0.0
        self.score_pulse = 0.0
        self.health_flash = 0.0

    def draw(
        self,
        surface: pygame.Surface,
        health: int,
        max_health: int,
        lives: int,
        progress: LevelProgress,
        level_name: str,
        active_power: str = "—",
        power_feedback: float = 0.0,
        power_warning: bool = False,
        elapsed_time: float = 0.0,
    ) -> None:
        self._draw_vitals(surface, health, max_health, lives)
        self._draw_shards(surface, progress)
        self._draw_score_and_level(surface, progress.score, level_name)
        self._draw_powerup_slot(surface, active_power, power_feedback, power_warning)
        timer = self.small_font.render(f"TIME  {format_time(elapsed_time)}", True, (183, 198, 224))
        surface.blit(timer, timer.get_rect(center=(656, 80)))

    def _draw_vitals(
        self,
        surface: pygame.Surface,
        health: int,
        max_health: int,
        lives: int,
    ) -> None:
        panel = pygame.Rect(18, 16, 230, 76)
        self._panel(surface, panel)
        label = self._render_cached(self.small_font, PLAYER_NAME.upper(), (180, 195, 226))
        surface.blit(label, (32, 24))
        flash = self.health_flash > 0.0 and int(self.health_flash * 24) % 2 == 0
        for index in range(max_health):
            center = (42 + index * 34, 62)
            filled = index < health
            color = (255, 238, 170) if flash else ((237, 89, 103) if filled else (74, 75, 103))
            self._heart(surface, center, color)
        lives_label = self._render_cached(self.font, f"× {lives}", (230, 235, 246))
        surface.blit(lives_label, (151, 50))

    def _draw_shards(self, surface: pygame.Surface, progress: LevelProgress) -> None:
        panel = pygame.Rect(266, 16, 270, 76)
        self._panel(surface, panel)
        pygame.draw.polygon(
            surface,
            (255, 151, 61),
            [(290, 32), (304, 54), (290, 76), (276, 54)],
        )
        count = progress.count(CollectibleType.EMBER_SHARD)
        total = progress.total(CollectibleType.EMBER_SHARD)
        text = self._render_cached(self.title_font, f"{count:02d} / {total:02d}", (255, 239, 195))
        scale = 1.0 + 0.12 * math.sin(self.shard_pulse * math.pi / 0.28) if self.shard_pulse else 1.0
        self._blit_scaled(surface, text, (410, 58), scale)
        label = self._render_cached(self.small_font, PRIMARY_COLLECTIBLE_NAME.upper(), (180, 195, 226))
        surface.blit(label, (318, 25))

    def _draw_score_and_level(
        self,
        surface: pygame.Surface,
        score: int,
        level_name: str,
    ) -> None:
        panel = pygame.Rect(surface.get_width() - 380, 16, 362, 76)
        self._panel(surface, panel)
        level_label = self._render_cached(self.small_font, level_name, (177, 198, 221))
        surface.blit(level_label, level_label.get_rect(topright=(panel.right - 14, panel.y + 9)))
        score_label = self._render_cached(self.title_font, f"{score:08d}", (255, 230, 151))
        scale = 1.0 + 0.08 * math.sin(self.score_pulse * math.pi / 0.3) if self.score_pulse else 1.0
        self._blit_scaled(surface, score_label, (panel.right - 105, panel.y + 51), scale)

    def _draw_powerup_slot(self, surface: pygame.Surface, active_power: str, feedback: float, warning: bool) -> None:
        panel = pygame.Rect(542, 16, 228, 48)
        self._panel(surface, panel, alpha=150)
        color = (255, 184, 105) if warning and int(feedback * 20) % 2 == 0 else (194, 211, 242)
        label = self.small_font.render(f"POWER  {active_power}", True, color)
        surface.blit(label, label.get_rect(center=panel.center))
        if feedback > 0.0:
            pygame.draw.rect(surface, (255, 205, 112), panel.inflate(4, 4), 3, border_radius=14)

    def _panel(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        alpha: int = 195,
    ) -> None:
        key = (rect.size, alpha)
        panel = self._panel_cache.get(key)
        if panel is None:
            panel = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(panel, (12, 18, 41, alpha), panel.get_rect(), border_radius=12)
            pygame.draw.rect(panel, (107, 127, 176, 215), panel.get_rect(), 2, border_radius=12)
            if len(self._panel_cache) >= 16:
                self._panel_cache.pop(next(iter(self._panel_cache)))
            self._panel_cache[key] = panel
        surface.blit(panel, rect)

    @staticmethod
    def _heart(surface: pygame.Surface, center: tuple[int, int], color: tuple[int, int, int]) -> None:
        x, y = center
        pygame.draw.circle(surface, color, (x - 6, y - 4), 7)
        pygame.draw.circle(surface, color, (x + 6, y - 4), 7)
        pygame.draw.polygon(surface, color, [(x - 13, y - 1), (x + 13, y - 1), (x, y + 14)])

    @staticmethod
    def _blit_scaled(
        surface: pygame.Surface,
        text: pygame.Surface,
        center: tuple[int, int],
        scale: float,
    ) -> None:
        if abs(scale - 1.0) > 0.001:
            size = (round(text.get_width() * scale), round(text.get_height() * scale))
            text = pygame.transform.smoothscale(text, size)
        surface.blit(text, text.get_rect(center=center))
