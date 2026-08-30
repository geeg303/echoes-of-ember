"""Tests for Phase 0's failure-tolerant asset service."""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from core.asset_manager import AssetManager, SilentSound


def test_missing_assets_return_safe_fallbacks(tmp_path) -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))
    assets = AssetManager(tmp_path)

    assert assets.image("missing.png").get_size() == (64, 64)
    assert assets.font("missing.ttf", 18) is not None
    assert isinstance(assets.sound("missing.wav"), SilentSound)

    pygame.quit()


def test_silent_sound_accepts_standard_operations() -> None:
    sound = SilentSound()
    assert sound.play() is None
    sound.set_volume(0.5)
    sound.stop()

