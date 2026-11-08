"""Top-level game lifecycle and fixed-resolution rendering."""

from __future__ import annotations

import logging
import time

import pygame

from core.asset_manager import AssetManager
from core.achievement_manager import AchievementManager
from core.audio_manager import AudioManager
from core.input_manager import Action, InputManager
from core.save_manager import SaveManager, SlotState
from core.settings_manager import SettingsManager
from core.debug_manager import DebugManager
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
from systems.dialogue_system import DialogueSystem
from systems.npc_system import NPCSystem
from settings import (
    DISPLAY,
    EFFECT_PARTICLE_CAP,
    GAME_TITLE,
    LEVEL_COMPLETION_SEQUENCE_DURATION,
    PROJECT_ROOT,
    SHOW_FPS,
)
from states.level_complete import LevelCompleteScreen
from states.frontend import FrontendController
from states.settings_menu import SettingsController
from states.pause_menu import GameOverController, PauseController
from ui.menu import menu_action_from_input
from states.world_complete import WorldCompleteScreen
from states.world_map import WorldMapScreen
from ui.hud import HUD
from ui.boss_hud import BossHUD
from ui.achievement_screen import AchievementScreen
from ui.achievement_toast import AchievementToastQueue
from ui.notifications import NotificationQueue
from ui.dialogue_box import DialogueBox
from world.background import ParallaxBackground
from world.themes import level_theme
from world.camera import Camera
from world.collision import CollisionEngine
from world.level import Level
from world.ember_current import EmberCurrentSystem
from world.campaign import DEFAULT_WORLD_REGISTRY, WorldProgress, WorldRegistry
from world.world_map import WorldMapRuntime
from core.game_feedback import GameFeedbackMixin
from core.game_flow import GameFlowMixin

LOGGER = logging.getLogger(__name__)


