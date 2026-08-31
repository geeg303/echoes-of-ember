"""Top-level game lifecycle and fixed-resolution rendering."""

from __future__ import annotations

import logging

import pygame

from core.asset_manager import AssetManager
from entities.level_goal import EmberGate
from entities.player import Player, PlayerControls
from systems.combat import DamageSource
from systems.collectible_system import CollectibleManager
from systems.enemy_system import EnemyManager
from systems.player_combat import PlayerCombatController
from systems.projectile_system import ProjectileManager
from systems.powerup_system import PowerUpManager, PowerUpSystem, PowerUpType
from systems.world_object_system import WorldObjectManager
from systems.level_completion import (
    ExitType,
    GameplayPhase,
    LevelResult,
    calculate_rating,
)
from systems.progression import LevelProgress
from systems.secret_system import SecretSystem
from settings import DEBUG_MODE, DISPLAY, GAME_TITLE, LEVEL_COMPLETION_SEQUENCE_DURATION, SHOW_FPS
from states.level_complete import LevelCompleteScreen
from states.world_complete import WorldCompleteScreen
from states.world_map import WorldMapScreen
from ui.debug_overlay import DebugOverlay
from ui.hud import HUD
from ui.notifications import NotificationQueue
from world.background import ParallaxBackground
from world.camera import Camera
from world.collision import CollisionEngine
from world.level import Level
from world.campaign import DEFAULT_WORLD_REGISTRY, WorldProgress, WorldRegistry
from world.world_map import WorldMapRuntime

LOGGER = logging.getLogger(__name__)


