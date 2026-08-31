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

PLAYER_MAX_HEALTH = 3
PLAYER_STARTING_LIVES = 3
COLLECTIBLE_SCORE_VALUES: dict[str, int] = {
    "ember_shard": 100,
    "health_item": 0,
    "rare_crystal": 1_000,
    "secret_token": 2_500,
}
PLAYER_INVULNERABILITY_DURATION = 1.25
PLAYER_STOMP_BOUNCE_SPEED = 650.0
PLAYER_ENEMY_KNOCKBACK = (390.0, -430.0)
ENEMY_GRAVITY = 2_400.0
ENEMY_MAX_FALL_SPEED = 1_050.0
EMBER_PULSE_DAMAGE = 1
EMBER_PULSE_SPEED = 720.0
EMBER_PULSE_LIFETIME = 0.85
EMBER_PULSE_COOLDOWN = 0.35
EMBER_PULSE_MAX_ACTIVE = 4
EMBER_PULSE_KNOCKBACK = 135.0
POWERUP_DURATIONS: dict[str, float | None] = {
    "ember_pulse": 20.0,
    "wind_boots": 18.0,
    "aether_wing": 18.0,
    "stone_guard": None,
}
WIND_BOOTS_SPEED_MULTIPLIER = 1.20
WIND_BOOTS_ACCELERATION_MULTIPLIER = 1.15
WIND_BOOTS_JUMP_MULTIPLIER = 1.05
STONE_GUARD_INVULNERABILITY = 0.55
LEVEL_COMPLETION_SEQUENCE_DURATION = 1.5
EFFECT_PARTICLE_CAP = 600
EFFECT_DEFAULT_QUALITY = "full"


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


@dataclass(frozen=True, slots=True)
class CameraSettings:
    dead_zone_size: tuple[int, int] = (380, 220)
    smoothing: float = 8.5
    look_ahead_distance: float = 170.0
    look_ahead_smoothing: float = 5.0
    vertical_bias: float = 35.0
    shake_decay: float = 9.0


CAMERA_SETTINGS = CameraSettings()


@dataclass(frozen=True, slots=True)
class PlayerAnimationSettings:
    visual_size: tuple[int, int] = (64, 80)
    apex_velocity_threshold: float = 45.0
    landing_speed_threshold: float = 430.0
    hurt_duration: float = 0.36


PLAYER_ANIMATION = PlayerAnimationSettings()
