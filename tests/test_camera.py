"""Deterministic camera tracking, bounds, look-ahead, and shake tests."""

from __future__ import annotations

import pygame

from world.background import ParallaxBackground
from world.camera import Camera


def test_target_inside_dead_zone_does_not_move_camera() -> None:
    camera = Camera((1280, 720), (5000, 1400))
    camera.position.update(1000.0, 200.0)
    target = pygame.Rect(1500, 480, 44, 62)
    camera.update(target, pygame.Vector2(), 1.0 / 60.0)
    assert camera.position == pygame.Vector2(1000.0, 200.0)


def test_follow_smooths_toward_target_and_stays_in_world_bounds() -> None:
    camera = Camera((1280, 720), (4000, 1152))
    target = pygame.Rect(3850, 1000, 44, 62)
    for _ in range(180):
        camera.update(target, pygame.Vector2(360, 0), 1.0 / 60.0)
    assert 2_500 < camera.position.x <= 2_720
    assert 0 < camera.position.y <= 432
    assert camera.view_rect.right <= 4000
    assert camera.view_rect.bottom <= 1152


def test_velocity_builds_configurable_look_ahead() -> None:
    camera = Camera((1280, 720), (4000, 1152))
    target = pygame.Rect(1800, 700, 44, 62)
    camera.snap_to(target)
    for _ in range(30):
        camera.update(target, pygame.Vector2(360, 0), 1.0 / 60.0)
    assert 100.0 < camera.look_ahead <= camera.settings.look_ahead_distance


def test_shake_offsets_rendering_then_expires() -> None:
    camera = Camera((1280, 720), (4000, 1152))
    camera.shake(10.0, 0.1)
    camera.update(pygame.Rect(640, 360, 44, 62), pygame.Vector2(), 0.02)
    assert camera.shake_offset.length_squared() > 0.0
    for _ in range(10):
        camera.update(pygame.Rect(640, 360, 44, 62), pygame.Vector2(), 0.02)
    assert camera.shake_offset == pygame.Vector2()


def test_procedural_parallax_draws_multiple_colors() -> None:
    surface = pygame.Surface((1280, 720))
    background = ParallaxBackground(4608, 1152)
    background.draw(surface, pygame.Vector2(900, 250))
    sampled = {
        surface.get_at((x, y))[:3]
        for x in range(0, surface.get_width(), 80)
        for y in range(0, surface.get_height(), 80)
    }
    assert len(sampled) >= 8

