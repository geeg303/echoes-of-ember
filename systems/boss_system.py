"""Boss encounter orchestration using shared combat, projectile, and arena systems."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import pygame

from bosses.ashen_warden import AshenWarden
from bosses.boss_base import BossState, load_boss_config
from entities.player import Player
from entities.projectile import Faction
from settings import EMBER_PULSE_KNOCKBACK, PLAYER_ENEMY_KNOCKBACK, PROJECT_ROOT
from systems.combat import CombatEffect, DamageSource
from systems.powerup_system import PowerUpSystem, PowerUpType
from systems.progression import LevelProgress
from systems.projectile_system import ProjectileManager
from ui.boss_hud import BossHUDState
from world.boss_arena import BossArena, BossArenaDefinition


@dataclass(slots=True)
class BossUpdateResult:
    triggered: bool = False
    player_damaged: bool = False
    player_died: bool = False
    boss_hit: bool = False
    boss_defeated: bool = False
    defeat_sequence_complete: bool = False
    score_awarded: int = 0
    shake: float = 0.0
    audio_events: tuple[str, ...] = ()


class BossSystem:
    def __init__(self, definition: BossArenaDefinition, doors: list[object], projectiles: ProjectileManager) -> None:
        config = load_boss_config(PROJECT_ROOT / "data" / "bosses" / f"{definition.boss_id}.json")
        if config.boss_id != definition.boss_id:
            raise ValueError("boss definition/config ID mismatch")
        if definition.boss_id != "ashen_warden":
            raise ValueError(f"no runtime implementation for boss: {definition.boss_id}")
        self.definition = definition
        self.arena = BossArena(definition, doors)
        self.boss = AshenWarden(config, definition.spawn)
        self.projectiles = projectiles
        self.effects: list[CombatEffect] = []
        self.completed_reported = False

    @property
    def active(self) -> bool:
        return self.arena.active

    @property
    def defeated(self) -> bool:
        return self.boss.defeat_claimed

    @property
    def hud_state(self) -> BossHUDState:
        visible = self.arena.active and not self.boss.defeated
        return BossHUDState(
            visible,
            self.boss.display_name,
            self.boss.health,
            self.boss.max_health,
            self.boss.phase,
            self.boss.state is BossState.INTRO,
            self.boss.vulnerable,
        )

    def update(self, dt: float, player: Player, powers: PowerUpSystem, progress: LevelProgress) -> BossUpdateResult:
        result = BossUpdateResult()
        if self.arena.try_trigger(player.rect):
            self.boss.begin()
            powers.grant_encounter_ability(PowerUpType.EMBER_PULSE)
            result.triggered = True
            result.audio_events = ("awaken",)
        if not self.arena.active:
            return result
        events = self.boss.update(dt, player.rect, self.definition.bounds, self.projectiles.spawn, self.projectiles.new_id)
        audio = list(result.audio_events)
        if "phase_transition" in events:
            result.shake = 8.0
            audio.append("phase")
        if any(item in events for item in ("ground_slam", "fast_ground_slam")):
            result.shake = max(result.shake, 7.0)
            audio.append("ground_slam")
        if "leap_slam" in events:
            result.shake = max(result.shake, 7.0)
            audio.append("leap")
        if "charge_leap" in events:
            result.shake = max(result.shake, 7.0)
            audio.append("charge")
        if any(item in events for item in ("ember_bolt", "double_ember_bolt")):
            audio.append("bolt")
        if "ember_rain" in events:
            audio.append("ember_rain")
        if "core_burst" in events:
            audio.append("core_burst")
        result.audio_events = tuple(audio)
        for projectile in self.projectiles.projectiles:
            if not projectile.active or projectile.faction is not Faction.PLAYER or not projectile.rect.colliderect(self.boss.rect):
                continue
            projectile.active = False
            previous_phase = self.boss.phase
            if self.boss.take_damage(projectile.damage):
                result.boss_hit = True
                result.audio_events += ("hurt",)
                if self.boss.phase != previous_phase:
                    result.shake = max(result.shake, 8.0)
                    result.audio_events += ("phase",)
                self.effects.append(CombatEffect(pygame.Vector2(projectile.rect.center), (255, 200, 92), self.boss.defeat_claimed))
                if self.boss.defeat_claimed:
                    result.boss_defeated = True
                    result.audio_events += ("defeat",)
                    result.score_awarded = self.boss.claim_score()
                    progress.award_score(result.score_awarded)
                    self._clear_hostile_projectiles()
                    result.shake = 12.0
        contact_enabled = self.boss.state not in {BossState.INTRO, BossState.PHASE_TRANSITION, BossState.DEFEATED}
        if contact_enabled and self.boss.rect.colliderect(player.rect) and not player.is_dead:
            direction = -1 if player.rect.centerx < self.boss.rect.centerx else 1
            damage = player.apply_damage(
                self.boss.config.contact_damage, DamageSource.ENEMY,
                pygame.Vector2(direction * PLAYER_ENEMY_KNOCKBACK[0], PLAYER_ENEMY_KNOCKBACK[1]),
            )
            result.player_damaged = damage.applied or damage.absorbed
            result.player_died = damage.died
            if damage.applied: result.shake = max(result.shake, 6.0)
        if self.boss.defeat_claimed:
            self._clear_hostile_projectiles()
            if player.is_dead:
                player.stabilize_for_completion()
            if self.boss.defeated and not self.completed_reported:
                self.completed_reported = True
                self.arena.finish()
                powers.clear_encounter_abilities()
                result.defeat_sequence_complete = True
        for effect in self.effects: effect.update(dt)
        self.effects = [effect for effect in self.effects if effect.active]
        return result

    def skip_intro(self) -> None:
        self.boss.skip_intro()

    def reset_encounter(self, powers: PowerUpSystem | None = None) -> None:
        self._clear_hostile_projectiles()
        self.boss.reset(self.definition.spawn)
        self.arena.reset()
        self.effects.clear()
        self.completed_reported = False
        if powers is not None: powers.clear_encounter_abilities()

    def debug_damage(self, amount: int) -> bool:
        """Apply controlled developer damage while preserving phase/defeat invariants."""
        if amount <= 0 or self.boss.defeat_claimed:
            return False
        self.boss.active = True
        self.boss.invulnerability_timer = 0.0
        self.boss.vulnerable = True
        return self.boss.take_damage(amount)

    def _clear_hostile_projectiles(self) -> None:
        for projectile in self.projectiles.projectiles:
            if projectile.faction is Faction.ENEMY and projectile.owner_id == self.boss.boss_id:
                projectile.active = False
        self.projectiles.projectiles = [item for item in self.projectiles.projectiles if item.active]

    def draw(self, surface: pygame.Surface, offset: tuple[int, int]) -> None:
        if self.arena.active and self.boss.state is BossState.TELEGRAPH:
            arena = self.definition.bounds.move(offset)
            attack = self.boss.current_attack
            if attack == "ember_rain":
                spacing = self.definition.bounds.width / 6
                safe = max(1, min(4, int((self.boss.target_x - self.definition.bounds.left) / spacing)))
                for index in range(1, 6):
                    if index == safe:
                        continue
                    x = round(self.definition.bounds.left + spacing * index + offset[0])
                    pygame.draw.circle(surface, (255, 91, 58), (x, arena.bottom - 12), 28, 4)
                    pygame.draw.line(surface, (255, 170, 78), (x, arena.top + 20), (x, arena.bottom - 40), 2)
            elif attack in {"leap_slam", "charge_leap"}:
                x = round(self.boss.target_x + offset[0])
                pygame.draw.circle(surface, (255, 100, 62), (x, arena.bottom - 12), 52, 5)
        if self.arena.active or self.arena.completed:
            self.boss.draw(surface, offset)
        for effect in self.effects:
            effect.draw(surface, offset)
        source = pygame.Vector2(self.definition.pulse_source) + pygame.Vector2(offset)
        pygame.draw.circle(surface, (255, 125, 52), source, 24)
        pygame.draw.circle(surface, (255, 231, 153), source, 11)
