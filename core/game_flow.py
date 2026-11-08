"""Application-mode transitions: menus, pause, campaign start/return, level reload, dialogue close, autosave."""

from __future__ import annotations

import logging

from core.save_manager import SaveManager, SlotState
from systems.level_completion import ExitType
from states.world_map import WorldMapScreen
from world.campaign import WorldRegistryError
from world.world_map import WorldMapRuntime

LOGGER = logging.getLogger("core.game")


class GameFlowMixin:
    """Mixin for :class:`core.game.Game`; relies on attributes Game.__init__ creates."""

    def open_achievements(self) -> None:
        self.app_mode = "achievements"
        self.input.suppress_edges()

    def open_pause(self) -> None:
        if self.app_mode == "gameplay":
            self.app_mode = "pause"
            self.pause_controller.dialog = None
            self.input.suppress_edges()

    def resume_game(self) -> None:
        if self.app_mode in {"pause", "settings"}:
            self.app_mode = "gameplay"
            self.input.suppress_edges()

    def restart_from_menu(self) -> None:
        self.reset_level()
        self.app_mode = "gameplay"

    def retry_after_game_over(self) -> None:
        self.reset_level()
        self.app_mode = "gameplay"

    def abandon_to_map(self) -> None:
        self.level_result = None
        self.return_to_world_map()

    def open_settings(self, parent: str) -> None:
        self.settings_parent = parent
        self.app_mode = "settings"
        self.input.suppress_edges()
        self.settings_controller._rebuild()

    def close_settings(self) -> None:
        self.app_mode = self.settings_parent
        self.input.suppress_edges()

    def set_fullscreen(self, enabled: bool) -> None:
        if self.fullscreen != bool(enabled):
            self.toggle_fullscreen()
        self.app_settings.fullscreen = self.fullscreen

    def _activate_world(self, world_id: str) -> None:
        """Point the map, registry, and progress at ``world_id`` and restore its last map node."""
        self.campaign_progress.active_world_id = world_id
        self.registry = self.campaign.world(world_id)
        self.world_progress = self.campaign_progress.active
        self.world_map_runtime = WorldMapRuntime(self.registry.map_definition, self.world_progress)
        saved = self.save_session.map_nodes.get(world_id) if self.save_session is not None else None
        node = self.registry.map_definition.nodes[saved or self.registry.map_definition.start_node]
        self.world_map_runtime.current_node_id = node.node_id
        self.world_map_runtime.avatar_position.update(node.position)
        self.world_map_screen = WorldMapScreen(
            self.world_map_runtime,
            self.assets.font(None, 38),
            self.assets.font(None, 25),
            self.assets.font(None, 19),
            self.input,
        )

    def travel_to_world(self, world_id: str) -> bool:
        """Cross a world gate. Returns False (with feedback) when the destination is still locked."""
        if world_id == self.registry.world_id:
            return False
        try:
            unlocked = self.campaign_progress.world_unlocked(world_id)
        except WorldRegistryError:
            return False
        if not unlocked:
            self.world_map_screen.notify("THE WAY ONWARD IS STILL SEALED")
            self.audio.play_sound("ui_locked")
            return False
        if self.save_session is not None:
            self.save_session.current_map_node = self.world_map_runtime.current_node_id
        self.campaign_progress.set_active_world(world_id)
        self._activate_world(world_id)
        self.app_mode = "map"
        self.show_world_summary = False
        self.input.suppress_edges()
        self.effects.clear()
        self._configure_map_effects()
        self._configure_map_audio()
        self.effects.spawn("route_unlocked", self.world_map_runtime.avatar_position)
        self.audio.play_sound("route_unlock")
        self.world_map_screen.notify(f"WELCOME TO {self.registry.display_name.upper()}")
        self._mark_save_dirty()
        self._autosave()
        return True

    def start_campaign(self, slot_id: int, new_game: bool = False) -> None:
        if self.save_manager is None:
            self.save_manager = SaveManager(self.campaign)
        if new_game:
            self.save_session = self.save_manager.new_game(slot_id, overwrite=True)
        else:
            outcome = self.save_manager.load(slot_id)
            if outcome.session is None:
                return
            self.save_session = outcome.session
            self.save_warning = "SAVE RECOVERED FROM BACKUP" if outcome.state is SlotState.RECOVERED else ""
        self.persistence_enabled = True
        self.campaign_progress = self.save_session.campaign_progress
        self._activate_world(self.campaign_progress.active_world_id)
        if self.save_warning:
            self.world_map_screen.notify(self.save_warning)
        self.app_mode = "map"
        self.input.suppress_edges()
        self.show_world_summary = False
        self.effects.clear()
        self._configure_map_effects()
        self._configure_map_audio()

    def return_to_main_menu(self) -> None:
        self._close_dialogue()
        self.achievements.flush()
        self._autosave(force=True)
        self.app_mode = "frontend"
        self.input.suppress_edges()
        self.effects.clear()
        self.effects.start_emitter("frontend:title", "sanctum_available", (640, 500))
        self.audio.reset_context()
        self.audio.play_music("music_world_map")
        self.frontend.refresh_slots()
        self.frontend._main()

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
        self.input.suppress_edges()
        self.level_path = self.registry.level_paths[level_id]
        self.reset_level()

    def return_to_world_map(self) -> None:
        self._close_dialogue()
        level_id = self.level.metadata.level_id
        self.world_map_runtime.return_to_level_node(level_id)
        self.app_mode = "map"
        self.input.suppress_edges()
        self.show_world_summary = False
        self.effects.clear()
        self._configure_map_effects()
        self._configure_map_audio()
        if self.level_result is not None:
            center = (self.canvas.get_width() / 2, self.canvas.get_height() / 2)
            self.effects.spawn(
                "ember_veil_reveal" if self.level_result.exit_type is ExitType.SECRET else "route_unlocked", center
            )
            if self.level_result.exit_type is ExitType.SECRET:
                self.audio.play_sound("ember_veil_reveal")
            else:
                self.audio.play_sound("route_unlock")
            if self.world_progress.world_completed_once:
                self.effects.spawn("world_complete", center)
                self.audio.play_music("music_world_complete")
                self.audio.play_sound("world_complete")
        self._mark_save_dirty()
        self._autosave()
        if self.level_result is not None:
            self.world_map_screen.notify("PATH OPENED — CHOOSE YOUR NEXT DESTINATION")

    def _close_dialogue(self) -> None:
        dialogue = getattr(self, "dialogue", None)
        if dialogue is not None and dialogue.active:
            dialogue.close()
        npcs = getattr(self, "npcs", None)
        if npcs is not None:
            npcs.end()

    def _commit_dialogue_flag(self, flag: str) -> None:
        """Persist semantic story flags immediately when authored dialogue grants one."""
        self._mark_save_dirty()
        self._autosave()

    def _mark_save_dirty(self) -> None:
        if self.persistence_enabled and self.save_session is not None:
            self.save_session.dirty = True

    def _autosave(self, force: bool = False) -> None:
        if self.debug.enabled:
            return
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
