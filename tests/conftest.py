"""Shared isolated Phase 24 fixtures.

Fixtures create all writable state under pytest's temporary directory. Nothing
in this file points at the user's actual save, settings, or achievement roots.
"""
from __future__ import annotations

import os
import random
from pathlib import Path
from typing import Callable, Iterator

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from core.achievement_manager import AchievementManager
from core.game import Game
from core.save_manager import SaveManager
from core.settings_manager import SettingsManager
from settings import PROJECT_ROOT
from world.campaign import DEFAULT_WORLD_REGISTRY, WorldRegistry


@pytest.fixture
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture
def world_registry() -> WorldRegistry:
    return WorldRegistry.load(DEFAULT_WORLD_REGISTRY)


@pytest.fixture
def isolated_save_manager(tmp_path: Path, world_registry: WorldRegistry) -> SaveManager:
    return SaveManager(world_registry, tmp_path / "saves")


@pytest.fixture
def isolated_settings_manager(tmp_path: Path) -> SettingsManager:
    return SettingsManager(tmp_path / "settings.json")


@pytest.fixture
def isolated_achievement_manager(tmp_path: Path) -> AchievementManager:
    return AchievementManager.create(
        PROJECT_ROOT / "data" / "achievements" / "achievements.json",
        tmp_path / "achievements.json",
    )


@pytest.fixture
def seeded_rng() -> random.Random:
    """A local deterministic generator that never changes global RNG state."""
    return random.Random(0xE0E24)


@pytest.fixture
def pygame_headless() -> Iterator[pygame.Surface]:
    pygame.init()
    surface = pygame.display.set_mode((1280, 720))
    yield surface
    pygame.quit()


@pytest.fixture
def game_factory(
    tmp_path: Path,
    isolated_settings_manager: SettingsManager,
) -> Iterator[Callable[..., Game]]:
    games: list[Game] = []

    def create(**kwargs: object) -> Game:
        kwargs.setdefault("settings_manager", isolated_settings_manager)
        kwargs.setdefault("achievements_enabled", False)
        kwargs.setdefault("persistence", False)
        game = Game(**kwargs)
        games.append(game)
        return game

    yield create
    for game in reversed(games):
        game.shutdown()

