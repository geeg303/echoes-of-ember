"""Named presentation themes for levels and world maps.

Levels pick a theme with their ``theme`` metadata field; world registries pick a map theme with
``map_theme``. A theme bundles music, ambience, and procedural palette colors so new worlds get a
distinct look and sound by data alone. World 1 values reproduce the original hardcoded presentation.
Future-world audio reuses World 1 placeholder tracks until production audio replaces them.
"""

from __future__ import annotations

from dataclasses import dataclass

Color = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class BackgroundPalette:
    sky_top: Color
    sky_bottom: Color
    star_blue: int
    cloud: Color
    mountain: Color
    mountain_highlight: Color
    cave: Color
    cave_highlight: Color
    trunk: Color
    canopy: Color
    canopy_highlight: Color


@dataclass(frozen=True, slots=True)
class LevelTheme:
    music: str
    ambience: str
    background: BackgroundPalette


@dataclass(frozen=True, slots=True)
class MapTheme:
    ambience: str
    frame: Color
    parchment: Color
    land: Color
    tree: Color
    trunk: Color
    river: Color
    river_highlight: Color
    sparkle: Color
    verdant_landmarks: bool = False


VERDANT_TWILIGHT = BackgroundPalette(
    sky_top=(25, 32, 72),
    sky_bottom=(50, 63, 103),
    star_blue=222,
    cloud=(92, 102, 149),
    mountain=(42, 50, 87),
    mountain_highlight=(70, 74, 112),
    cave=(30, 37, 66),
    cave_highlight=(45, 51, 80),
    trunk=(41, 57, 65),
    canopy=(48, 78, 74),
    canopy_highlight=(57, 94, 80),
)

SANCTUM_EMBERS = BackgroundPalette(
    sky_top=(38, 18, 30),
    sky_bottom=(92, 40, 38),
    star_blue=150,
    cloud=(122, 64, 62),
    mountain=(62, 34, 42),
    mountain_highlight=(110, 58, 52),
    cave=(44, 24, 32),
    cave_highlight=(70, 38, 42),
    trunk=(46, 30, 36),
    canopy=(64, 38, 46),
    canopy_highlight=(80, 46, 54),
)

GLASSREACH_PRISM = BackgroundPalette(
    sky_top=(40, 86, 132),
    sky_bottom=(132, 186, 214),
    star_blue=255,
    cloud=(196, 222, 238),
    mountain=(92, 132, 168),
    mountain_highlight=(170, 214, 236),
    cave=(70, 108, 146),
    cave_highlight=(118, 160, 196),
    trunk=(88, 118, 150),
    canopy=(136, 196, 214),
    canopy_highlight=(186, 232, 240),
)

HOLLOW_DEPTHS = BackgroundPalette(
    sky_top=(10, 18, 20),
    sky_bottom=(24, 46, 46),
    star_blue=170,
    cloud=(36, 62, 60),
    mountain=(28, 42, 40),
    mountain_highlight=(48, 70, 64),
    cave=(18, 28, 28),
    cave_highlight=(34, 50, 48),
    trunk=(60, 48, 36),
    canopy=(52, 84, 64),
    canopy_highlight=(74, 112, 80),
)

CINDER_CROWN = BackgroundPalette(
    sky_top=(52, 22, 22),
    sky_bottom=(150, 74, 44),
    star_blue=120,
    cloud=(106, 70, 66),
    mountain=(56, 38, 40),
    mountain_highlight=(132, 72, 48),
    cave=(40, 28, 30),
    cave_highlight=(76, 46, 40),
    trunk=(48, 36, 34),
    canopy=(96, 74, 52),
    canopy_highlight=(150, 102, 58),
)

LEVEL_THEMES: dict[str, LevelTheme] = {
    # World 1 (shipped): audio pairs match the original per-level choices exactly.
    "verdant_day": LevelTheme("music_verdant", "ambience_verdant", VERDANT_TWILIGHT),
    "canopy_day": LevelTheme("music_verdant", "ambience_canopy", VERDANT_TWILIGHT),
    "ember_ravine": LevelTheme("music_ravine", "ambience_ravine", VERDANT_TWILIGHT),
    "first_flame_ruins": LevelTheme("music_ruins", "ambience_ruins", VERDANT_TWILIGHT),
    "first_flame_sanctum": LevelTheme("music_ruins", "ambience_sanctum", SANCTUM_EMBERS),
    # Developer prototype and Worlds 2-4 (placeholder audio until production assets).
    "glassreach_graybox": LevelTheme("music_verdant", "ambience_verdant", GLASSREACH_PRISM),
    "glassreach": LevelTheme("music_verdant", "ambience_canopy", GLASSREACH_PRISM),
    "hollow_deep": LevelTheme("music_ravine", "ambience_ravine", HOLLOW_DEPTHS),
    "crown_of_cinders": LevelTheme("music_ruins", "ambience_sanctum", CINDER_CROWN),
}

MAP_THEMES: dict[str, MapTheme] = {
    "verdant": MapTheme(
        ambience="ambience_verdant",
        frame=(57, 83, 76),
        parchment=(183, 164, 111),
        land=(72, 105, 82),
        tree=(45, 91, 65),
        trunk=(78, 68, 53),
        river=(73, 141, 157),
        river_highlight=(143, 205, 199),
        sparkle=(255, 190, 92),
        verdant_landmarks=True,
    ),
    "glassreach": MapTheme(
        ambience="ambience_canopy",
        frame=(52, 78, 104),
        parchment=(196, 210, 214),
        land=(118, 160, 184),
        tree=(170, 214, 232),
        trunk=(90, 118, 140),
        river=(222, 240, 250),
        river_highlight=(255, 255, 255),
        sparkle=(190, 236, 255),
    ),
    "hollow_deep": MapTheme(
        ambience="ambience_ravine",
        frame=(20, 30, 30),
        parchment=(120, 108, 84),
        land=(38, 58, 54),
        tree=(60, 92, 70),
        trunk=(70, 56, 42),
        river=(40, 96, 110),
        river_highlight=(90, 160, 168),
        sparkle=(255, 170, 90),
    ),
    "crown_of_cinders": MapTheme(
        ambience="ambience_sanctum",
        frame=(60, 30, 28),
        parchment=(176, 138, 104),
        land=(112, 72, 56),
        tree=(140, 96, 64),
        trunk=(70, 46, 40),
        river=(220, 118, 60),
        river_highlight=(255, 196, 120),
        sparkle=(255, 210, 120),
    ),
}


def level_theme(name: str) -> LevelTheme:
    try:
        return LEVEL_THEMES[name]
    except KeyError:
        raise KeyError(f"unknown level theme: {name!r}") from None


def map_theme(name: str) -> MapTheme:
    try:
        return MAP_THEMES[name]
    except KeyError:
        raise KeyError(f"unknown map theme: {name!r}") from None
