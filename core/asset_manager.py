"""Cached, failure-tolerant asset loading."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

import pygame

from settings import ASSET_ROOT

LOGGER = logging.getLogger(__name__)


class SoundLike(Protocol):
    def play(self, *args: object, **kwargs: object) -> object: ...

    def stop(self) -> None: ...

    def set_volume(self, volume: float) -> None: ...


class SilentSound:
    """Drop-in no-op used when audio is unavailable or an asset is missing."""

    def play(self, *args: object, **kwargs: object) -> None:
        return None

    def stop(self) -> None:
        return None

    def set_volume(self, volume: float) -> None:
        return None


class AssetManager:
    """Resolve and cache game assets without making optional files mandatory."""

    def __init__(self, root: Path = ASSET_ROOT) -> None:
        self.root = root
        self._images: dict[tuple[str, tuple[int, int] | None], pygame.Surface] = {}
        self._fonts: dict[tuple[str | None, int], pygame.font.Font] = {}
        self._sounds: dict[str, SoundLike] = {}

    def image(
        self,
        relative_path: str,
        size: tuple[int, int] | None = None,
    ) -> pygame.Surface:
        key = (relative_path, size)
        if key not in self._images:
            path = self.root / relative_path
            try:
                loaded = pygame.image.load(path).convert_alpha()
                image = pygame.transform.smoothscale(loaded, size) if size else loaded
            except (FileNotFoundError, pygame.error) as exc:
                LOGGER.warning("Using placeholder for image %s: %s", path, exc)
                image = self._placeholder_image(size or (64, 64))
            self._images[key] = image
        return self._images[key]

    def font(self, relative_path: str | None, size: int) -> pygame.font.Font:
        key = (relative_path, size)
        if key not in self._fonts:
            path = self.root / relative_path if relative_path else None
            try:
                self._fonts[key] = pygame.font.Font(path, size)
            except (FileNotFoundError, OSError, pygame.error, ImportError, NotImplementedError) as exc:
                LOGGER.warning("Using default font for %s: %s", path, exc)
                self._fonts[key] = pygame.font.Font(None, size)
        return self._fonts[key]

    def sound(self, relative_path: str) -> SoundLike:
        if relative_path not in self._sounds:
            path = self.root / relative_path
            try:
                if not pygame.mixer.get_init():
                    raise pygame.error("audio mixer is unavailable")
                self._sounds[relative_path] = pygame.mixer.Sound(path)
            except (FileNotFoundError, pygame.error, ImportError, NotImplementedError) as exc:
                LOGGER.warning("Using silent fallback for sound %s: %s", path, exc)
                self._sounds[relative_path] = SilentSound()
        return self._sounds[relative_path]

    @staticmethod
    def _placeholder_image(size: tuple[int, int]) -> pygame.Surface:
        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.fill((225, 65, 140, 255))
        pygame.draw.line(surface, (35, 18, 48), (0, 0), size, 4)
        pygame.draw.line(surface, (35, 18, 48), (size[0], 0), (0, size[1]), 4)
        return surface
