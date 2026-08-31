"""Smooth, bounded platform camera with dead-zone, look-ahead, and shake."""

from __future__ import annotations

import math
import random

import pygame

from settings import CAMERA_SETTINGS, CameraSettings


class Camera:
    def __init__(
        self,
        viewport_size: tuple[int, int],
        world_size: tuple[int, int],
        settings: CameraSettings = CAMERA_SETTINGS,
    ) -> None:
        self.viewport_width, self.viewport_height = viewport_size
        self.world_width, self.world_height = world_size
        self.settings = settings
        self.position = pygame.Vector2()
        self.look_ahead = 0.0
        self.shake_offset = pygame.Vector2()
        self._shake_intensity = 0.0
        self._shake_time = 0.0
        self._shake_duration = 0.0
        self._random = random.Random(0xE4B3)
        self.bounds: pygame.Rect | None = None

    def snap_to(self, target: pygame.Rect) -> None:
        self.look_ahead = 0.0
        self.position.update(
            target.centerx - self.viewport_width / 2,
            target.centery - self.viewport_height / 2 + self.settings.vertical_bias,
        )
        self._clamp_position()

    def update(self, target: pygame.Rect, velocity: pygame.Vector2, dt: float) -> None:
        dt = min(max(dt, 0.0), 0.05)
        look_target = 0.0
        if abs(velocity.x) > 20.0:
            look_target = math.copysign(self.settings.look_ahead_distance, velocity.x)
        look_alpha = 1.0 - math.exp(-self.settings.look_ahead_smoothing * dt)
        self.look_ahead += (look_target - self.look_ahead) * look_alpha

        desired = self.position.copy()
        dead_width, dead_height = self.settings.dead_zone_size
        dead_left = self.position.x + (self.viewport_width - dead_width) / 2
        dead_right = dead_left + dead_width
        dead_top = self.position.y + (self.viewport_height - dead_height) / 2
        dead_bottom = dead_top + dead_height
        focus_x = target.centerx + self.look_ahead
        focus_y = target.centery + self.settings.vertical_bias

        if focus_x < dead_left:
            desired.x += focus_x - dead_left
        elif focus_x > dead_right:
            desired.x += focus_x - dead_right
        if focus_y < dead_top:
            desired.y += focus_y - dead_top
        elif focus_y > dead_bottom:
            desired.y += focus_y - dead_bottom

        desired.x = self._clamp_axis(desired.x, self.world_width, self.viewport_width)
        desired.y = self._clamp_axis(desired.y, self.world_height, self.viewport_height)
        smoothing_alpha = 1.0 - math.exp(-self.settings.smoothing * dt)
        self.position += (desired - self.position) * smoothing_alpha
        self._clamp_position()
        self._update_shake(dt)

    def set_bounds(self, bounds: pygame.Rect | None) -> None:
        self.bounds = bounds.copy() if bounds is not None else None
        self._clamp_position()

    def shake(self, intensity: float, duration: float) -> None:
        if intensity <= 0.0 or duration <= 0.0:
            return
        self._shake_intensity = max(self._shake_intensity, intensity)
        self._shake_time = max(self._shake_time, duration)
        self._shake_duration = max(self._shake_duration, duration)

    def _update_shake(self, dt: float) -> None:
        if self._shake_time <= 0.0:
            self.shake_offset.update(0.0, 0.0)
            self._shake_intensity = 0.0
            self._shake_duration = 0.0
            return
        self._shake_time = max(0.0, self._shake_time - dt)
        life = self._shake_time / max(self._shake_duration, 0.001)
        strength = self._shake_intensity * life
        self.shake_offset.update(
            self._random.uniform(-strength, strength),
            self._random.uniform(-strength, strength),
        )
        self._shake_intensity = max(
            0.0, self._shake_intensity - self.settings.shake_decay * dt
        )

    @property
    def render_offset(self) -> tuple[int, int]:
        return (
            round(-self.position.x + self.shake_offset.x),
            round(-self.position.y + self.shake_offset.y),
        )

    @property
    def view_rect(self) -> pygame.Rect:
        return pygame.Rect(
            math.floor(self.position.x),
            math.floor(self.position.y),
            self.viewport_width,
            self.viewport_height,
        )

    def _clamp_position(self) -> None:
        self.position.x = self._clamp_axis(
            self.position.x, self.world_width, self.viewport_width
        )
        self.position.y = self._clamp_axis(
            self.position.y, self.world_height, self.viewport_height
        )
        if self.bounds is not None:
            max_x = max(self.bounds.left, self.bounds.right - self.viewport_width)
            max_y = max(self.bounds.top, self.bounds.bottom - self.viewport_height)
            self.position.x = max(self.bounds.left, min(self.position.x, max_x))
            self.position.y = max(self.bounds.top, min(self.position.y, max_y))

    @staticmethod
    def _clamp_axis(value: float, world_size: int, viewport_size: int) -> float:
        return max(0.0, min(value, max(0.0, world_size - viewport_size)))
