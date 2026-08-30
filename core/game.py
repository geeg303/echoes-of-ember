"""Top-level game lifecycle and fixed-resolution rendering."""

from __future__ import annotations

import logging

import pygame

from core.asset_manager import AssetManager
from entities.player import Player, PlayerControls
from settings import DISPLAY, GAME_TITLE, PLAYER_NAME, PROJECT_ROOT, SHOW_FPS
from world.collision import CollisionEngine
from world.level import Level

LOGGER = logging.getLogger(__name__)


class Game:
    """Own Pygame initialization, the main loop, display scaling, and shutdown."""

    def __init__(self) -> None:
        pygame.init()
        try:
            pygame.mixer.init()
        except (pygame.error, ImportError, NotImplementedError) as exc:
            LOGGER.warning("Audio disabled: %s", exc)

        pygame.display.set_caption(GAME_TITLE)
        self.fullscreen = DISPLAY.fullscreen
        self.screen = self._create_display()
        self.canvas = pygame.Surface(DISPLAY.internal_size).convert()
        self.clock = pygame.time.Clock()
        self.assets = AssetManager()
        self.running = True
        self._shutdown = False
        self._fps_font = self.assets.font(None, 24)
        self._ui_font = self.assets.font(None, 28)
        self.level = Level.load(PROJECT_ROOT / "data" / "levels" / "level_01.json")
        self.collision = CollisionEngine(self.level.tilemap)
        self.player = Player(self.level.player_spawn)
        self._jump_pressed = False
        self._jump_released = False
        LOGGER.info("Initialized %s at %sx%s", GAME_TITLE, *DISPLAY.internal_size)

    def _create_display(self) -> pygame.Surface:
        if self.fullscreen:
            return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        flags = pygame.RESIZABLE if DISPLAY.resizable else 0
        return pygame.display.set_mode(DISPLAY.window_size, flags)

    def run(self, frame_limit: int | None = None) -> None:
        frames = 0
        try:
            while self.running and (frame_limit is None or frames < frame_limit):
                dt = min(self.clock.tick(DISPLAY.target_fps) / 1000.0, 0.05)
                self._handle_events()
                self.update(dt)
                self.draw()
                frames += 1
        finally:
            self.shutdown()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                elif event.key in (pygame.K_SPACE, pygame.K_z, pygame.K_UP):
                    self._jump_pressed = True
            elif event.type == pygame.KEYUP and event.key in (
                pygame.K_SPACE,
                pygame.K_z,
                pygame.K_UP,
            ):
                self._jump_released = True

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        self.screen = self._create_display()
        LOGGER.info("Fullscreen: %s", self.fullscreen)

    def update(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        move_axis = float(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - float(
            keys[pygame.K_LEFT] or keys[pygame.K_a]
        )
        controls = PlayerControls(
            move_axis=move_axis,
            jump_pressed=self._jump_pressed,
            jump_held=bool(keys[pygame.K_SPACE] or keys[pygame.K_z] or keys[pygame.K_UP]),
            jump_released=self._jump_released,
        )
        self.player.update(dt, controls, self.collision)
        if self.player.hit_hazard:
            self.player.respawn(self.level.player_spawn)
        self._jump_pressed = False
        self._jump_released = False

    def draw(self) -> None:
        self.canvas.fill((24, 31, 64))
        self.level.tilemap.draw(self.canvas)
        self.player.draw(self.canvas)
        help_label = self._ui_font.render(
            f"{PLAYER_NAME}: A/D or arrows to move  •  Space/Z/Up to jump  •  F11 fullscreen",
            True,
            (226, 233, 245),
        )
        self.canvas.blit(help_label, (58, 24))
        if SHOW_FPS:
            label = self._fps_font.render(f"FPS {self.clock.get_fps():.0f}", True, (210, 220, 245))
            self.canvas.blit(label, (16, 12))
        scaled = pygame.transform.scale(self.canvas, self.screen.get_size())
        self.screen.blit(scaled, (0, 0))
        pygame.display.flip()

    def shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        self.running = False
        pygame.quit()
        LOGGER.info("Clean shutdown complete")
