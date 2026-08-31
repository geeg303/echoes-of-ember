"""Top-level game lifecycle and fixed-resolution rendering."""

from __future__ import annotations

import logging

import pygame

from core.asset_manager import AssetManager
from entities.player import Player, PlayerControls
from systems.combat import DamageSource
from systems.collectible_system import CollectibleManager
from systems.enemy_system import EnemyManager
from systems.player_combat import PlayerCombatController
from systems.projectile_system import ProjectileManager
from systems.powerup_system import PowerUpManager, PowerUpSystem, PowerUpType
from systems.world_object_system import WorldObjectManager
from systems.progression import LevelProgress
from settings import DEBUG_MODE, DISPLAY, GAME_TITLE, PROJECT_ROOT, SHOW_FPS
from ui.debug_overlay import DebugOverlay
from ui.hud import HUD
from world.background import ParallaxBackground
from world.camera import Camera
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
        self.debug_overlay = DebugOverlay(self.assets.font(None, 22))
        self.hud = HUD(
            self.assets.font(None, 26),
            self.assets.font(None, 20),
            self.assets.font(None, 32),
        )
        self.level_path = PROJECT_ROOT / "data" / "levels" / "level_01.json"
        self._load_level_runtime()
        self._jump_pressed = False
        self._jump_released = False
        self._attack_pressed = False
        LOGGER.info("Initialized %s at %sx%s", GAME_TITLE, *DISPLAY.internal_size)

    def _load_level_runtime(self) -> None:
        self.level = Level.load(self.level_path)
        self.collision = CollisionEngine(self.level.tilemap)
        self.player = Player(self.level.player_spawn)
        world_size = (self.level.tilemap.pixel_width, self.level.tilemap.pixel_height)
        self.camera = Camera(DISPLAY.internal_size, world_size)
        self.camera.snap_to(self.player.rect)
        self.background = ParallaxBackground(*world_size)
        self.progress = LevelProgress.from_types(
            [spawn.kind for spawn in self.level.collectible_spawns]
        )
        self.collectibles = CollectibleManager(self.level.collectible_spawns)
        self.projectiles = ProjectileManager()
        self.enemies = EnemyManager(self.level.enemy_spawns, self.projectiles)
        self.player_combat = PlayerCombatController()
        self.powerups = PowerUpSystem(self.player)
        self.powerup_pickups = PowerUpManager(self.level.powerup_spawns)
        self.world_objects = WorldObjectManager(self.level.world_object_spawns, self.level.player_spawn)
        self._interact_pressed = False

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
                elif DEBUG_MODE and event.key == pygame.K_F5:
                    self.player.trigger_attack()
                elif DEBUG_MODE and event.key == pygame.K_F6:
                    self.player.trigger_hurt()
                elif DEBUG_MODE and event.key == pygame.K_F7:
                    self.reset_level()
                elif event.key == pygame.K_f:
                    self._attack_pressed = True
                elif event.key == pygame.K_e:
                    self._interact_pressed = True
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
        self.powerups.update(dt)
        self.world_objects.update_before_player(dt, self.player, self.level.tilemap)
        self.player.update(dt, controls, self.collision, self.powerups.movement_modifiers)
        if self.world_objects.resolve_after_player(self.player, self._interact_pressed, self.level.tilemap):
            self.assets.sound("sounds/world_object_activate.wav").play()
        self.player_combat.ember_pulse_enabled = self.powerups.grants_ranged_attack
        self.player_combat.update(dt)
        if self._attack_pressed and self.player_combat.try_attack(self.player, self.projectiles):
            self.assets.sound("sounds/ember_pulse.wav").play()
        if self.player.hit_hazard and not self.player.is_dead:
            damage = self.player.apply_damage(1, DamageSource.HAZARD)
            if damage.applied:
                self.hud.notify_health_changed()
                self.camera.shake(8.0, 0.18)
            if damage.applied and not damage.died:
                self.player.reposition(self.world_objects.respawn_position)
                self.camera.snap_to(self.player.rect)
        if self.player.death_animation_finished:
            self.player.lose_life_and_restore()
            self.powerups.clear("life_lost")
            self.player.respawn(self.world_objects.respawn_position)
            self.camera.snap_to(self.player.rect)
        self.camera.update(self.player.rect, self.player.velocity, dt)
        enemy_result = self.enemies.update(
            dt,
            self.camera.view_rect,
            self.player,
            self.collision,
            self.level.tilemap,
            self.progress,
        )
        if enemy_result.player_damaged:
            self.hud.notify_health_changed()
        if enemy_result.score_awarded:
            self.hud.notify_score_changed()
        if enemy_result.shake:
            self.camera.shake(enemy_result.shake, 0.12)
        self.collectibles.update(dt, self.camera.view_rect)
        self.powerup_pickups.update(dt, self.camera.view_rect)
        if not self.player.is_dead:
            for result in self.collectibles.collect_overlaps(
                self.player.rect,
                self.player,
                self.progress,
            ):
                self.assets.sound(result.sound_path).play()
                self.hud.notify_pickup(result)
            for kind in self.powerup_pickups.collect_overlaps(self.player.rect, self.powerups):
                self.assets.sound(f"sounds/{kind.value}_pickup.wav").play()
        power_event = self.powerups.consume_event()
        if power_event in {"expired", "absorbed"}:
            self.assets.sound(f"sounds/powerup_{power_event}.wav").play()
        self.hud.update(dt)
        self._jump_pressed = False
        self._jump_released = False
        self._attack_pressed = False
        self._interact_pressed = False

    def draw(self) -> None:
        self.background.draw(self.canvas, self.camera.position)
        tile_view = self.camera.view_rect.inflate(
            self.level.tilemap.tile_size * 2,
            self.level.tilemap.tile_size * 2,
        )
        offset = self.camera.render_offset
        self.level.tilemap.draw(self.canvas, tile_view, offset)
        self.world_objects.draw(self.canvas, self.camera.view_rect, offset)
        self.collectibles.draw(self.canvas, self.camera.view_rect, offset)
        self.powerup_pickups.draw(self.canvas, self.camera.view_rect, offset)
        self.enemies.draw(self.canvas, self.camera.view_rect, offset)
        if self.powerups.has(PowerUpType.STONE_GUARD):
            pygame.draw.circle(self.canvas, (185, 213, 235), self.player.rect.move(offset).center, 42, 3)
        self.player.draw(self.canvas, offset)
        self.hud.draw(
            self.canvas,
            self.player.health,
            self.player.max_health,
            self.player.lives,
            self.progress,
            self.level.name,
            self.powerups.hud_text,
            self.powerups.feedback,
            self.powerups.timer_low,
        )
        if DEBUG_MODE:
            self.debug_overlay.draw(self.canvas, self.player)
        if SHOW_FPS:
            label = self._fps_font.render(f"FPS {self.clock.get_fps():.0f}", True, (210, 220, 245))
            position = (self.canvas.get_width() - 16, self.canvas.get_height() - 12)
            self.canvas.blit(label, label.get_rect(bottomright=position))
        scaled = pygame.transform.scale(self.canvas, self.screen.get_size())
        self.screen.blit(scaled, (0, 0))
        pygame.display.flip()

    def reset_level(self) -> None:
        """Reload original level state, including collectibles and current score."""
        self._load_level_runtime()
        self._jump_pressed = False
        self._jump_released = False
        self._attack_pressed = False
        self._interact_pressed = False
        self.hud.reset_feedback()
        LOGGER.info("Restarted level: %s", self.level.name)

    def shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        self.running = False
        pygame.quit()
        LOGGER.info("Clean shutdown complete")
