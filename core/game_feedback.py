"""Audio, rumble, visual-effect, and achievement-event helpers used by Game."""

from __future__ import annotations

import pygame

from systems.powerup_system import PowerUpType
from world.themes import level_theme, map_theme


class GameFeedbackMixin:
    """Mixin for :class:`core.game.Game`; relies on attributes Game.__init__ creates."""

    def _configure_level_audio(self) -> None:
        self.audio.reset_context()
        theme = level_theme(self.level.metadata.theme)
        self.audio.play_music(theme.music)
        self.audio.start_ambience("level", theme.ambience)

    def _configure_map_audio(self) -> None:
        self.audio.reset_context()
        self.audio.play_music("music_world_map")
        self.audio.start_ambience("map", map_theme(self.registry.map_theme).ambience)

    def _emit_boss_audio(self, result: object) -> None:
        mapping = self.boss_system.runtime.audio_events
        if result.triggered:
            self.audio.play_music("music_boss")
        for hook in result.audio_events:
            audio_id = mapping.get(hook)
            if audio_id:
                self.audio.play_sound(
                    audio_id, position=self.boss_system.boss.rect.center, listener_x=self.player.rect.centerx
                )
            if hook in {"ground_slam", "slam"}:
                self._rumble(0.45, 0.7, 190)
            elif hook == "phase":
                self._rumble(0.42, 0.76, 240)
            elif hook == "defeat":
                self._rumble(0.7, 1.0, 320)

    def _rumble(self, low: float, high: float, duration_ms: int) -> bool:
        return bool(self.app_settings.vibration_enabled and self.input.rumble(low, high, duration_ms))

    def _configure_level_effects(self) -> None:
        theme = self.level.metadata.theme.lower()
        effect_id = (
            "sanctum_motes"
            if self.level.boss_encounter
            else (
                "ravine_embers"
                if "ravine" in theme or "lava" in theme
                else "ruins_dust"
                if "ruin" in theme
                else "drifting_leaves"
            )
        )
        bounds = pygame.Rect(0, 0, self.level.tilemap.pixel_width, self.level.tilemap.pixel_height)
        self.effects.start_emitter(f"ambient:{self.level.metadata.level_id}", effect_id, (0, 0), region=bounds)
        if effect_id == "drifting_leaves":
            self.effects.start_emitter(
                f"ambient:{self.level.metadata.level_id}:pollen", "pollen_motes", (0, 0), region=bounds
            )

    def _configure_map_effects(self) -> None:
        self.effects.start_emitter("map:sanctum", "sanctum_available", (1080, 500))

    def _reset_transient_effects(self) -> None:
        quality = self.effects.quality
        self.effects.clear()
        self.effects.quality = quality
        self._configure_level_effects()
        for checkpoint in self.world_objects.checkpoints:
            if checkpoint.active:
                self.effects.start_emitter(
                    f"checkpoint:{checkpoint.object_id}", "checkpoint_idle", checkpoint.rect.center
                )

    def _drain_combat_effects(self, legacy: list[object], boss: bool = False) -> None:
        for effect in legacy:
            strong = bool(getattr(effect, "strong", False))
            if boss:
                effect_id = "warden_defeat" if strong else "warden_core_hit"
            elif effect.color[2] > effect.color[0]:
                effect_id = "armored_stomp_block"
            else:
                effect_id = "enemy_defeat" if strong else "enemy_hit"
                if strong and effect.color[1] >= 180:
                    self.effects.spawn("stomp_impact", effect.position)
            self.effects.spawn(effect_id, effect.position)
            audio_id = {
                "armored_stomp_block": "armored_block",
                "enemy_defeat": "enemy_defeat",
                "enemy_hit": "enemy_hit",
                "warden_defeat": "warden_defeat",
                "warden_core_hit": "warden_hurt",
            }[effect_id]
            self.audio.play_sound(audio_id, position=effect.position, listener_x=self.player.rect.centerx)
        legacy.clear()

    def _emit_boss_effects(self, result: object) -> None:
        if result.triggered:
            self.effects.spawn("warden_awaken", self.boss_system.boss.rect.center)
        mapping = {
            "phase": "warden_phase_three" if self.boss_system.boss.phase >= 3 else "warden_phase_two",
            "slam": "warden_ground_slam",
            "ground_slam": "warden_ground_slam",
            "projectile": "warden_bolt_launch",
            "bolt": "warden_bolt_launch",
            "ember_rain": "warden_bolt_launch",
            "leap": "warden_leap_takeoff",
            "charge": "warden_leap_takeoff",
            "core_burst": "warden_core_burst",
            "hurt": "warden_core_hit",
            "defeat": "warden_defeat",
        }
        for hook in result.audio_events:
            effect_id = mapping.get(hook)
            if effect_id:
                self.effects.spawn(effect_id, self.boss_system.boss.rect.center)
        owner = "boss:warden:vulnerable"
        if self.boss_system.boss.vulnerable:
            if owner not in self.effects.emitters:
                self.effects.start_emitter(owner, "warden_core_vulnerable", self.boss_system.boss.rect.center)
            self.effects.update_emitter_position(owner, self.boss_system.boss.rect.center)
        else:
            self.effects.stop_emitter(owner)

    def _update_effects(self, dt: float) -> None:
        for event in self.projectiles.consume_effect_events():
            self.effects.spawn(event.effect_id, event.position)
            self.audio.play_sound(
                "breakable_destroy" if event.effect_id == "breakable_destroy" else "ember_pulse_hit",
                position=event.position,
                listener_x=self.player.rect.centerx,
            )
        self._effect_trail_timer -= dt
        if self._effect_trail_timer <= 0:
            for projectile in self.projectiles.projectiles:
                if projectile.faction.value == "player":
                    self.effects.spawn("ember_pulse_trail", projectile.rect.center)
            if self.powerups.has(PowerUpType.WIND_BOOTS) and abs(self.player.velocity.x) > 80:
                self.effects.spawn("wind_boots_trail", self.player.rect.midbottom)
            self._effect_trail_timer = 0.05
        self.effects.update(dt, self.camera.view_rect)
        self.effects.apply_shake(self.camera)
        self.audio.update(dt)

    def _emit_achievement(self, event: str, **payload: object) -> None:
        if self.debug.enabled:
            self.debug.record_event("ACHIEVEMENT", event, **payload)
            return
        unlocked = self.achievements.emit(event, **payload)
        for definition in unlocked:
            self.achievement_toasts.push(definition)
            self.audio.play_sound("achievement_unlocked")
            self.effects.spawn("route_unlocked", (self.canvas.get_width() - 220, 90))
        self.achievements.notifications.clear()
