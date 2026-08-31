"""Top-level game lifecycle and fixed-resolution rendering."""

from __future__ import annotations

import logging

import pygame

from core.asset_manager import AssetManager
from core.save_manager import SaveManager, SlotState
from systems.save_data import SaveSession
from systems.boss_system import BossSystem
from entities.level_goal import EmberGate
from entities.player import Player, PlayerControls
from systems.combat import DamageSource
from systems.collectible_system import CollectibleManager
from systems.enemy_system import EnemyManager
from systems.effects_system import EffectQuality, EffectsSystem
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
from settings import DEBUG_MODE, DISPLAY, EFFECT_PARTICLE_CAP, GAME_TITLE, LEVEL_COMPLETION_SEQUENCE_DURATION, SHOW_FPS
from states.level_complete import LevelCompleteScreen
from states.world_complete import WorldCompleteScreen
from states.world_map import WorldMapScreen
from ui.debug_overlay import DebugOverlay
from ui.hud import HUD
from ui.boss_hud import BossHUD
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

    def __init__(self, level_id: str = "verdant_01", registry: WorldRegistry | None = None, start_on_map: bool = False, save_manager: SaveManager | None = None, slot_id: int = 1, new_game: bool = False, persistence: bool = False) -> None:
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
        self.boss_hud = BossHUD(self.assets.font(None, 25), self.assets.font(None, 17))
        self.level_complete_screen = LevelCompleteScreen(
            self.assets.font(None, 44), self.assets.font(None, 29), self.assets.font(None, 22)
        )
        self.notifications = NotificationQueue(self.assets.font(None, 30))
        self.effects = EffectsSystem(capacity=EFFECT_PARTICLE_CAP)
        self._effect_trail_timer = 0.0
        self.world_complete_screen = WorldCompleteScreen(self.assets.font(None, 44), self.assets.font(None, 29), self.assets.font(None, 22))
        self.registry = registry or WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
        if level_id not in self.registry.level_paths:
            raise ValueError(f"unknown registered level: {level_id}")
        self.persistence_enabled = persistence
        self.save_manager = save_manager or (SaveManager(self.registry) if persistence else None)
        self.save_session: SaveSession | None = None
        self.save_warning = ""
        if persistence and self.save_manager is not None:
            if new_game:
                self.save_session = self.save_manager.new_game(slot_id, overwrite=True)
            else:
                loaded = self.save_manager.load(slot_id)
                if loaded.session is not None:
                    self.save_session = loaded.session
                    if loaded.state is SlotState.RECOVERED:
                        self.save_warning = "SAVE RECOVERED FROM BACKUP"
                elif loaded.state is SlotState.EMPTY:
                    self.save_session = self.save_manager.new_game(slot_id)
                else:
                    self.save_warning = "SAVE UNAVAILABLE — USE --NEW-GAME TO RESET"
                    self.persistence_enabled = False
                    self.save_session = SaveSession.fresh(slot_id, self.registry)
        self.world_progress = self.save_session.progress if self.save_session else WorldProgress(self.registry)
        self.world_map_runtime = WorldMapRuntime(self.registry.map_definition, self.world_progress)
        if self.save_session:
            saved_node = self.registry.map_definition.nodes[self.save_session.current_map_node]
            self.world_map_runtime.current_node_id = saved_node.node_id
            self.world_map_runtime.avatar_position.update(saved_node.position)
        self.world_map_screen = WorldMapScreen(
            self.world_map_runtime, self.assets.font(None, 38), self.assets.font(None, 25), self.assets.font(None, 19)
        )
        if self.save_warning:
            self.world_map_screen.notify(self.save_warning)
        self.show_world_summary = False
        self.app_mode = "map" if start_on_map else "gameplay"
        self.level_path = self.registry.level_paths[level_id]
        if not start_on_map:
            self._load_level_runtime()
        else:
            self._configure_map_effects()
        self._jump_pressed = False
        self._jump_released = False
        self._attack_pressed = False
        LOGGER.info("Initialized %s at %sx%s", GAME_TITLE, *DISPLAY.internal_size)

    def _load_level_runtime(self) -> None:
        self.effects.clear()
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
        self.boss_system = (
            BossSystem(self.level.boss_encounter, self.world_objects.doors, self.projectiles)
            if self.level.boss_encounter is not None else None
        )
        self.secrets = SecretSystem(self.level.secret_definitions)
        self.goal = EmberGate(self.level.goal.position, self.level.goal.requires_interact)
        self.gameplay_phase = GameplayPhase.PLAYING
        self.elapsed_time = 0.0
        self.deaths = 0
        self.completion_timer = 0.0
        self.level_result: LevelResult | None = None
        self.level_complete_screen.reset()
        self._interact_pressed = False
        self._configure_level_effects()

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
                    quality = self.effects.toggle_optional()
                    self.notifications.push(f"OPTIONAL EFFECTS: {quality.value.upper()}")
                elif DEBUG_MODE and event.key == pygame.K_F7:
                    self.reset_level()
                elif event.key == pygame.K_f:
                    self._attack_pressed = True
                elif event.key == pygame.K_e:
                    self._interact_pressed = True
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE) and self.boss_system and self.boss_system.active:
                    self.boss_system.skip_intro()
                    if event.key == pygame.K_SPACE:
                        self._jump_pressed = True
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
        if self.save_session is not None:
            self.save_session.play_time_seconds += dt
        if self.app_mode == "map":
            previous_node = self.world_map_runtime.current_node_id
            self.world_map_screen.update(dt)
            self.effects.update(dt)
            if self.world_map_runtime.current_node_id != previous_node:
                self.effects.spawn("route_unlocked", self.world_map_runtime.avatar_position)
                self._mark_save_dirty()
                self._autosave()
            return
        if self.gameplay_phase in {GameplayPhase.LEVEL_COMPLETE, GameplayPhase.WORLD_COMPLETE}:
            self._clear_frame_inputs()
            return
        if self.gameplay_phase is GameplayPhase.COMPLETION_SEQUENCE:
            self.completion_timer = max(0.0, self.completion_timer - dt)
            self.goal.update(dt, self.player.rect)
            self.camera.update(self.player.rect, pygame.Vector2(), dt)
            self.hud.update(dt)
            self.effects.update(dt, self.camera.view_rect)
            self.effects.apply_shake(self.camera)
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
        previous_grounded = self.player.grounded
        previous_double_jump_fx = self.player.double_jump_effect_timer
        previous_health = self.player.health
        previous_checkpoints = set(self.world_objects.activated_checkpoint_ids)
        previous_switches = {item.object_id for item in self.world_objects.switches if item.active}
        self.powerups.update(dt)
        self.world_objects.update_before_player(dt, self.player, self.level.tilemap)
        self.player.update(dt, controls, self.collision, self.powerups.movement_modifiers)
        if previous_grounded and not self.player.grounded and self.player.velocity.y < 0:
            self.effects.spawn("player_jump_dust", self.player.rect.midbottom)
        if not previous_grounded and self.player.grounded:
            self.effects.spawn("player_land_dust", self.player.rect.midbottom)
        if self.player.double_jump_effect_timer > previous_double_jump_fx:
            self.effects.spawn("aether_double_jump", self.player.rect.center)
        if self.world_objects.resolve_after_player(self.player, self._interact_pressed, self.level.tilemap):
            self.assets.sound("sounds/world_object_activate.wav").play()
            new_checkpoints = self.world_objects.activated_checkpoint_ids - previous_checkpoints
            for item in self.world_objects.checkpoints:
                if item.object_id in new_checkpoints:
                    self.effects.spawn("checkpoint_activate", item.rect.center)
                    self.effects.start_emitter(f"checkpoint:{item.object_id}", "checkpoint_idle", item.rect.center)
            new_switches = {item.object_id for item in self.world_objects.switches if item.active} - previous_switches
            for item in self.world_objects.switches:
                if item.object_id in new_switches: self.effects.spawn("switch_activate", item.rect.center)
            for door in self.world_objects.doors:
                if any(door.object_id in switch.target_ids for switch in self.world_objects.switches if switch.object_id in new_switches): self.effects.spawn("door_open", door.rect.center)
        self.player_combat.ember_pulse_enabled = self.powerups.grants_ranged_attack
        self.player_combat.update(dt)
        if self._attack_pressed and self.player_combat.try_attack(self.player, self.projectiles):
            self.assets.sound("sounds/ember_pulse.wav").play()
            self.effects.spawn("ember_pulse_launch", self.player.rect.center)
        if self.player.hit_hazard and not self.player.is_dead:
            damage = self.player.apply_damage(1, DamageSource.HAZARD)
            if damage.applied:
                self.hud.notify_health_changed()
                self.effects.request_shake(8.0, 0.18)
                self.effects.spawn("player_death" if damage.died else "player_damage", self.player.rect.center)
                self.effects.request_flash((142, 42, 37), 68, 0.16)
            if damage.applied and not damage.died:
                self.player.reposition(self.world_objects.respawn_position)
                self.camera.snap_to(self.player.rect)
        if self.player.death_animation_finished:
            self.deaths += 1
            self.player.lose_life_and_restore()
            self.powerups.clear("life_lost")
            if self.boss_system is not None:
                self.boss_system.reset_encounter(self.powerups)
                self.camera.set_bounds(None)
            self.player.respawn(self.world_objects.respawn_position)
            self.camera.snap_to(self.player.rect)
            self._reset_transient_effects()
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
            self.effects.spawn("player_death" if enemy_result.player_died else "player_damage", self.player.rect.center)
            self.effects.request_flash((142, 42, 37), 62, 0.14)
        if enemy_result.score_awarded:
            self.hud.notify_score_changed()
        if enemy_result.shake:
            self.effects.request_shake(enemy_result.shake, 0.12)
        self._drain_combat_effects(self.enemies.effects)
        if self.boss_system is not None:
            boss_result = self.boss_system.update(dt, self.player, self.powerups, self.progress)
            self.camera.set_bounds(self.boss_system.arena.camera_bounds)
            if self.boss_system.active:
                focus = self.player.rect.union(self.boss_system.boss.rect)
                if boss_result.triggered:
                    self.camera.snap_to(focus)
                else:
                    self.camera.update(focus, pygame.Vector2(), dt)
            if boss_result.player_damaged:
                self.hud.notify_health_changed()
            if boss_result.score_awarded:
                self.hud.notify_score_changed()
            if boss_result.shake:
                self.effects.request_shake(boss_result.shake, 0.25)
            self._emit_boss_effects(boss_result)
            self._drain_combat_effects(self.boss_system.effects, boss=True)
            for hook in boss_result.audio_events:
                self.assets.sound(f"sounds/boss_{hook}.wav").play()
            if boss_result.defeat_sequence_complete:
                self._begin_completion("ashen_warden", ExitType.NORMAL, boss_id="ashen_warden")
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
                pickup_fx = {"ember_shard":"ember_shard_pickup", "rare_crystal":"rare_crystal_pickup", "secret_token":"secret_token_pickup"}.get(result.kind.value)
                if pickup_fx: self.effects.spawn(pickup_fx, result.position)
            for kind in self.powerup_pickups.collect_overlaps(self.player.rect, self.powerups):
                self.assets.sound(f"sounds/{kind.value}_pickup.wav").play()
                pickup_fx = {PowerUpType.EMBER_PULSE:"ember_pulse_pickup", PowerUpType.WIND_BOOTS:"wind_boots_trail", PowerUpType.AETHER_WING:"aether_double_jump", PowerUpType.STONE_GUARD:"stone_guard_activate"}[kind]
                self.effects.spawn(pickup_fx, self.player.rect.center)
        power_event = self.powerups.consume_event()
        if power_event in {"expired", "absorbed"}:
            self.assets.sound(f"sounds/powerup_{power_event}.wav").play()
            if power_event == "absorbed":
                self.effects.spawn("stone_guard_break", self.player.rect.center)
                self.effects.request_flash((170, 196, 218), 58, 0.14)
        secret_update = self.secrets.update(self.player.rect, self._interact_pressed, self.enemies.defeated_ids)
        if secret_update.score_awarded:
            self.progress.award_score(secret_update.score_awarded)
            self.hud.notify_score_changed()
        for message in secret_update.messages:
            self.notifications.push(message)
            self.effects.spawn("challenge_complete" if "CHALLENGE" in message else "secret_discovered", self.player.rect.center)
        if secret_update.secret_exit_id:
            self._begin_completion(secret_update.secret_exit_id, ExitType.SECRET)
        self.notifications.update(dt)
        self.goal.update(dt, self.player.rect)
        if self.boss_system is None and not self.player.is_dead and self.goal.try_activate(self.player.rect, self._interact_pressed):
            if self.level.metadata.requirements.evaluate(True, self.progress):
                self._begin_completion("ember_gate", ExitType.NORMAL)
        self.hud.update(dt)
        self._update_effects(dt)
        self._clear_frame_inputs()

    def _clear_frame_inputs(self) -> None:
        self._jump_pressed = False
        self._jump_released = False
        self._attack_pressed = False
        self._interact_pressed = False

    def _begin_completion(self, exit_id: str = "ember_gate", exit_type: ExitType = ExitType.NORMAL, boss_id: str | None = None) -> None:
        if self.gameplay_phase is not GameplayPhase.PLAYING:
            return
        self.gameplay_phase = GameplayPhase.GOAL_TRIGGERED
        self.level_result = self._build_level_result(exit_id, exit_type)
        if boss_id is not None:
            self.world_progress.record_boss_defeat(boss_id, self.level_result)
        else:
            self.world_progress.record(self.level_result)
        self._mark_save_dirty()
        self._autosave()
        self.gameplay_phase = GameplayPhase.COMPLETION_SEQUENCE
        self.completion_timer = LEVEL_COMPLETION_SEQUENCE_DURATION
        self.projectiles.clear()
        self.player.velocity.update()
        self.assets.sound("sounds/level_complete.wav").play()
        self.effects.request_shake(4.0, 0.2)
        self.effects.spawn("world_complete" if exit_id == "ashen_warden" else "route_unlocked", (self.canvas.get_width()/2, self.canvas.get_height()/2))

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
            self.effects.draw_screen(self.canvas)
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
        if self.boss_system is None:
            self.goal.draw(self.canvas, offset)
        else:
            self.boss_system.draw(self.canvas, offset)
        self.secrets.draw(self.canvas, self.camera.view_rect, offset)
        self.collectibles.draw(self.canvas, self.camera.view_rect, offset)
        self.powerup_pickups.draw(self.canvas, self.camera.view_rect, offset)
        self.enemies.draw(self.canvas, self.camera.view_rect, offset)
        if self.powerups.has(PowerUpType.STONE_GUARD):
            pygame.draw.circle(self.canvas, (185, 213, 235), self.player.rect.move(offset).center, 42, 3)
        self.player.draw(self.canvas, offset)
        self.effects.draw_world(self.canvas, offset, self.camera.view_rect)
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
        self.effects.draw_screen(self.canvas)
        if self.boss_system is not None:
            self.boss_hud.draw(self.canvas, self.boss_system.hud_state)
        if DEBUG_MODE:
            self.debug_overlay.draw(self.canvas, self.player, self.effects)
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

    def _configure_level_effects(self) -> None:
        theme = self.level.metadata.theme.lower()
        effect_id = "sanctum_motes" if self.level.boss_encounter else ("ravine_embers" if "ravine" in theme or "lava" in theme else "ruins_dust" if "ruin" in theme else "drifting_leaves")
        bounds = pygame.Rect(0, 0, self.level.tilemap.pixel_width, self.level.tilemap.pixel_height)
        self.effects.start_emitter(f"ambient:{self.level.metadata.level_id}", effect_id, (0, 0), region=bounds)
        if effect_id == "drifting_leaves": self.effects.start_emitter(f"ambient:{self.level.metadata.level_id}:pollen", "pollen_motes", (0, 0), region=bounds)

    def _configure_map_effects(self) -> None:
        self.effects.start_emitter("map:sanctum", "sanctum_available", (1080, 500))

    def _reset_transient_effects(self) -> None:
        quality = self.effects.quality
        self.effects.clear(); self.effects.quality = quality
        self._configure_level_effects()
        for checkpoint in self.world_objects.checkpoints:
            if checkpoint.active: self.effects.start_emitter(f"checkpoint:{checkpoint.object_id}", "checkpoint_idle", checkpoint.rect.center)

    def _drain_combat_effects(self, legacy: list[object], boss: bool = False) -> None:
        for effect in legacy:
            strong = bool(getattr(effect, "strong", False))
            if boss:
                effect_id = "warden_defeat" if strong else "warden_core_hit"
            elif effect.color[2] > effect.color[0]:
                effect_id = "armored_stomp_block"
            else:
                effect_id = "enemy_defeat" if strong else "enemy_hit"
                if strong and effect.color[1] >= 180: self.effects.spawn("stomp_impact", effect.position)
            self.effects.spawn(effect_id, effect.position)
        legacy.clear()

    def _emit_boss_effects(self, result: object) -> None:
        if result.triggered: self.effects.spawn("warden_awaken", self.boss_system.boss.rect.center)
        mapping = {"phase":"warden_phase_three" if self.boss_system.boss.phase >= 3 else "warden_phase_two", "slam":"warden_ground_slam", "projectile":"warden_bolt_launch", "hurt":"warden_core_hit", "defeat":"warden_defeat"}
        for hook in result.audio_events:
            effect_id = mapping.get(hook)
            if effect_id: self.effects.spawn(effect_id, self.boss_system.boss.rect.center)
        owner = "boss:warden:vulnerable"
        if self.boss_system.boss.vulnerable:
            if owner not in self.effects.emitters: self.effects.start_emitter(owner, "warden_core_vulnerable", self.boss_system.boss.rect.center)
            self.effects.update_emitter_position(owner, self.boss_system.boss.rect.center)
        else: self.effects.stop_emitter(owner)

    def _update_effects(self, dt: float) -> None:
        for event in self.projectiles.consume_effect_events():
            self.effects.spawn(event.effect_id, event.position)
        self._effect_trail_timer -= dt
        if self._effect_trail_timer <= 0:
            for projectile in self.projectiles.projectiles:
                if projectile.faction.value == "player": self.effects.spawn("ember_pulse_trail", projectile.rect.center)
            if self.powerups.has(PowerUpType.WIND_BOOTS) and abs(self.player.velocity.x) > 80: self.effects.spawn("wind_boots_trail", self.player.rect.midbottom)
            self._effect_trail_timer = .05
        self.effects.update(dt, self.camera.view_rect)
        self.effects.apply_shake(self.camera)

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
        self.effects.clear()
        self._configure_map_effects()
        if self.level_result is not None:
            center = (self.canvas.get_width() / 2, self.canvas.get_height() / 2)
            self.effects.spawn("ember_veil_reveal" if self.level_result.exit_type is ExitType.SECRET else "route_unlocked", center)
            if self.world_progress.world_completed_once: self.effects.spawn("world_complete", center)
        self._mark_save_dirty()
        self._autosave()
        if self.level_result is not None:
            self.world_map_screen.notify("PATH OPENED — CHOOSE YOUR NEXT DESTINATION")

    def _mark_save_dirty(self) -> None:
        if self.persistence_enabled and self.save_session is not None:
            self.save_session.dirty = True

    def _autosave(self, force: bool = False) -> None:
        if not self.persistence_enabled or self.save_manager is None or self.save_session is None:
            return
        if not force and not self.save_session.dirty:
            return
        self.save_session.progress = self.world_progress
        self.save_session.current_map_node = self.world_map_runtime.current_node_id
        try:
            self.save_manager.save(self.save_session)
        except OSError:
            LOGGER.exception("Autosave failed; campaign remains active in memory")

    def continue_campaign(self) -> None:
        """Compatibility alias: Continue now returns to the authored World Map."""
        self.return_to_world_map()

    def shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        if self.persistence_enabled and self.save_session is not None:
            self.save_session.dirty = True
            self._autosave(force=True)
        self.running = False
        pygame.quit()
        LOGGER.info("Clean shutdown complete")
