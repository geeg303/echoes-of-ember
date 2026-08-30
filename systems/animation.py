"""Reusable, delta-time-aware frame animation primitives."""

from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass(frozen=True, slots=True)
class AnimationFrame:
    image: pygame.Surface
    duration: float
    events: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.duration <= 0.0:
            raise ValueError("animation frame duration must be positive")


@dataclass(frozen=True, slots=True)
class AnimationClip:
    name: str
    frames: tuple[AnimationFrame, ...]
    loop: bool = True

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("animation clip name cannot be empty")
        if not self.frames:
            raise ValueError(f"animation clip {self.name!r} requires at least one frame")

    @classmethod
    def from_surfaces(
        cls,
        name: str,
        surfaces: list[pygame.Surface] | tuple[pygame.Surface, ...],
        fps: float,
        loop: bool = True,
        frame_events: dict[int, tuple[str, ...]] | None = None,
    ) -> "AnimationClip":
        if fps <= 0.0:
            raise ValueError("animation fps must be positive")
        events = frame_events or {}
        duration = 1.0 / fps
        return cls(
            name=name,
            frames=tuple(
                AnimationFrame(surface, duration, events.get(index, ()))
                for index, surface in enumerate(surfaces)
            ),
            loop=loop,
        )


class AnimationController:
    """Play named clips without exposing timer bookkeeping to entities."""

    def __init__(self, animations: list[AnimationClip] | tuple[AnimationClip, ...]) -> None:
        self.animations = {animation.name: animation for animation in animations}
        if not self.animations:
            raise ValueError("animation controller requires at least one clip")
        if len(self.animations) != len(animations):
            raise ValueError("animation names must be unique")
        self.current_name = next(iter(self.animations))
        self.frame_index = 0
        self.elapsed = 0.0
        self.finished = False
        self.flip_x = False
        self._pending_events: list[str] = list(self.current_clip.frames[0].events)
        self._flipped_cache: dict[tuple[str, int], pygame.Surface] = {}

    @property
    def current_clip(self) -> AnimationClip:
        return self.animations[self.current_name]

    @property
    def current_frame(self) -> pygame.Surface:
        frame = self.current_clip.frames[self.frame_index].image
        if not self.flip_x:
            return frame
        key = (self.current_name, self.frame_index)
        if key not in self._flipped_cache:
            self._flipped_cache[key] = pygame.transform.flip(frame, True, False)
        return self._flipped_cache[key]

    def play(self, name: str, restart: bool = False) -> None:
        if name not in self.animations:
            raise KeyError(f"unknown animation: {name}")
        if name == self.current_name and not restart:
            return
        self.current_name = name
        self.reset()

    def reset(self) -> None:
        self.frame_index = 0
        self.elapsed = 0.0
        self.finished = False
        self._pending_events = list(self.current_clip.frames[0].events)

    def update(self, dt: float) -> tuple[str, ...]:
        if dt < 0.0:
            raise ValueError("animation delta time cannot be negative")
        if not self.finished:
            self.elapsed += dt
            while self.elapsed >= self.current_clip.frames[self.frame_index].duration:
                self.elapsed -= self.current_clip.frames[self.frame_index].duration
                if self.frame_index + 1 < len(self.current_clip.frames):
                    self.frame_index += 1
                    self._pending_events.extend(self.current_clip.frames[self.frame_index].events)
                elif self.current_clip.loop:
                    self.frame_index = 0
                    self._pending_events.extend(self.current_clip.frames[0].events)
                else:
                    self.finished = True
                    self.elapsed = 0.0
                    break
        events = tuple(self._pending_events)
        self._pending_events.clear()
        return events

