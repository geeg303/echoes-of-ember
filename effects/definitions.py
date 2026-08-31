"""Typed procedural effect catalog; no per-frame parsing or texture assets."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum


class ParticlePrimitive(str, Enum):
    CIRCLE = "circle"
    SPARK = "spark"
    RECT = "rect"
    GLOW = "soft_glow"
    DUST = "dust_puff"


class EffectSpace(str, Enum):
    WORLD = "world"
    SCREEN = "screen"


class EffectPriority(IntEnum):
    AMBIENT = 0
    NORMAL = 1
    CRITICAL = 2


@dataclass(frozen=True, slots=True)
class EffectDefinition:
    effect_id: str
    primitive: ParticlePrimitive
    count: int
    lifetime: tuple[float, float]
    speed: tuple[float, float]
    direction: float
    spread: float
    acceleration: tuple[float, float]
    drag: float
    start_size: tuple[float, float]
    end_size: tuple[float, float]
    alpha: tuple[int, int]
    colors: tuple[tuple[int, int, int], ...]
    spawn_radius: float = 0.0
    space: EffectSpace = EffectSpace.WORLD
    priority: EffectPriority = EffectPriority.NORMAL
    max_particles: int = 80
    emission_rate: float = 0.0


def effect(effect_id: str, primitive: ParticlePrimitive, count: int, colors, *, lifetime=(0.3,0.6), speed=(30,140), direction=-90, spread=180, acceleration=(0,180), drag=1.2, size=(3,7), end=(0,2), alpha=(255,0), radius=4, space=EffectSpace.WORLD, priority=EffectPriority.NORMAL, maximum=80, rate=0.0) -> EffectDefinition:
    return EffectDefinition(effect_id, primitive, count, lifetime, speed, direction, spread, acceleration, drag, size, end, alpha, tuple(colors), radius, space, priority, maximum, rate)

EMBER=((255,103,51),(255,174,71),(255,232,153))
DUST=((173,151,119),(121,113,100),(214,194,155))
WIND=((105,225,235),(194,249,243))
AETHER=((191,147,255),(236,218,255))
STONE=((124,127,132),(184,175,154),(255,145,65))
VIOLET=((163,94,235),(230,184,255),(255,211,104))
GREEN=((87,171,91),(156,211,113),(220,226,145))

_EFFECTS=[
 effect("player_jump_dust",ParticlePrimitive.DUST,5,DUST,lifetime=(.2,.42),speed=(25,80),direction=-90,spread=120,acceleration=(0,100),size=(3,6)),
 effect("player_land_dust",ParticlePrimitive.DUST,8,DUST,lifetime=(.28,.55),speed=(40,130),direction=-90,spread=150,acceleration=(0,120),size=(4,8)),
 effect("player_damage",ParticlePrimitive.SPARK,12,EMBER,lifetime=(.2,.45),speed=(90,210),spread=360,acceleration=(0,80),priority=EffectPriority.CRITICAL),
 effect("player_death",ParticlePrimitive.GLOW,20,EMBER,lifetime=(.55,1.1),speed=(60,210),spread=360,acceleration=(0,100),size=(5,11),priority=EffectPriority.CRITICAL),
 effect("ember_pulse_pickup",ParticlePrimitive.SPARK,14,EMBER,direction=-90,spread=240),
 effect("wind_boots_trail",ParticlePrimitive.SPARK,2,WIND,lifetime=(.18,.36),speed=(15,55),direction=180,spread=45,acceleration=(0,0),size=(2,5),rate=12),
 effect("aether_double_jump",ParticlePrimitive.GLOW,14,AETHER,lifetime=(.3,.65),speed=(50,150),spread=360,acceleration=(0,30),size=(4,9),priority=EffectPriority.CRITICAL),
 effect("stone_guard_activate",ParticlePrimitive.RECT,15,STONE,lifetime=(.35,.7),speed=(50,140),spread=360,acceleration=(0,220),size=(4,8)),
 effect("stone_guard_break",ParticlePrimitive.RECT,22,STONE,lifetime=(.4,.85),speed=(80,230),spread=360,acceleration=(0,300),size=(4,9),priority=EffectPriority.CRITICAL),
 effect("ember_pulse_launch",ParticlePrimitive.GLOW,7,EMBER,lifetime=(.15,.32),speed=(20,75),spread=90,acceleration=(0,0),size=(3,8)),
 effect("ember_pulse_trail",ParticlePrimitive.GLOW,1,EMBER,lifetime=(.12,.26),speed=(0,20),spread=360,acceleration=(0,0),size=(2,5),maximum=60,rate=20),
 effect("ember_pulse_impact",ParticlePrimitive.SPARK,10,EMBER,lifetime=(.18,.42),speed=(70,190),spread=360,acceleration=(0,100)),
 effect("enemy_hit",ParticlePrimitive.SPARK,8,EMBER,lifetime=(.18,.38),speed=(70,170),spread=360),
 effect("enemy_defeat",ParticlePrimitive.DUST,15,EMBER,lifetime=(.35,.75),speed=(60,190),spread=360,acceleration=(0,220),size=(4,9)),
 effect("stomp_impact",ParticlePrimitive.DUST,8,DUST,lifetime=(.2,.45),speed=(40,130),direction=90,spread=140),
 effect("armored_stomp_block",ParticlePrimitive.SPARK,11,STONE,lifetime=(.2,.48),speed=(80,190),spread=220,priority=EffectPriority.CRITICAL),
 effect("ember_shard_pickup",ParticlePrimitive.SPARK,5,EMBER,lifetime=(.2,.42),speed=(40,110),spread=360,size=(2,5)),
 effect("rare_crystal_pickup",ParticlePrimitive.GLOW,16,AETHER,lifetime=(.35,.8),speed=(55,170),spread=360,size=(4,10)),
 effect("secret_token_pickup",ParticlePrimitive.SPARK,20,VIOLET,lifetime=(.4,.9),speed=(60,190),spread=360,size=(3,8),priority=EffectPriority.CRITICAL),
 effect("checkpoint_activate",ParticlePrimitive.SPARK,22,EMBER,lifetime=(.45,1.0),speed=(60,180),direction=-90,spread=110,acceleration=(0,-20),priority=EffectPriority.CRITICAL),
 effect("checkpoint_idle",ParticlePrimitive.GLOW,1,EMBER,lifetime=(.5,1.0),speed=(12,35),direction=-90,spread=60,acceleration=(0,-12),size=(2,5),priority=EffectPriority.AMBIENT,maximum=30,rate=3),
 effect("secret_discovered",ParticlePrimitive.GLOW,24,VIOLET,lifetime=(.5,1.1),speed=(60,180),spread=360,size=(4,10),priority=EffectPriority.CRITICAL),
 effect("challenge_complete",ParticlePrimitive.SPARK,18,VIOLET,lifetime=(.35,.8),speed=(50,160),spread=360),
 effect("breakable_destroy",ParticlePrimitive.RECT,18,DUST,lifetime=(.35,.8),speed=(60,210),spread=360,acceleration=(0,350),size=(4,9)),
 effect("switch_activate",ParticlePrimitive.GLOW,10,EMBER,lifetime=(.25,.55),speed=(30,100),spread=360),
 effect("door_open",ParticlePrimitive.DUST,8,DUST,lifetime=(.3,.65),speed=(20,90),direction=-90,spread=160),
 effect("platform_warning",ParticlePrimitive.DUST,2,DUST,lifetime=(.25,.5),speed=(15,55),direction=-90,spread=120,priority=EffectPriority.AMBIENT),
 effect("drifting_leaves",ParticlePrimitive.RECT,1,GREEN,lifetime=(2.5,4.5),speed=(15,45),direction=110,spread=55,acceleration=(0,8),drag=.2,size=(3,6),end=(2,4),priority=EffectPriority.AMBIENT,maximum=70,rate=4),
 effect("pollen_motes",ParticlePrimitive.GLOW,1,((226,220,139),(173,222,154)),lifetime=(2,4),speed=(5,22),direction=-90,spread=180,acceleration=(0,-3),drag=.4,size=(1,3),end=(0,2),priority=EffectPriority.AMBIENT,maximum=60,rate=5),
 effect("ravine_embers",ParticlePrimitive.SPARK,1,EMBER,lifetime=(1.2,2.5),speed=(15,55),direction=-90,spread=60,acceleration=(0,-15),drag=.3,size=(2,4),priority=EffectPriority.AMBIENT,maximum=60,rate=5),
 effect("ruins_dust",ParticlePrimitive.DUST,1,DUST,lifetime=(1.5,3),speed=(6,28),direction=100,spread=100,acceleration=(0,2),drag=.3,size=(2,5),priority=EffectPriority.AMBIENT,maximum=50,rate=3),
 effect("sanctum_motes",ParticlePrimitive.GLOW,1,EMBER,lifetime=(1.2,2.8),speed=(8,35),direction=-90,spread=100,acceleration=(0,-4),size=(2,5),priority=EffectPriority.AMBIENT,maximum=70,rate=4),
 effect("warden_awaken",ParticlePrimitive.RECT,26,STONE,lifetime=(.5,1.2),speed=(50,190),direction=-90,spread=170,acceleration=(0,320),size=(4,10),priority=EffectPriority.CRITICAL),
 effect("warden_ground_slam",ParticlePrimitive.DUST,30,STONE,lifetime=(.45,1),speed=(90,260),direction=-90,spread=170,acceleration=(0,260),size=(5,12),priority=EffectPriority.CRITICAL),
 effect("warden_bolt_launch",ParticlePrimitive.GLOW,12,EMBER,lifetime=(.2,.5),speed=(50,140),spread=360,size=(3,9)),
 effect("warden_bolt_impact",ParticlePrimitive.SPARK,14,EMBER,lifetime=(.25,.55),speed=(90,220),spread=360),
 effect("warden_leap_takeoff",ParticlePrimitive.DUST,14,STONE,lifetime=(.3,.65),speed=(55,160),direction=-90,spread=150),
 effect("warden_leap_impact",ParticlePrimitive.RECT,24,STONE,lifetime=(.45,1),speed=(90,250),spread=250,acceleration=(0,340),size=(4,10),priority=EffectPriority.CRITICAL),
 effect("warden_phase_two",ParticlePrimitive.RECT,32,EMBER,lifetime=(.55,1.25),speed=(80,250),spread=360,acceleration=(0,180),size=(5,11),priority=EffectPriority.CRITICAL),
 effect("warden_phase_three",ParticlePrimitive.SPARK,40,EMBER,lifetime=(.6,1.4),speed=(100,280),spread=360,acceleration=(0,100),size=(4,10),priority=EffectPriority.CRITICAL),
 effect("warden_core_vulnerable",ParticlePrimitive.GLOW,1,EMBER,lifetime=(.25,.5),speed=(10,40),spread=360,acceleration=(0,0),size=(3,7),priority=EffectPriority.CRITICAL,maximum=30,rate=8),
 effect("warden_core_hit",ParticlePrimitive.SPARK,16,EMBER,lifetime=(.25,.6),speed=(100,250),spread=360,priority=EffectPriority.CRITICAL),
 effect("warden_core_burst",ParticlePrimitive.SPARK,28,EMBER,lifetime=(.4,.9),speed=(120,300),spread=360,acceleration=(0,30),priority=EffectPriority.CRITICAL),
 effect("warden_defeat",ParticlePrimitive.RECT,42,EMBER,lifetime=(.7,1.7),speed=(80,280),spread=360,acceleration=(0,260),size=(5,13),priority=EffectPriority.CRITICAL,maximum=140),
 effect("route_unlocked",ParticlePrimitive.SPARK,16,EMBER,lifetime=(.4,.9),speed=(40,130),spread=360,space=EffectSpace.SCREEN),
 effect("ember_veil_reveal",ParticlePrimitive.GLOW,28,VIOLET,lifetime=(.6,1.4),speed=(45,150),spread=360,space=EffectSpace.SCREEN,priority=EffectPriority.CRITICAL),
 effect("sanctum_available",ParticlePrimitive.GLOW,1,EMBER,lifetime=(.7,1.4),speed=(8,30),spread=360,space=EffectSpace.SCREEN,priority=EffectPriority.AMBIENT,maximum=25,rate=2),
 effect("world_complete",ParticlePrimitive.SPARK,36,EMBER,lifetime=(.7,1.5),speed=(70,220),direction=-90,spread=220,space=EffectSpace.SCREEN,priority=EffectPriority.CRITICAL),
]
EFFECT_DEFINITIONS={item.effect_id:item for item in _EFFECTS}