class Game:
    """Own Pygame initialization, the main loop, display scaling, and shutdown."""

    def __init__(self, level_id: str = "verdant_01", registry: WorldRegistry | None = None, start_on_map: bool = False) -> None:
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
        self.level_complete_screen = LevelCompleteScreen(
            self.assets.font(None, 44), self.assets.font(None, 29), self.assets.font(None, 22)
        )
        self.notifications = NotificationQueue(self.assets.font(None, 30))
        self.world_complete_screen = WorldCompleteScreen(self.assets.font(None, 44), self.assets.font(None, 29), self.assets.font(None, 22))
        self.registry = registry or WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
        if level_id not in self.registry.level_paths:
            raise ValueError(f"unknown registered level: {level_id}")
        self.world_progress = WorldProgress(self.registry)
        self.world_map_runtime = WorldMapRuntime(self.registry.map_definition, self.world_progress)
        self.world_map_screen = WorldMapScreen(
            self.world_map_runtime, self.assets.font(None, 38), self.assets.font(None, 25), self.assets.font(None, 19)
        )
        self.show_world_summary = False
        self.app_mode = "map" if start_on_map else "gameplay"
        self.level_path = self.registry.level_paths[level_id]
        if not start_on_map:
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
        self.secrets = SecretSystem(self.level.secret_definitions)
        self.goal = EmberGate(self.level.goal.position, self.level.goal.requires_interact)
        self.gameplay_phase = GameplayPhase.PLAYING
        self.elapsed_time = 0.0
        self.deaths = 0
        self.completion_timer = 0.0
        self.level_result: LevelResult | None = None
        self.level_complete_screen.reset()
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
                if self.app_mode == "map":
                    self._handle_map_key(event.key)
                    continue
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif self.gameplay_phase is GameplayPhase.LEVEL_COMPLETE and event.key == pygame.K_r:
                    self.reset_level()
                elif self.gameplay_phase is GameplayPhase.LEVEL_COMPLETE and event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_m):
                    self.return_to_world_map()
                elif event.key == pygame.K_m:
                    self.return_to_world_map()
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

    def _handle_map_key(self, key: int) -> None:
        if self.show_world_summary:
            if key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                self.show_world_summary = False
            return
        directions = {
            pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0),
            pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
            pygame.K_UP: (0, -1), pygame.K_w: (0, -1),
            pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1),
        }
        if key in directions:
            self.world_map_runtime.choose_direction(pygame.Vector2(directions[key]))
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            action, level_id = self.world_map_screen.activate_current()
            if action == "level" and level_id:
                self.load_level(level_id)
            elif action == "world_summary":
                self.show_world_summary = True
        elif key == pygame.K_ESCAPE:
            self.running = False

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        self.screen = self._create_display()
        LOGGER.info("Fullscreen: %s", self.fullscreen)

    def update(self, dt: float) -> None:
        if self.app_mode == "map":
            self.world_map_screen.update(dt)
            return
        if self.gameplay_phase in {GameplayPhase.LEVEL_COMPLETE, GameplayPhase.WORLD_COMPLETE}:
            self._clear_frame_inputs()
            return
        if self.gameplay_phase is GameplayPhase.COMPLETION_SEQUENCE:
            self.completion_timer = max(0.0, self.completion_timer - dt)
            self.goal.update(dt, self.player.rect)
            self.camera.update(self.player.rect, pygame.Vector2(), dt)
            self.hud.update(dt)
            if self.completion_timer <= 0.0:
                self.gameplay_phase = GameplayPhase.LEVEL_COMPLETE
            self._clear_frame_inputs()
            return
        self.elapsed_time += dt
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
            self.deaths += 1
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
        secret_update = self.secrets.update(self.player.rect, self._interact_pressed, self.enemies.defeated_ids)
        if secret_update.score_awarded:
            self.progress.award_score(secret_update.score_awarded)
            self.hud.notify_score_changed()
        for message in secret_update.messages:
            self.notifications.push(message)
        if secret_update.secret_exit_id:
            self._begin_completion(secret_update.secret_exit_id, ExitType.SECRET)
        self.notifications.update(dt)
        self.goal.update(dt, self.player.rect)
        if not self.player.is_dead and self.goal.try_activate(self.player.rect, self._interact_pressed):
            if self.level.metadata.requirements.evaluate(True, self.progress):
                self._begin_completion("ember_gate", ExitType.NORMAL)
        self.hud.update(dt)
        self._clear_frame_inputs()

    def _clear_frame_inputs(self) -> None:
        self._jump_pressed = False
        self._jump_released = False
        self._attack_pressed = False
        self._interact_pressed = False

    def _begin_completion(self, exit_id: str = "ember_gate", exit_type: ExitType = ExitType.NORMAL) -> None:
        if self.gameplay_phase is not GameplayPhase.PLAYING:
            return
        self.gameplay_phase = GameplayPhase.GOAL_TRIGGERED
        self.level_result = self._build_level_result(exit_id, exit_type)
        self.world_progress.record(self.level_result)
        self.gameplay_phase = GameplayPhase.COMPLETION_SEQUENCE
        self.completion_timer = LEVEL_COMPLETION_SEQUENCE_DURATION
        self.projectiles.clear()
        self.player.velocity.update()
        self.assets.sound("sounds/level_complete.wav").play()
        self.camera.shake(4.0, 0.2)

    def _build_level_result(self, exit_id: str = "ember_gate", exit_type: ExitType = ExitType.NORMAL) -> LevelResult:
        from systems.progression import CollectibleType

        shards = self.progress.count(CollectibleType.EMBER_SHARD)
        rating = calculate_rating(
            self.progress.score, shards, self.progress.total(CollectibleType.EMBER_SHARD),
            self.elapsed_time, self.level.metadata.ratings,
        )
        return LevelResult(
            level_id=self.level.metadata.level_id, completed=True,
            completion_time=self.elapsed_time, score=self.progress.score,
            ember_shards_collected=shards,
            ember_shards_total=self.progress.total(CollectibleType.EMBER_SHARD),
            rare_crystals_collected=self.progress.count(CollectibleType.RARE_CRYSTAL),
            rare_crystals_total=self.progress.total(CollectibleType.RARE_CRYSTAL),
            secret_tokens_collected=self.progress.count(CollectibleType.SECRET_TOKEN),
            secret_tokens_total=self.progress.total(CollectibleType.SECRET_TOKEN),
            enemies_defeated=len(self.enemies.defeated_ids), enemies_total=len(self.level.enemy_spawns),
            deaths=self.deaths, lives_remaining=self.player.lives,
            health_remaining=self.player.health,
            checkpoints_activated=len(self.world_objects.activated_checkpoint_ids),
            rating=rating, secrets_discovered=self.secrets.discovered_count,
            secrets_total=len(self.level.secret_definitions),
            secret_rooms_completed=self.secrets.completed_room_count,
            exit_type=exit_type, exit_id=exit_id,
        )

    def draw(self) -> None:
        if self.app_mode == "map":
            self.world_map_screen.draw(self.canvas)
            if self.show_world_summary:
                self.world_complete_screen.draw(self.canvas, self.world_progress)
            scaled = pygame.transform.scale(self.canvas, self.screen.get_size())
            self.screen.blit(scaled, (0, 0))
            pygame.display.flip()
            return
        self.background.draw(self.canvas, self.camera.position)
        tile_view = self.camera.view_rect.inflate(
            self.level.tilemap.tile_size * 2,
            self.level.tilemap.tile_size * 2,
        )
        offset = self.camera.render_offset
        self.level.tilemap.draw(self.canvas, tile_view, offset)
        self.world_objects.draw(self.canvas, self.camera.view_rect, offset)
        self.goal.draw(self.canvas, offset)
        self.secrets.draw(self.canvas, self.camera.view_rect, offset)
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
            self.elapsed_time,
        )
        self.notifications.draw(self.canvas)
        if DEBUG_MODE:
            self.debug_overlay.draw(self.canvas, self.player)
        if SHOW_FPS:
            label = self._fps_font.render(f"FPS {self.clock.get_fps():.0f}", True, (210, 220, 245))
            position = (self.canvas.get_width() - 16, self.canvas.get_height() - 12)
            self.canvas.blit(label, label.get_rect(bottomright=position))
        if self.gameplay_phase is GameplayPhase.COMPLETION_SEQUENCE:
            fade = pygame.Surface(self.canvas.get_size(), pygame.SRCALPHA)
            fade.fill((255, 183, 78, round(35 * (1.0 - self.completion_timer / LEVEL_COMPLETION_SEQUENCE_DURATION))))
            self.canvas.blit(fade, (0, 0))
        elif self.gameplay_phase is GameplayPhase.LEVEL_COMPLETE and self.level_result:
            self.level_complete_screen.draw(self.canvas, self.level.metadata.display_name, self.level_result)
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
        self.notifications.clear()
        LOGGER.info("Restarted level: %s", self.level.name)

    def load_level(self, level_id: str) -> None:
        self.app_mode = "gameplay"
        self.level_path = self.registry.level_paths[level_id]
        self.reset_level()

    def return_to_world_map(self) -> None:
        level_id = self.level.metadata.level_id
        self.world_map_runtime.return_to_level_node(level_id)
        self.app_mode = "map"
        self.show_world_summary = False
        if self.level_result is not None:
            self.world_map_screen.notify("PATH OPENED — CHOOSE YOUR NEXT DESTINATION")

    def continue_campaign(self) -> None:
        """Compatibility alias: Continue now returns to the authored World Map."""
        self.return_to_world_map()

    def shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        self.running = False
        pygame.quit()
        LOGGER.info("Clean shutdown complete")
