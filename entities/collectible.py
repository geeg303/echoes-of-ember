"""Reusable non-solid collectible entities and original placeholder art."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pygame

from systems.animation import AnimationClip, AnimationController
from systems.progression import CollectibleType, LevelProgress


class HealthRecipient(Protocol):
    health: int
    max_health: int

    def heal(self, amount: int) -> int: ...


@dataclass(frozen=True, slots=True)
class PickupResult:
    collectible_id: str
    kind: CollectibleType
    position: tuple[float, float]
    score_value: int
    sound_path: str


class Collectible:
    """Animated world-space pickup with a camera-independent overlap rectangle."""

    kind = CollectibleType.EMBER_SHARD
    pickup_size = (34, 42)
    sound_path = "sounds/ember_shard.wav"

    def __init__(self, collectible_id: str, position: tuple[float, float]) -> None:
        self.collectible_id = collectible_id
        self.position = pygame.Vector2(position)
        self.active = True
        self.animation = _build_collectible_animation(self.kind)

    @property
    def pickup_rect(self) -> pygame.Rect:
        rect = pygame.Rect(0, 0, *self.pickup_size)
        rect.center = (round(self.position.x), round(self.position.y))
        return rect

    def update(self, dt: float) -> None:
        if self.active:
            self.animation.update(dt)

    def try_collect(
        self,
        player_rect: pygame.Rect,
        recipient: HealthRecipient,
        progress: LevelProgress,
    ) -> PickupResult | None:
        if not self.active or not self.pickup_rect.colliderect(player_rect):
            return None
        if not self._can_collect(recipient):
            return None
        if not progress.register(self.collectible_id, self.kind):
            self.active = False
            return None
        self._apply_pickup(recipient)
        self.active = False
        return PickupResult(
            collectible_id=self.collectible_id,
            kind=self.kind,
            position=(self.position.x, self.position.y),
            score_value=self.kind.score_value,
            sound_path=self.sound_path,
        )

    def _can_collect(self, recipient: HealthRecipient) -> bool:
        return True

    def _apply_pickup(self, recipient: HealthRecipient) -> None:
        return None

    def draw(self, surface: pygame.Surface, offset: tuple[int, int]) -> None:
        if not self.active:
            return
        bob_cycle = (0, -1, -3, -4, -3, -1)
        bob = bob_cycle[self.animation.frame_index % len(bob_cycle)]
        frame = self.animation.current_frame
        center = (
            round(self.position.x + offset[0]),
            round(self.position.y + offset[1] + bob),
        )
        surface.blit(frame, frame.get_rect(center=center))


class EmberShard(Collectible):
    kind = CollectibleType.EMBER_SHARD


class HealthItem(Collectible):
    kind = CollectibleType.HEALTH_ITEM
    pickup_size = (38, 42)
    sound_path = "sounds/health_pickup.wav"

    def _can_collect(self, recipient: HealthRecipient) -> bool:
        return recipient.health < recipient.max_health

    def _apply_pickup(self, recipient: HealthRecipient) -> None:
        recipient.heal(1)


class RareCrystal(Collectible):
    kind = CollectibleType.RARE_CRYSTAL
    pickup_size = (42, 52)
    sound_path = "sounds/rare_crystal.wav"


class SecretToken(Collectible):
    kind = CollectibleType.SECRET_TOKEN
    pickup_size = (44, 44)
    sound_path = "sounds/secret_token.wav"


COLLECTIBLE_CLASSES: dict[CollectibleType, type[Collectible]] = {
    CollectibleType.EMBER_SHARD: EmberShard,
    CollectibleType.HEALTH_ITEM: HealthItem,
    CollectibleType.RARE_CRYSTAL: RareCrystal,
    CollectibleType.SECRET_TOKEN: SecretToken,
}


def create_collectible(
    collectible_id: str,
    kind: CollectibleType,
    position: tuple[float, float],
) -> Collectible:
    return COLLECTIBLE_CLASSES[kind](collectible_id, position)


def _build_collectible_animation(kind: CollectibleType) -> AnimationController:
    frames = [_draw_collectible_frame(kind, frame) for frame in range(6)]
    return AnimationController(
        [AnimationClip.from_surfaces(kind.value, frames, fps=8.0, loop=True)]
    )


def _draw_collectible_frame(kind: CollectibleType, frame: int) -> pygame.Surface:
    surface = pygame.Surface((58, 64), pygame.SRCALPHA)
    center = (29, 31)
    pulse = (0, 1, 2, 3, 2, 1)[frame]
    glow = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

    if kind is CollectibleType.EMBER_SHARD:
        pygame.draw.circle(glow, (255, 121, 53, 32), center, 20 + pulse)
        points = [(29, 10 - pulse), (42 + pulse, 30), (29, 51 + pulse), (16 - pulse, 30)]
        pygame.draw.polygon(surface, (255, 137, 55), points)
        pygame.draw.polygon(surface, (255, 226, 128), [(29, 13), (29, 47), (19, 30)])
        pygame.draw.line(surface, (255, 246, 194), (29, 13), (39, 29), 3)
    elif kind is CollectibleType.RARE_CRYSTAL:
        pygame.draw.circle(glow, (76, 235, 255, 40), center, 24 + pulse)
        points = [(29, 5 - pulse), (47, 21), (40, 51 + pulse), (18, 51 + pulse), (11, 21)]
        pygame.draw.polygon(surface, (74, 211, 232), points)
        pygame.draw.polygon(surface, (171, 251, 255), [(29, 8), (29, 48), (14, 22)])
        pygame.draw.line(surface, (231, 255, 255), (30, 9), (44, 21), 4)
    elif kind is CollectibleType.SECRET_TOKEN:
        pygame.draw.circle(glow, (255, 214, 72, 45), center, 23 + pulse)
        pygame.draw.circle(surface, (244, 177, 43), center, 18 + pulse // 2)
        pygame.draw.circle(surface, (255, 233, 133), center, 13, 3)
        pygame.draw.arc(surface, (111, 71, 83), (21, 23, 17, 17), 0.2, 5.6, 3)
        pygame.draw.circle(surface, (111, 71, 83), center, 3)
    else:
        pygame.draw.circle(glow, (107, 255, 161, 38), center, 21 + pulse)
        pygame.draw.rect(surface, (73, 158, 128), (19, 15, 20, 34), border_radius=8)
        pygame.draw.rect(surface, (183, 247, 181), (22, 20, 14, 24), border_radius=5)
        pygame.draw.rect(surface, (238, 229, 162), (23, 10, 12, 9), border_radius=3)
        pygame.draw.rect(surface, (222, 88, 104), (27, 24, 4, 16))
        pygame.draw.rect(surface, (222, 88, 104), (21, 30, 16, 4))
    glow.blit(surface, (0, 0))
    return glow

