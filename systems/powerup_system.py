"""Single-slot, data-driven player power-up lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pygame

from entities.player import Player, PlayerModifiers
from settings import (
    POWERUP_DURATIONS,
    STONE_GUARD_INVULNERABILITY,
    WIND_BOOTS_ACCELERATION_MULTIPLIER,
    WIND_BOOTS_JUMP_MULTIPLIER,
    WIND_BOOTS_SPEED_MULTIPLIER,
)
from systems.combat import DamageSource


class PowerUpType(str, Enum):
    EMBER_PULSE = "ember_pulse"
    WIND_BOOTS = "wind_boots"
    AETHER_WING = "aether_wing"
    STONE_GUARD = "stone_guard"


@dataclass(frozen=True, slots=True)
class PowerUpDefinition:
    kind: PowerUpType
    display_name: str
    duration: float | None
    color: tuple[int, int, int]


POWERUP_DEFINITIONS = {
    PowerUpType.EMBER_PULSE: PowerUpDefinition(PowerUpType.EMBER_PULSE, "Ember Pulse", POWERUP_DURATIONS["ember_pulse"], (255, 128, 55)),
    PowerUpType.WIND_BOOTS: PowerUpDefinition(PowerUpType.WIND_BOOTS, "Wind Boots", POWERUP_DURATIONS["wind_boots"], (91, 225, 235)),
    PowerUpType.AETHER_WING: PowerUpDefinition(PowerUpType.AETHER_WING, "Aether Wing", POWERUP_DURATIONS["aether_wing"], (198, 150, 255)),
    PowerUpType.STONE_GUARD: PowerUpDefinition(PowerUpType.STONE_GUARD, "Stone Guard", POWERUP_DURATIONS["stone_guard"], (168, 184, 203)),
}
KNOWN_POWERUP_TYPES = frozenset(kind.value for kind in PowerUpType)


@dataclass(slots=True)
class ActivePowerUp:
    definition: PowerUpDefinition
    remaining: float | None
    charge: int = 0


class PowerUpSystem:
    """Owns the one primary slot and exposes capability queries."""

    def __init__(self, player: Player) -> None:
        self.player = player
        self.active: ActivePowerUp | None = None
        self.feedback = 0.0
        self.last_event: str | None = None
        player.damage_absorber = self.absorb_damage

    def activate(self, kind: PowerUpType, duration_override: float | None = None) -> None:
        definition = POWERUP_DEFINITIONS[kind]
        duration = duration_override if duration_override is not None else definition.duration
        charge = 1 if kind is PowerUpType.STONE_GUARD else 0
        self.active = ActivePowerUp(definition, duration, charge)
        self.feedback = 0.45
        self.last_event = "pickup"
        if kind is PowerUpType.AETHER_WING and not self.player.grounded:
            self.player.extra_jump_available = True

    def update(self, dt: float) -> None:
        self.feedback = max(0.0, self.feedback - dt)
        if not self.active or self.active.remaining is None:
            return
        self.active.remaining = max(0.0, self.active.remaining - dt)
        if self.active.remaining <= 0.0:
            self.clear("expired")

    def clear(self, reason: str = "cleared") -> None:
        if self.active:
            self.last_event = reason
            self.feedback = 0.45
        self.active = None

    def consume_event(self) -> str | None:
        event = self.last_event
        self.last_event = None
        return event

    def has(self, kind: PowerUpType) -> bool:
        return bool(self.active and self.active.definition.kind is kind)

    @property
    def grants_ranged_attack(self) -> bool:
        return self.has(PowerUpType.EMBER_PULSE)

    @property
    def movement_modifiers(self) -> PlayerModifiers:
        if self.has(PowerUpType.WIND_BOOTS):
            return PlayerModifiers(
                WIND_BOOTS_SPEED_MULTIPLIER,
                WIND_BOOTS_ACCELERATION_MULTIPLIER,
                WIND_BOOTS_JUMP_MULTIPLIER,
            )
        return PlayerModifiers(double_jump=self.has(PowerUpType.AETHER_WING))

    def absorb_damage(self, source: DamageSource) -> bool:
        if not self.has(PowerUpType.STONE_GUARD) or not self.active or self.active.charge <= 0:
            return False
        self.active.charge = 0
        self.player.invulnerability_timer = STONE_GUARD_INVULNERABILITY
        self.clear("absorbed")
        return True

    @property
    def hud_text(self) -> str:
        if not self.active:
            return "—"
        name = self.active.definition.display_name.upper()
        if self.active.remaining is not None:
            return f"{name} {self.active.remaining:04.1f}s"
        return f"{name} ×{self.active.charge}"

    @property
    def timer_low(self) -> bool:
        return bool(self.active and self.active.remaining is not None and self.active.remaining <= 5.0)


@dataclass(slots=True)
class PowerUpEffect:
    position: pygame.Vector2
    color: tuple[int, int, int]
    age: float = 0.0

    @property
    def active(self) -> bool:
        return self.age < 0.45

    def update(self, dt: float) -> None:
        self.age += dt

    def draw(self, surface: pygame.Surface, offset: tuple[int, int]) -> None:
        center = (round(self.position.x + offset[0]), round(self.position.y + offset[1]))
        radius = round(10 + 32 * min(1.0, self.age / 0.45))
        pygame.draw.circle(surface, self.color, center, radius, 3)


class PowerUpManager:
    """Owns level pickup state separately from the active player slot."""

    def __init__(self, spawns: tuple[object, ...]) -> None:
        from entities.powerup import PowerUpPickup

        self.pickups = [
            PowerUpPickup(spawn.object_id, spawn.kind, spawn.position, spawn.duration)
            for spawn in spawns
        ]
        self.effects: list[PowerUpEffect] = []

    def update(self, dt: float, camera_view: pygame.Rect) -> None:
        padded = camera_view.inflate(320, 240)
        for pickup in self.pickups:
            if pickup.active and padded.colliderect(pickup.pickup_rect):
                pickup.update(dt)
        for effect in self.effects:
            effect.update(dt)
        self.effects = [effect for effect in self.effects if effect.active]

    def collect_overlaps(self, player_rect: pygame.Rect, system: PowerUpSystem) -> tuple[PowerUpType, ...]:
        collected: list[PowerUpType] = []
        for pickup in self.pickups:
            if pickup.try_collect(player_rect, system):
                collected.append(pickup.kind)
                self.effects.append(PowerUpEffect(pygame.Vector2(pickup.pickup_rect.center), POWERUP_DEFINITIONS[pickup.kind].color))
        return tuple(collected)

    def draw(self, surface: pygame.Surface, view: pygame.Rect, offset: tuple[int, int]) -> None:
        padded = view.inflate(192, 160)
        for pickup in self.pickups:
            if pickup.active and padded.colliderect(pickup.pickup_rect):
                pickup.draw(surface, offset)
        for effect in self.effects:
            if padded.collidepoint(effect.position):
                effect.draw(surface, offset)
