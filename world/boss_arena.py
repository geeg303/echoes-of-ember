"""Data-driven boss arena trigger, door locking, and camera bounds."""

from __future__ import annotations

from dataclasses import dataclass
import pygame


@dataclass(frozen=True, slots=True)
class BossArenaDefinition:
    boss_id: str
    spawn: tuple[float, float]
    bounds: pygame.Rect
    trigger: pygame.Rect
    door_ids: tuple[str, ...]
    pulse_source: tuple[float, float]


class BossArena:
    def __init__(self, definition: BossArenaDefinition, doors: list[object]) -> None:
        self.definition = definition
        available = {door.object_id: door for door in doors}
        self.doors = [available[door_id] for door_id in definition.door_ids]
        self.active = False
        self.completed = False

    def try_trigger(self, player_rect: pygame.Rect) -> bool:
        if self.active or self.completed or not self.definition.trigger.colliderect(player_rect):
            return False
        self.active = True
        for door in self.doors:
            door.close()
        return True

    def finish(self) -> None:
        self.active = False
        self.completed = True
        for door in self.doors:
            door.open()

    def reset(self) -> None:
        self.active = False
        self.completed = False
        for door in self.doors:
            door.open()

    @property
    def camera_bounds(self) -> pygame.Rect | None:
        return self.definition.bounds.copy() if self.active else None