class Game(GameFlowMixin, GameFeedbackMixin):
    """Own Pygame initialization, the main loop, display scaling, and shutdown."""

    def __init__(
        self,
        level_id: str = "verdant_01",
        registry: WorldRegistry | None = None,
        start_on_map: bool = False,
        start_frontend: bool = False,
        save_manager: SaveManager | None = None,
        slot_id: int = 1,
        new_game: bool = False,
        persistence: bool = False,
        audio_manager: AudioManager | None = None,
        settings_manager: SettingsManager | None = None,
        input_manager: InputManager | None = None,
        achievement_manager: AchievementManager | None = None,
        achievements_enabled: bool | None = None,
        debug_enabled: bool = False,
    ) -> None:
        pygame.init()
        pygame.display.set_caption(GAME_TITLE)
        self.input = input_manager or InputManager()
        self.settings_manager = settings_manager or SettingsManager()
        self.app_settings = self.settings_manager.load()
        self.fullscreen = self.app_settings.fullscreen
        self.screen = self._create_display()
        self.canvas = pygame.Surface(DISPLAY.internal_size).convert()
        self.clock = pygame.time.Clock()
        self.assets = AssetManager()
        self.audio = audio_manager or AudioManager(settings=self.app_settings.audio)
        achievement_enabled = (start_frontend or persistence) if achievements_enabled is None else achievements_enabled
        profile_path = None
        if save_manager is not None:
            profile_path = save_manager.save_root.parent / "achievements.json"
        elif settings_manager is not None:
            profile_path = settings_manager.path.parent / "achievements.json"
        self.achievements = achievement_manager or AchievementManager.create(
            PROJECT_ROOT / "data" / "achievements" / "achievements.json",
            profile_path=profile_path,
            enabled=achievement_enabled,
        )
        self.achievement_screen = AchievementScreen(
            self.achievements, self.assets.font(None, 42), self.assets.font(None, 25), self.assets.font(None, 19)
        )
        self.achievement_toasts = AchievementToastQueue(self.assets.font(None, 28), self.assets.font(None, 18))
        self.running = True
        self._shutdown = False
        self._fps_font = self.assets.font(None, 24)
        self.debug = DebugManager(debug_enabled, self.assets.font(None, 21), self.assets.font(None, 17))
        self._debug_update_ms = 0.0
        self._debug_render_ms = 0.0
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
        self.dialogue_box = DialogueBox(
            self.assets.font(None, 30), self.assets.font(None, 26), self.assets.font(None, 21)
        )
        self.effects = EffectsSystem(
            capacity=EFFECT_PARTICLE_CAP, quality=EffectQuality(self.app_settings.effects_quality)
        )
        self._effect_trail_timer = 0.0
        self.world_complete_screen = WorldCompleteScreen(
            self.assets.font(None, 44), self.assets.font(None, 29), self.assets.font(None, 22)
        )
        self.registry = registry or WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
        if level_id not in self.registry.level_paths:
            raise ValueError(f"unknown registered level: {level_id}")
        self.persistence_enabled = persistence
        self.save_manager = save_manager or (SaveManager(self.registry) if persistence or start_frontend else None)
        self.save_session: SaveSession | None = None
        self.save_warning = ""
        if persistence and not start_frontend and self.save_manager is not None:
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
            self.world_map_runtime,
            self.assets.font(None, 38),
            self.assets.font(None, 25),
            self.assets.font(None, 19),
            self.input,
        )
        if self.save_warning:
            self.world_map_screen.notify(self.save_warning)
        self.show_world_summary = False
        self.frontend = FrontendController(
            self,
            self.save_manager or SaveManager(self.registry),
            self.assets.font(None, 48),
            self.assets.font(None, 29),
            self.assets.font(None, 20),
            self.audio,
        )
        self.settings_parent = "frontend"
        self.settings_controller = SettingsController(
            self,
            self.settings_manager,
            self.app_settings,
            self.audio,
            self.effects,
            self.assets.font(None, 44),
            self.assets.font(None, 27),
            self.assets.font(None, 19),
        )
        self.pause_controller = PauseController(
            self, self.assets.font(None, 46), self.assets.font(None, 29), self.assets.font(None, 20), self.audio
        )
        self.game_over_controller = GameOverController(
            self, self.assets.font(None, 48), self.assets.font(None, 29), self.assets.font(None, 20), self.audio
        )
        self.app_mode = "frontend" if start_frontend else "map" if start_on_map else "gameplay"
        self.level_path = self.registry.level_paths[level_id]
        if start_frontend:
            self.effects.clear()
            self.effects.start_emitter("frontend:title", "sanctum_available", (640, 500))
            self.audio.play_music("music_world_map")
        elif not start_on_map:
            self._load_level_runtime()
        else:
            self._configure_map_effects()
            self._configure_map_audio()
        self._jump_pressed = False
        self._jump_released = False
        self._attack_pressed = False
        LOGGER.info("Initialized %s at %sx%s", GAME_TITLE, *DISPLAY.internal_size)

    def _load_level_runtime(self) -> None:
        self.effects.clear()
        self.level = Level.load(self.level_path)
        self.collision = CollisionEngine(self.level.tilemap)
        self.ember_currents = EmberCurrentSystem(self.level.ember_currents)
        self.player = Player(self.level.player_spawn)
        world_size = (self.level.tilemap.pixel_width, self.level.tilemap.pixel_height)
        self.camera = Camera(DISPLAY.internal_size, world_size)
        self.camera.snap_to(self.player.rect)
        self.background = ParallaxBackground(*world_size, palette=level_theme(self.level.metadata.theme).background)
        self.progress = LevelProgress.from_types([spawn.kind for spawn in self.level.collectible_spawns])
        self.collectibles = CollectibleManager(self.level.collectible_spawns)
        self.projectiles = ProjectileManager()
        self.enemies = EnemyManager(self.level.enemy_spawns, self.projectiles)
        self.player_combat = PlayerCombatController()
        self.powerups = PowerUpSystem(self.player)
        self.powerup_pickups = PowerUpManager(self.level.powerup_spawns)
        self.world_objects = WorldObjectManager(self.level.world_object_spawns, self.level.player_spawn)
        self.boss_system = (
            BossSystem(self.level.boss_encounter, self.world_objects.doors, self.projectiles)
            if self.level.boss_encounter is not None
            else None
        )
        self.secrets = SecretSystem(self.level.secret_definitions)
        self.goal = EmberGate(self.level.goal.position, self.level.goal.requires_interact)
        self.npcs, dialogue_definitions = NPCSystem.load(
            PROJECT_ROOT / "data", self.level.metadata.level_id, self.world_progress, world_size
        )
        self.dialogue = DialogueSystem(dialogue_definitions, self.world_progress, self._commit_dialogue_flag)
        self.gameplay_phase = GameplayPhase.PLAYING
        self.elapsed_time = 0.0
        self.deaths = 0
        self.damage_taken_this_attempt = False
        self.completion_timer = 0.0
        self.level_result: LevelResult | None = None
        self.level_complete_screen.reset()
        self.achievement_toasts.clear()
        self._interact_pressed = False
        self._configure_level_effects()
        self._configure_level_audio()

    def _create_display(self) -> pygame.Surface:
        if self.fullscreen:
            return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        flags = pygame.RESIZABLE if DISPLAY.resizable else 0
        return pygame.display.set_mode(DISPLAY.window_size, flags)

    def run(self, frame_limit: int | None = None) -> None:
        frames = 0
        try:
            while self.running and (frame_limit is None or frames < frame_limit):
                frame_started = time.perf_counter()
                dt = min(self.clock.tick(DISPLAY.target_fps) / 1000.0, 0.05)
                self.input.begin_frame(dt)
                self._handle_events()
                update_started = time.perf_counter()
                self.update(self.debug.simulation_dt(dt))
                self._debug_update_ms = (time.perf_counter() - update_started) * 1000.0
                render_started = time.perf_counter()
                self.draw()
                self._debug_render_ms = (time.perf_counter() - render_started) * 1000.0
                if self.debug.enabled:
                    frame_ms = (time.perf_counter() - frame_started) * 1000.0
                    context = f"{self.app_mode}:{getattr(getattr(self, 'gameplay_phase', None), 'value', '-')}"
                    self.debug.profiler.record("update", self._debug_update_ms, context)
                    self.debug.profiler.record("render", self._debug_render_ms, context)
                    self.debug.profiler.record("frame", frame_ms, context)
                frames += 1
        finally:
            self.shutdown()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif self.debug.handle_event(event, self):
                continue
            else:
                self.input.process_event(event)
        self._dispatch_input()

    def _dispatch_input(self) -> None:
        menu_order = (
            Action.MENU_UP,
            Action.MENU_DOWN,
            Action.MENU_LEFT,
            Action.MENU_RIGHT,
            Action.CONFIRM,
            Action.BACK,
            Action.PAUSE,
        )
        if self.app_mode == "achievements":
            for action in (Action.MENU_UP, Action.MENU_DOWN, Action.MENU_LEFT, Action.MENU_RIGHT, Action.BACK):
                if self.input.was_pressed(action):
                    outcome = self.achievement_screen.handle(action)
                    self.audio.play_sound("ui_cancel" if outcome == "back" else "ui_move")
                    if outcome == "back":
                        self.app_mode = "frontend"
                        self.input.suppress_edges()
                    break
            return
        if self.app_mode == "dialogue":
            for action in (Action.MENU_UP, Action.MENU_DOWN, Action.CONFIRM, Action.BACK):
                if self.input.was_pressed(action):
                    active_npc = self.npcs.active_npc
                    outcome = self.dialogue.handle(action)
                    if outcome == "close" and self.dialogue.completed_dialogue and active_npc is not None:
                        self._emit_achievement("npc_conversation_completed", npc_id=active_npc.display_name.lower())
                    sound = {"move": "ui_move", "close": "ui_cancel"}.get(outcome, "ui_confirm")
                    if outcome != "none":
                        self.audio.play_sound(sound)
                    if not self.dialogue.active:
                        self.npcs.end()
                        self.app_mode = "gameplay"
                        self.input.suppress_edges()
                    break
            return
        if self.app_mode in {"pause", "game_over", "settings", "frontend"}:
            controller = {
                "pause": self.pause_controller,
                "game_over": self.game_over_controller,
                "settings": self.settings_controller,
                "frontend": self.frontend,
            }[self.app_mode]
            for action in menu_order:
                if self.input.was_pressed(action):
                    mapped = menu_action_from_input(action)
                    if mapped is not None:
                        controller.handle(mapped)
                    break
            return
        if self.app_mode == "map":
            self._handle_map_actions()
            return
        if self.input.was_pressed(Action.PAUSE) or self.input.was_pressed(Action.BACK):
            self.open_pause()
            return
        if self.gameplay_phase is GameplayPhase.LEVEL_COMPLETE:
            if self.input.was_pressed(Action.ATTACK):
                self.reset_level()
            elif self.input.was_pressed(Action.CONFIRM) or self.input.was_pressed(Action.BACK):
                self.return_to_world_map()
            return
        if self.debug.palette_open:
            return
        if self.input.was_pressed(Action.ATTACK):
            self._attack_pressed = True
        if self.input.was_pressed(Action.INTERACT):
            self._interact_pressed = True
        if self.input.was_pressed(Action.CONFIRM) and self.boss_system and self.boss_system.active:
            self.boss_system.skip_intro()
        if self.input.was_pressed(Action.JUMP):
            self._jump_pressed = True
        if self.input.was_released(Action.JUMP):
            self._jump_released = True

    def _handle_map_actions(self) -> None:
        if self.show_world_summary:
            if any(self.input.was_pressed(x) for x in (Action.CONFIRM, Action.BACK)):
                self.show_world_summary = False
                self.input.suppress_edges()
            return
        directions = (
            (Action.MENU_LEFT, (-1, 0)),
            (Action.MENU_RIGHT, (1, 0)),
            (Action.MENU_UP, (0, -1)),
            (Action.MENU_DOWN, (0, 1)),
        )
        for action, direction in directions:
            if self.input.was_pressed(action):
                moved = self.world_map_runtime.choose_direction(pygame.Vector2(direction))
                self.audio.play_sound("ui_move" if moved else "ui_locked")
                return
        if self.input.was_pressed(Action.CONFIRM):
            action, level_id = self.world_map_screen.activate_current()
            self.audio.play_sound("ui_confirm" if action in {"level", "world_summary"} else "ui_locked")
            if action == "level" and level_id:
                self.load_level(level_id)
            elif action == "world_summary":
                self.show_world_summary = True
                self.input.suppress_edges()
        elif self.input.was_pressed(Action.BACK):
            self.audio.play_sound("ui_cancel")
            self.return_to_main_menu()

    def _handle_map_key(self, key: int) -> None:
        """Compatibility helper for older integration tests; runtime uses logical actions."""
        directions = {
            pygame.K_LEFT: (-1, 0),
            pygame.K_a: (-1, 0),
            pygame.K_RIGHT: (1, 0),
            pygame.K_d: (1, 0),
            pygame.K_UP: (0, -1),
            pygame.K_w: (0, -1),
            pygame.K_DOWN: (0, 1),
            pygame.K_s: (0, 1),
        }
        if key in directions:
            moved = self.world_map_runtime.choose_direction(pygame.Vector2(directions[key]))
            self.audio.play_sound("ui_move" if moved else "ui_locked")
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            action, level_id = self.world_map_screen.activate_current()
            self.audio.play_sound("ui_confirm" if action in {"level", "world_summary"} else "ui_locked")
            if action == "level" and level_id:
                self.load_level(level_id)
            elif action == "world_summary":
                self.show_world_summary = True
        elif key == pygame.K_ESCAPE:
            self.audio.play_sound("ui_cancel")
            self.return_to_main_menu()

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        self.screen = self._create_display()
        self.app_settings.fullscreen = self.fullscreen
        LOGGER.info("Fullscreen: %s", self.fullscreen)

    def update(self, dt: float) -> None:
        """Advance one frame. Non-gameplay modes short-circuit; gameplay runs fixed ordered steps."""
        if self._update_non_gameplay_mode(dt):
            return
        if self._update_completion_phases(dt):
            return
        self._update_gameplay(dt)

    def _update_non_gameplay_mode(self, dt: float) -> bool:
        """Handle debug pause, menus, dialogue, and the World Map. Returns True when the frame is consumed."""
        if self.debug.enabled and self.debug.simulation_paused and dt <= 0 and self.app_mode == "gameplay":
            self.debug.update_free_camera(self, 1.0 / DISPLAY.target_fps)
            self.audio.update(0.0)
            self._clear_frame_inputs()
            return True
        if self.app_mode in {"pause", "game_over"}:
            self.audio.update(dt)
            self._clear_frame_inputs()
            return True
        if self.app_mode == "settings":
            self.audio.update(dt)
            return True
        if self.app_mode == "achievements":
            self.audio.update(dt)
            return True
        if self.app_mode == "frontend":
            self.frontend.update(dt)
            self.effects.update(dt)
            self.audio.update(dt)
            return True
        if self.app_mode == "dialogue":
            self.dialogue.update(dt)
            self.audio.update(dt)
            self._clear_frame_inputs()
            return True
        if self.save_session is not None:
            self.save_session.play_time_seconds += dt
        if self.app_mode == "map":
            previous_node = self.world_map_runtime.current_node_id
            self.world_map_screen.update(dt)
            self.effects.update(dt)
            self.achievement_toasts.update(dt)
            self.audio.update(dt)
            if self.world_map_runtime.current_node_id != previous_node:
                self.effects.spawn("route_unlocked", self.world_map_runtime.avatar_position)
                self._mark_save_dirty()
                self._autosave()
            return True
        return False

    def _update_completion_phases(self, dt: float) -> bool:
        """Freeze gameplay during level/world completion screens and the completion sequence."""
        if self.gameplay_phase in {GameplayPhase.LEVEL_COMPLETE, GameplayPhase.WORLD_COMPLETE}:
            self.achievement_toasts.update(dt)
            self.audio.update(dt)
            self._clear_frame_inputs()
            return True
        if self.gameplay_phase is GameplayPhase.COMPLETION_SEQUENCE:
            self.completion_timer = max(0.0, self.completion_timer - dt)
            self.goal.update(dt, self.player.rect)
            self.camera.update(self.player.rect, pygame.Vector2(), dt)
            self.hud.update(dt)
            self.effects.update(dt, self.camera.view_rect)
            self.audio.update(dt)
            self.effects.apply_shake(self.camera)
            if self.completion_timer <= 0.0:
                self.gameplay_phase = GameplayPhase.LEVEL_COMPLETE
            self._clear_frame_inputs()
            return True
        return False

    def _update_gameplay(self, dt: float) -> None:
        """Run one gameplay frame. Step order is significant and matches the original monolithic update."""
        self.elapsed_time += dt
        if self.debug.enabled and self.debug.god_mode:
            self.player.invulnerability_timer = max(self.player.invulnerability_timer, 0.1)
        self.debug.update_free_camera(self, dt)
        world_interacted = self._update_world_and_player(dt)
        if self._update_player_damage_and_lives():
            return
        self.camera.update(self.player.rect, self.player.velocity, dt)
        self._update_enemies(dt)
        self._update_boss(dt)
        self._update_pickups(dt)
        self._handle_powerup_events()
        secret_update = self._update_secrets(world_interacted)
        self.notifications.update(dt)
        self.goal.update(dt, self.player.rect)
        self._update_goal_and_npcs(world_interacted, secret_update)
        self.hud.update(dt)
        self._update_effects(dt)
        if self.app_mode != "dialogue":
            self.achievement_toasts.update(dt)
        self._clear_frame_inputs()

    def _update_world_and_player(self, dt: float) -> bool:
        """Power-ups, platforms, Nova movement, interactables, NPC proximity, and Ember Pulse firing."""
        controls = PlayerControls(
            move_axis=self.input.axis(Action.MOVE_X),
            jump_pressed=self._jump_pressed,
            jump_held=self.input.is_down(Action.JUMP),
            jump_released=self._jump_released,
        )
        previous_grounded = self.player.grounded
        previous_double_jump_fx = self.player.double_jump_effect_timer
        previous_checkpoints = set(self.world_objects.activated_checkpoint_ids)
        previous_switches = {item.object_id for item in self.world_objects.switches if item.active}
        previous_platform_states = {
            item.object_id: getattr(item, "state", None) for item in self.world_objects.platforms
        }
        self.powerups.update(dt)
        self.world_objects.update_before_player(dt, self.player, self.level.tilemap)
        for platform in self.world_objects.platforms:
            before = previous_platform_states.get(platform.object_id)
            after = getattr(platform, "state", None)
            if before != after and getattr(after, "value", "") == "warning":
                self.audio.play_sound(
                    "platform_warning", position=platform.rect.center, listener_x=self.player.rect.centerx
                )
            if before != after and getattr(after, "value", "") == "falling":
                self.audio.play_sound(
                    "platform_drop", position=platform.rect.center, listener_x=self.player.rect.centerx
                )
        current_force = self.ember_currents.influence(self.player.rect, "player")
        self.player.update(dt, controls, self.collision, self.powerups.movement_modifiers, current_force)
        if previous_grounded and not self.player.grounded and self.player.velocity.y < 0:
            self.effects.spawn("player_jump_dust", self.player.rect.midbottom)
            self.audio.play_sound("player_jump")
        if not previous_grounded and self.player.grounded:
            self.effects.spawn("player_land_dust", self.player.rect.midbottom)
            self.audio.play_sound("player_land")
        if self.player.double_jump_effect_timer > previous_double_jump_fx:
            self.effects.spawn("aether_double_jump", self.player.rect.center)
            self.audio.play_sound("powerup_aether")
        world_interacted = self.world_objects.resolve_after_player(
            self.player, self._interact_pressed, self.level.tilemap
        )
        if world_interacted:
            new_checkpoints = self.world_objects.activated_checkpoint_ids - previous_checkpoints
            for item in self.world_objects.checkpoints:
                if item.object_id in new_checkpoints:
                    self.effects.spawn("checkpoint_activate", item.rect.center)
                    self.audio.play_sound(
                        "checkpoint_activate", position=item.rect.center, listener_x=self.player.rect.centerx
                    )
                    self.effects.start_emitter(f"checkpoint:{item.object_id}", "checkpoint_idle", item.rect.center)
            new_switches = {item.object_id for item in self.world_objects.switches if item.active} - previous_switches
            for item in self.world_objects.switches:
                if item.object_id in new_switches:
                    self.effects.spawn("switch_activate", item.rect.center)
                    self.audio.play_sound(
                        "switch_activate", position=item.rect.center, listener_x=self.player.rect.centerx
                    )
            for door in self.world_objects.doors:
                if any(
                    door.object_id in switch.target_ids
                    for switch in self.world_objects.switches
                    if switch.object_id in new_switches
                ):
                    self.effects.spawn("door_open", door.rect.center)
                    self.audio.play_sound("door_open", position=door.rect.center, listener_x=self.player.rect.centerx)
        self.npcs.update(dt, self.player.rect)
        self.player_combat.ember_pulse_enabled = self.powerups.grants_ranged_attack
        self.player_combat.update(dt)
        if self._attack_pressed and self.player_combat.try_attack(self.player, self.projectiles):
            self.audio.play_sound(
                "ember_pulse_fire", position=self.player.rect.center, listener_x=self.player.rect.centerx
            )
            self.effects.spawn("ember_pulse_launch", self.player.rect.center)
        return world_interacted

    def _update_player_damage_and_lives(self) -> bool:
        """Apply hazard damage and life loss. Returns True when Game Over begins (frame ends early)."""
        if self.player.hit_hazard and not self.player.is_dead:
            damage = self.player.apply_damage(1, DamageSource.HAZARD)
            if damage.applied:
                self.damage_taken_this_attempt = True
                self.hud.notify_health_changed()
                self.effects.request_shake(8.0, 0.18)
                self.effects.spawn("player_death" if damage.died else "player_damage", self.player.rect.center)
                self.effects.request_flash((142, 42, 37), 68, 0.16)
                self.audio.play_sound("player_death" if damage.died else "player_damage")
                self._rumble(0.25, 0.55, 140 if not damage.died else 240)
            if damage.applied and not damage.died:
                self.player.reposition(self.world_objects.respawn_position)
                self.camera.snap_to(self.player.rect)
        if self.player.death_animation_finished:
            self.deaths += 1
            self.player.lose_life_and_restore()
            self.powerups.clear("life_lost")
            if self.player.lives <= 0:
                self.projectiles.clear()
                if self.boss_system is not None:
                    self.boss_system.reset_encounter(self.powerups)
                    self.camera.set_bounds(None)
                self.effects.clear()
                self.audio.reset_context()
                self.audio.stop_music(0.5)
                self.app_mode = "game_over"
                self.input.suppress_edges()
                self._clear_frame_inputs()
                return True
            if self.boss_system is not None:
                self.boss_system.reset_encounter(self.powerups)
                self.camera.set_bounds(None)
            self._configure_level_audio()
            self.player.respawn(self.world_objects.respawn_position)
            self.camera.snap_to(self.player.rect)
            self._reset_transient_effects()
        return False

    def _update_enemies(self, dt: float) -> None:
        prior_projectiles = {item.projectile_id for item in self.projectiles.projectiles}
        enemy_result = self.enemies.update(
            dt,
            self.camera.view_rect,
            self.player,
            self.collision,
            self.level.tilemap,
            self.progress,
            self.ember_currents,
        )
        for projectile in self.projectiles.projectiles:
            if (
                projectile.projectile_id not in prior_projectiles
                and projectile.faction.value == "enemy"
                and not (self.boss_system is not None and projectile.owner_id == self.boss_system.boss.boss_id)
            ):
                self.audio.play_sound(
                    "turret_fire", position=projectile.rect.center, listener_x=self.player.rect.centerx
                )
        for enemy_id, method in enemy_result.defeated:
            self._emit_achievement("enemy_defeated", enemy_id=enemy_id, method=method)
        if enemy_result.player_damaged:
            self.damage_taken_this_attempt = True
            self.hud.notify_health_changed()
            self._rumble(0.22, 0.52, 140)
            self.audio.play_sound("player_death" if enemy_result.player_died else "player_damage")
            self.effects.spawn("player_death" if enemy_result.player_died else "player_damage", self.player.rect.center)
            self.effects.request_flash((142, 42, 37), 62, 0.14)
        if enemy_result.score_awarded:
            self.hud.notify_score_changed()
        if enemy_result.shake:
            self.effects.request_shake(enemy_result.shake, 0.12)
        self._drain_combat_effects(self.enemies.effects)

    def _update_boss(self, dt: float) -> None:
        if self.boss_system is None:
            return
        boss_result = self.boss_system.update(dt, self.player, self.powerups, self.progress)
        self.camera.set_bounds(self.boss_system.arena.camera_bounds)
        if self.boss_system.active:
            focus = self.player.rect.union(self.boss_system.boss.rect)
            if boss_result.triggered:
                self.camera.snap_to(focus)
            else:
                self.camera.update(focus, pygame.Vector2(), dt)
        if boss_result.player_damaged:
            self.damage_taken_this_attempt = True
            self.hud.notify_health_changed()
            self._rumble(0.3, 0.62, 180)
        if boss_result.score_awarded:
            self.hud.notify_score_changed()
        if boss_result.shake:
            self.effects.request_shake(boss_result.shake, 0.25)
        self._emit_boss_effects(boss_result)
        self._drain_combat_effects(self.boss_system.effects, boss=True)
        self._emit_boss_audio(boss_result)
        if boss_result.defeat_sequence_complete:
            boss_id = self.boss_system.boss.boss_id
            self._begin_completion(boss_id, ExitType.NORMAL, boss_id=boss_id)

    def _update_pickups(self, dt: float) -> None:
        self.collectibles.update(dt, self.camera.view_rect)
        self.powerup_pickups.update(dt, self.camera.view_rect)
        if not self.player.is_dead:
            for result in self.collectibles.collect_overlaps(
                self.player.rect,
                self.player,
                self.progress,
            ):
                event_name = {
                    "ember_shard": "ember_shard_collected",
                    "rare_crystal": "rare_crystal_collected",
                    "secret_token": "secret_token_collected",
                }.get(result.kind.value)
                if event_name:
                    self._emit_achievement(event_name, collectible_id=result.collectible_id)
                collectible_audio = {
                    "ember_shard": "ember_shard",
                    "rare_crystal": "rare_crystal",
                    "secret_token": "secret_token",
                    "health_item": "player_land",
                }[result.kind.value]
                self.audio.play_sound(collectible_audio, position=result.position, listener_x=self.player.rect.centerx)
                self.hud.notify_pickup(result)
                pickup_fx = {
                    "ember_shard": "ember_shard_pickup",
                    "rare_crystal": "rare_crystal_pickup",
                    "secret_token": "secret_token_pickup",
                }.get(result.kind.value)
                if pickup_fx:
                    self.effects.spawn(pickup_fx, result.position)
            for kind in self.powerup_pickups.collect_overlaps(self.player.rect, self.powerups):
                power_audio = {
                    PowerUpType.EMBER_PULSE: "powerup_ember",
                    PowerUpType.WIND_BOOTS: "powerup_wind",
                    PowerUpType.AETHER_WING: "powerup_aether",
                    PowerUpType.STONE_GUARD: "powerup_stone",
                }[kind]
                self.audio.play_sound(power_audio)
                pickup_fx = {
                    PowerUpType.EMBER_PULSE: "ember_pulse_pickup",
                    PowerUpType.WIND_BOOTS: "wind_boots_trail",
                    PowerUpType.AETHER_WING: "aether_double_jump",
                    PowerUpType.STONE_GUARD: "stone_guard_activate",
                }[kind]
                self.effects.spawn(pickup_fx, self.player.rect.center)

    def _handle_powerup_events(self) -> None:
        power_event = self.powerups.consume_event()
        if power_event in {"expired", "absorbed"}:
            if power_event == "absorbed":
                self._emit_achievement("stone_guard_absorbed")
                self.effects.spawn("stone_guard_break", self.player.rect.center)
                self.effects.request_flash((170, 196, 218), 58, 0.14)
                self.audio.play_sound("stone_guard_break")
                self._rumble(0.38, 0.68, 180)

    def _update_secrets(self, world_interacted: bool):
        critical_interact = self._interact_pressed and not world_interacted
        previous_secrets = {key for key, area in self.secrets.areas.items() if area.state.value != "undiscovered"}
        secret_update = self.secrets.update(self.player.rect, critical_interact, self.enemies.defeated_ids)
        discovered_now = {
            key for key, area in self.secrets.areas.items() if area.state.value != "undiscovered"
        } - previous_secrets
        for secret_id in sorted(discovered_now):
            self._emit_achievement("secret_discovered", secret_id=secret_id)
        if secret_update.score_awarded:
            self.progress.award_score(secret_update.score_awarded)
            self.hud.notify_score_changed()
        for message in secret_update.messages:
            self.notifications.push(message)
            is_challenge = "CHALLENGE" in message
            self.effects.spawn("challenge_complete" if is_challenge else "secret_discovered", self.player.rect.center)
            self.audio.play_sound("challenge_complete" if is_challenge else "secret_discovered")
        if secret_update.secret_exit_id:
            self._emit_achievement("secret_exit_discovered", exit_id=secret_update.secret_exit_id)
            self.audio.play_sound("secret_exit")
            self._begin_completion(secret_update.secret_exit_id, ExitType.SECRET)
        return secret_update

    def _update_goal_and_npcs(self, world_interacted: bool, secret_update) -> None:
        critical_consumed = world_interacted or bool(secret_update.messages) or bool(secret_update.secret_exit_id)
        goal_activated = False
        if self.boss_system is None and not self.player.is_dead and not critical_consumed:
            goal_activated = self.goal.try_activate(self.player.rect, self._interact_pressed)
            if goal_activated and self.level.metadata.requirements.evaluate(True, self.progress):
                self._begin_completion("ember_gate", ExitType.NORMAL)
        if (
            self.gameplay_phase is GameplayPhase.PLAYING
            and not self.player.is_dead
            and self._interact_pressed
            and not critical_consumed
            and not goal_activated
            and self.npcs.begin(self.player.rect, self.dialogue)
        ):
            self.app_mode = "dialogue"
            self.audio.play_sound("ui_confirm")
            if self.npcs.active_npc is not None:
                self.effects.spawn("switch_activate", self.npcs.active_npc.rect.center)
            self.input.suppress_edges()

    def _clear_frame_inputs(self) -> None:
        self._jump_pressed = False
        self._jump_released = False
        self._attack_pressed = False
        self._interact_pressed = False

    def _begin_completion(
        self, exit_id: str = "ember_gate", exit_type: ExitType = ExitType.NORMAL, boss_id: str | None = None
    ) -> None:
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
        from systems.progression import CollectibleType

        normal_level = exit_type is ExitType.NORMAL and boss_id is None
        self._emit_achievement(
            "level_completed",
            level_id=self.level.metadata.level_id,
            no_damage=normal_level and not self.damage_taken_this_attempt,
            shard_sweep=normal_level
            and self.progress.total(CollectibleType.EMBER_SHARD) > 0
            and self.progress.count(CollectibleType.EMBER_SHARD) == self.progress.total(CollectibleType.EMBER_SHARD),
            normal=normal_level,
        )
        if boss_id is not None:
            self._emit_achievement("boss_defeated", boss_id=boss_id)
        if self.world_progress.world_completed_once:
            self._emit_achievement("world_completed", world_id=self.registry.world_id)
        self.achievements.flush()
        self.gameplay_phase = GameplayPhase.COMPLETION_SEQUENCE
        self.input.suppress_edges()
        self.completion_timer = LEVEL_COMPLETION_SEQUENCE_DURATION
        self.projectiles.clear()
        self.player.velocity.update()
        self.audio.play_sound("level_complete")
        if boss_id is not None:
            self.audio.stop_music(1.0)
            self.audio.play_sound("warden_defeat")
        self.effects.request_shake(4.0, 0.2)
        self.effects.spawn(
            "world_complete" if boss_id is not None else "route_unlocked",
            (self.canvas.get_width() / 2, self.canvas.get_height() / 2),
        )

    def _build_level_result(self, exit_id: str = "ember_gate", exit_type: ExitType = ExitType.NORMAL) -> LevelResult:
        from systems.progression import CollectibleType

        shards = self.progress.count(CollectibleType.EMBER_SHARD)
        rating = calculate_rating(
            self.progress.score,
            shards,
            self.progress.total(CollectibleType.EMBER_SHARD),
            self.elapsed_time,
            self.level.metadata.ratings,
        )
        return LevelResult(
            level_id=self.level.metadata.level_id,
            completed=True,
            completion_time=self.elapsed_time,
            score=self.progress.score,
            ember_shards_collected=shards,
            ember_shards_total=self.progress.total(CollectibleType.EMBER_SHARD),
            rare_crystals_collected=self.progress.count(CollectibleType.RARE_CRYSTAL),
            rare_crystals_total=self.progress.total(CollectibleType.RARE_CRYSTAL),
            secret_tokens_collected=self.progress.count(CollectibleType.SECRET_TOKEN),
            secret_tokens_total=self.progress.total(CollectibleType.SECRET_TOKEN),
            enemies_defeated=len(self.enemies.defeated_ids),
            enemies_total=len(self.level.enemy_spawns),
            deaths=self.deaths,
            lives_remaining=self.player.lives,
            health_remaining=self.player.health,
            checkpoints_activated=len(self.world_objects.activated_checkpoint_ids),
            rating=rating,
            secrets_discovered=self.secrets.discovered_count,
            secrets_total=len(self.level.secret_definitions),
            secret_rooms_completed=self.secrets.completed_room_count,
            exit_type=exit_type,
            exit_id=exit_id,
        )

    def draw(self) -> None:
        if self.app_mode == "settings":
            self.settings_controller.draw(self.canvas)
            self._draw_debug_layer()
            self._present()
            return
        if self.app_mode == "achievements":
            self.achievement_screen.draw(self.canvas, self.input)
            self._draw_debug_layer()
            self._present()
            return
        if self.app_mode == "frontend":
            self.frontend.draw(self.canvas)
            self.effects.draw_screen(self.canvas)
            self._draw_debug_layer()
            self._present()
            return
        if self.app_mode == "map":
            self.world_map_screen.draw(self.canvas)
            self.effects.draw_screen(self.canvas)
            if self.show_world_summary:
                self.world_complete_screen.draw(self.canvas, self.world_progress, self.input)
            self.achievement_toasts.draw(self.canvas)
            self._draw_debug_layer()
            self._present()
            return
        self.background.draw(self.canvas, self.camera.position)
        view = self.debug.view_rect(self) if self.debug.enabled else self.camera.view_rect
        tile_view = view.inflate(
            self.level.tilemap.tile_size * 2,
            self.level.tilemap.tile_size * 2,
        )
        offset = self.debug.render_offset(self) if self.debug.enabled else self.camera.render_offset
        self.level.tilemap.draw(self.canvas, tile_view, offset)
        self.ember_currents.draw(self.canvas, view, offset)
        self.world_objects.draw(self.canvas, view, offset)
        self.npcs.draw(
            self.canvas,
            view,
            offset,
            self.player.rect,
            self.input.get_prompt(Action.INTERACT),
            self._fps_font,
        )
        if self.boss_system is None:
            self.goal.draw(self.canvas, offset, self.input.get_prompt(Action.INTERACT))
        else:
            self.boss_system.draw(self.canvas, offset)
        self.secrets.draw(self.canvas, view, offset)
        self.collectibles.draw(self.canvas, view, offset)
        self.powerup_pickups.draw(self.canvas, view, offset)
        self.enemies.draw(self.canvas, view, offset)
        if self.powerups.has(PowerUpType.STONE_GUARD):
            pygame.draw.circle(self.canvas, (185, 213, 235), self.player.rect.move(offset).center, 42, 3)
        self.player.draw(self.canvas, offset)
        self.effects.draw_world(self.canvas, offset, view)
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
        self._draw_debug_layer()
        if SHOW_FPS:
            label = self._fps_font.render(f"FPS {self.clock.get_fps():.0f}", True, (210, 220, 245))
            position = (self.canvas.get_width() - 16, self.canvas.get_height() - 12)
            self.canvas.blit(label, label.get_rect(bottomright=position))
        if self.gameplay_phase is GameplayPhase.COMPLETION_SEQUENCE:
            fade = pygame.Surface(self.canvas.get_size(), pygame.SRCALPHA)
            fade.fill((255, 183, 78, round(35 * (1.0 - self.completion_timer / LEVEL_COMPLETION_SEQUENCE_DURATION))))
            self.canvas.blit(fade, (0, 0))
        elif self.gameplay_phase is GameplayPhase.LEVEL_COMPLETE and self.level_result:
            self.level_complete_screen.draw(
                self.canvas, self.level.metadata.display_name, self.level_result, self.input
            )
        if self.app_mode != "dialogue" and self.gameplay_phase is not GameplayPhase.COMPLETION_SEQUENCE:
            self.achievement_toasts.draw(self.canvas)
        if self.app_mode == "dialogue":
            self.dialogue_box.draw(self.canvas, self.dialogue, self.input)
        if self.app_mode == "pause":
            self.pause_controller.draw(self.canvas)
        elif self.app_mode == "game_over":
            self.game_over_controller.draw(self.canvas)
        self._present()

    def _present(self) -> None:
        """Scale only when the resizable window differs from the internal canvas."""
        if self.screen.get_size() == self.canvas.get_size():
            self.screen.blit(self.canvas, (0, 0))
        else:
            self.screen.blit(pygame.transform.scale(self.canvas, self.screen.get_size()), (0, 0))
        pygame.display.flip()

    def _draw_debug_layer(self) -> None:
        if not self.debug.enabled:
            return
        fps = self.clock.get_fps()
        perf = {
            "fps": fps,
            "frame_ms": 1000.0 / fps if fps > 0 else 0.0,
            "update_ms": self._debug_update_ms,
            "render_ms": self._debug_render_ms,
        }
        self.debug.capture(self, perf)
        self.debug.draw(self.canvas, self)

    def shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        self.achievements.flush()
        if self.persistence_enabled and self.save_session is not None:
            self.save_session.dirty = True
            self._autosave(force=True)
        if not self.debug.enabled:
            self.settings_manager.save(self.app_settings)
        self.running = False
        self.audio.shutdown()
        pygame.quit()
        LOGGER.info("Clean shutdown complete")
