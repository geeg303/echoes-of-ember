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
DEFAULT_TILE_SIZE = 64
BOUNCE_PAD_SPEED = 980.0

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


@dataclass(frozen=True, slots=True)
class PlayerPhysics:
    """Tunable, pixels-per-second movement values for Nova."""

    max_run_speed: float = 360.0
    ground_acceleration: float = 2_600.0
    air_acceleration: float = 1_650.0
    ground_deceleration: float = 3_200.0
    air_deceleration: float = 700.0
    slippery_deceleration: float = 260.0
    gravity: float = 2_400.0
    held_jump_gravity_scale: float = 0.42
    jump_speed: float = 820.0
    jump_cut_multiplier: float = 0.45
    maximum_fall_speed: float = 1_050.0
    maximum_jump_hold: float = 0.22
    coyote_time: float = 0.12
    jump_buffer_time: float = 0.12


PLAYER_PHYSICS = PlayerPhysics()
