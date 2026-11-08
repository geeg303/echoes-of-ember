# Presentation Themes

Levels and world maps choose music, ambience, and procedural palettes by **theme name**, defined once in `world/themes.py`. No runtime code selects presentation by level or world ID.

## Level themes

A level's `theme` metadata field must name an entry in `LEVEL_THEMES`; the level validator rejects unknown names.

| Theme | Used by | Music / ambience | Background |
|---|---|---|---|
| `verdant_day` | 1-1 | verdant / verdant | Verdant twilight |
| `canopy_day` | 1-2 | verdant / canopy | Verdant twilight |
| `ember_ravine` | 1-3 | ravine / ravine | Verdant twilight |
| `first_flame_ruins` | 1-4 | ruins / ruins | Verdant twilight |
| `first_flame_sanctum` | Sanctum boss | ruins / sanctum | Sanctum embers |
| `glassreach_graybox` | Ember Currents prototype | verdant / verdant | Glassreach prism |
| `glassreach` | World 2 | placeholder | Glassreach prism |
| `hollow_deep` | World 3 | placeholder | Hollow depths |
| `crown_of_cinders` | World 4 | placeholder | Cinder crown |

World 1 audio pairs are identical to the original hardcoded choices. Worlds 2–4 reuse World 1 placeholder tracks until production audio (Milestone L) adds their own catalog entries; at that point only the theme table changes.

## Map themes

A world registry may set `"map_theme"` (default `"verdant"`). Map themes recolor the procedural World Map frame, land, trees, river, and sparkles and choose map ambience. Only `verdant` draws the World 1 landmark silhouettes; later worlds will add their own landmark art with their map layouts.

## Adding a theme

1. Add a `BackgroundPalette` (and `LevelTheme`/`MapTheme`) in `world/themes.py`.
2. Use only music/sound IDs that exist in `data/audio/audio.json`; `tests/test_themes.py` enforces this.
3. Keep hazards, projectiles, and interactables readable: orange/red threats must contrast with the background layers.
