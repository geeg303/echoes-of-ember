"""Central configuration for Echoes of Ember."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
ASSET_ROOT = PROJECT_ROOT / "assets"

GAME_TITLE = "Echoes of Ember"
PLAYER_NAME = "Nova"
PRIMARY_COLLECTIBLE_NAME = "Ember Shards"

INTERNAL_WIDTH = 1280
INTERNAL_HEIGHT = 720
INTERNAL_SIZE = (INTERNAL_WIDTH, INTERNAL_HEIGHT)
WINDOW_SIZE = INTERNAL_SIZE
TARGET_FPS = 60
BACKGROUND_COLOR = (19, 24, 48)

DEBUG_MODE = True
SHOW_COLLISION_BOXES = False
SHOW_FPS = True
GOD_MODE = False


@dataclass(frozen=True, slots=True)
class DisplaySettings:
    internal_size: tuple[int, int] = INTERNAL_SIZE
    window_size: tuple[int, int] = WINDOW_SIZE
    target_fps: int = TARGET_FPS
    fullscreen: bool = False
    resizable: bool = True


DISPLAY = DisplaySettings()

