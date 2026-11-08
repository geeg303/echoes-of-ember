"""Visual/audio themes: levels and world maps choose presentation by theme name, not by level ID."""

from __future__ import annotations

import json
from pathlib import Path

import pygame
import pytest

from settings import PROJECT_ROOT
from world.background import ParallaxBackground
from world.themes import LEVEL_THEMES, MAP_THEMES, level_theme, map_theme

# Exact music/ambience pairs the old hardcoded _configure_level_audio produced for World 1.
WORLD_1_AUDIO = {
    "verdant_01": ("music_verdant", "ambience_verdant"),
    "verdant_02": ("music_verdant", "ambience_canopy"),
    "verdant_03": ("music_ravine", "ambience_ravine"),
    "verdant_04": ("music_ruins", "ambience_ruins"),
    "verdant_boss": ("music_ruins", "ambience_sanctum"),
}


def _level(level_id: str) -> dict:
    return json.loads((PROJECT_ROOT / "data" / "levels" / f"{level_id}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize(("level_id", "expected"), sorted(WORLD_1_AUDIO.items()))
def test_world_1_themes_keep_their_original_music_and_ambience(level_id: str, expected: tuple[str, str]) -> None:
    style = level_theme(_level(level_id)["theme"])
    assert (style.music, style.ambience) == expected


def test_every_authored_level_uses_a_known_theme() -> None:
    for path in (PROJECT_ROOT / "data" / "levels").glob("*.json"):
        theme = json.loads(path.read_text(encoding="utf-8"))["theme"]
        assert theme in LEVEL_THEMES, f"{path.name} uses unknown theme {theme!r}"


def test_unknown_theme_is_a_clear_error() -> None:
    with pytest.raises(KeyError, match="unknown level theme"):
        level_theme("not_a_theme")


def test_level_validator_rejects_unknown_theme(tmp_path: Path) -> None:
    from tools.validation import LevelValidationError, load_and_validate_level

    data = _level("verdant_01")
    data["theme"] = "not_a_theme"
    path = tmp_path / "verdant_01.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LevelValidationError, match="theme"):
        load_and_validate_level(path)


def test_theme_audio_ids_exist_in_the_audio_catalog() -> None:
    catalog = json.loads((PROJECT_ROOT / "data" / "audio" / "audio.json").read_text(encoding="utf-8"))
    music = {item["id"] for item in catalog["music"]}
    sounds = {item["id"] for item in catalog["sounds"]}
    for name, style in LEVEL_THEMES.items():
        assert style.music in music, name
        assert style.ambience in sounds, name
    for name, style in MAP_THEMES.items():
        assert style.ambience in sounds, name


def test_future_worlds_have_distinct_level_and_map_themes() -> None:
    names = ("glassreach", "hollow_deep", "crown_of_cinders")
    skies = {LEVEL_THEMES[name].background.sky_top for name in ("verdant_day", *names)}
    assert len(skies) == 4
    maps = {MAP_THEMES[name].land for name in ("verdant", *names)}
    assert len(maps) == 4


def test_sanctum_has_its_own_sky_instead_of_the_forest() -> None:
    assert LEVEL_THEMES["first_flame_sanctum"].background != LEVEL_THEMES["verdant_day"].background


def test_background_draws_its_palette_sky(pygame_headless) -> None:
    palette = LEVEL_THEMES["first_flame_sanctum"].background
    surface = pygame.Surface((1280, 720))
    ParallaxBackground(2000, 1000, palette=palette).draw(surface, pygame.Vector2())
    assert surface.get_at((640, 0))[:3] == palette.sky_top


def test_default_background_is_unchanged_verdant_twilight(pygame_headless) -> None:
    surface = pygame.Surface((1280, 720))
    ParallaxBackground(2000, 1000).draw(surface, pygame.Vector2())
    assert surface.get_at((640, 0))[:3] == (25, 32, 72)


def test_boss_level_runtime_uses_sanctum_background(game_factory) -> None:
    game = game_factory(level_id="verdant_boss")
    assert game.background.palette == LEVEL_THEMES["first_flame_sanctum"].background


def test_world_registry_carries_its_map_theme() -> None:
    from world.campaign import DEFAULT_WORLD_REGISTRY, WorldRegistry

    registry = WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
    assert registry.map_theme == "verdant"
    assert map_theme(registry.map_theme) is MAP_THEMES["verdant"]
