"""Original three-phase Ashen Warden encounter behavior and procedural art."""

from __future__ import annotations

import math
import pygame

from bosses.boss_base import Boss, BossConfig, BossState
from entities.projectile import Faction, Projectile


class AshenWarden(Boss):
    def __init__(self, config: BossConfig, position: tuple[float, float]) -> None:
        super().__init__(config, position)
        self.facing = -1
        self.attack_history: list[str] = []
        self.current_attack: str | None = None
        self.attack_index = 0
        self.target_x = self.rect.centerx
        self._attack_executed = False
        self.glow = 0.0

    def begin(self) -> None:
        super().begin()
        self.attack_history.clear()
        self.current_attack = None
        self.attack_index = 0

    def update(self, dt: float, player_rect: pygame.Rect, arena: pygame.Rect, spawn_projectile, new_id) -> tuple[str, ...]:
        if not self.active:
            return ()
        previous_state = self.state
        self.update_lifecycle(dt)
        self.glow += dt
        events: list[str] = []
        if self.state is BossState.DEFEATED:
            return ("defeat_complete",) if self.state_timer <= 0 else ()
        if self.state is BossState.INTRO and self.state_timer <= 0:
            self.set_state(BossState.IDLE, 0.45)
            events.append("intro_complete")
        elif self.state is BossState.PHASE_TRANSITION and self.state_timer <= 0:
            self.set_state(BossState.IDLE, 0.4)
            events.append("phase_ready")
        elif self.state is BossState.IDLE and self.state_timer <= 0:
            self._begin_attack(player_rect)
            events.append("telegraph")
        elif self.state is BossState.TELEGRAPH and self.state_timer <= 0:
            self._execute_attack(player_rect, arena, spawn_projectile, new_id)
            events.append(self.current_attack or "attack")
        elif self.state is BossState.ATTACK:
            self._update_motion_attack(dt, player_rect, arena)
            if self.state_timer <= 0:
                self._begin_recovery()
        elif self.state is BossState.RECOVER and self.state_timer <= 0:
            cooldown = self.config.phase_config(self.phase).attack_cooldown
            self.set_state(BossState.IDLE, cooldown)
        if previous_state is not BossState.PHASE_TRANSITION and self.state is BossState.PHASE_TRANSITION:
            events.append("phase_transition")
        return tuple(events)

    def skip_intro(self) -> None:
        if self.state is BossState.INTRO:
            self.set_state(BossState.IDLE, 0.15)

    def _begin_attack(self, player_rect: pygame.Rect) -> None:
        attacks = self.config.phase_config(self.phase).attacks
        candidates = [item for item in attacks if item not in self.attack_history[-1:]] or list(attacks)
        attack = candidates[self.attack_index % len(candidates)]
        self.attack_index += 1
        self.attack_history.append(attack)
        self.attack_history = self.attack_history[-3:]
        self.current_attack = attack
        self.target_x = player_rect.centerx
        base = attack.removeprefix("fast_").removeprefix("double_")
        if base == "charge_leap": base = "leap_slam"
        duration = self.config.timings.get(f"{base}_telegraph", 0.65)
        if attack == "fast_ground_slam": duration *= 0.72
        self.set_state(BossState.TELEGRAPH, duration)

    def _execute_attack(self, player_rect: pygame.Rect, arena: pygame.Rect, spawn, new_id) -> None:
        attack = self.current_attack or "ground_slam"
        if attack in {"ground_slam", "fast_ground_slam"}:
            speed = self.config.projectile_speed * (1.18 if attack.startswith("fast") else 1.0)
            for direction in (-1, 1):
                spawn(self._projectile(new_id("warden_wave"), (self.rect.centerx, self.rect.bottom - 12), (direction * speed, 0), 2.2, (34, 18), False))
            self.set_state(BossState.ATTACK, 0.16)
        elif attack in {"ember_bolt", "double_ember_bolt"}:
            count = 2 if attack.startswith("double") else 1
            origin = pygame.Vector2(self.rect.centerx, self.rect.centery - 18)
            direction = pygame.Vector2(player_rect.center) - origin
            if direction.length_squared(): direction = direction.normalize()
            for index in range(count):
                velocity = direction.rotate((index - (count - 1) / 2) * 14) * self.config.projectile_speed
                spawn(self._projectile(new_id("warden_bolt"), origin, velocity, 3.0, (18, 18), True))
            self.set_state(BossState.ATTACK, 0.12)
        elif attack == "ember_rain":
            spacing = arena.width / 6
            safe_index = max(1, min(4, int((player_rect.centerx - arena.left) / spacing)))
            for index in range(1, 6):
                if index == safe_index: continue
                x = arena.left + spacing * index
                spawn(self._projectile(new_id("warden_rain"), (x, arena.top + 20), (0, self.config.projectile_speed * 0.9), 2.5, (22, 28), False))
            self.set_state(BossState.ATTACK, 0.3)
        elif attack in {"leap_slam", "charge_leap"}:
            destination = max(arena.left + 90, min(self.target_x, arena.right - self.rect.width - 90))
            self.position.x = destination - self.rect.width / 2
            self.rect.x = round(self.position.x)
            for direction in (-1, 1):
                spawn(self._projectile(new_id("warden_wave"), (self.rect.centerx, self.rect.bottom - 12), (direction * self.config.projectile_speed * 1.05, 0), 2.1, (34, 18), False))
            self.set_state(BossState.ATTACK, 0.22)
        elif attack == "heavy_advance":
            self.set_state(BossState.ATTACK, 0.9)
        elif attack == "core_burst":
            for angle in range(0, 360, 45):
                velocity = pygame.Vector2(self.config.projectile_speed * 0.82, 0).rotate(angle)
                spawn(self._projectile(new_id("warden_burst"), self.rect.center, velocity, 2.8, (18, 18), False))
            self.set_state(BossState.ATTACK, 0.3)

    def _update_motion_attack(self, dt: float, player_rect: pygame.Rect, arena: pygame.Rect) -> None:
        if self.current_attack not in {"heavy_advance", "charge_leap"}:
            return
        direction = 1 if player_rect.centerx > self.rect.centerx else -1
        speed = self.config.movement_speed * (1.5 if self.current_attack == "charge_leap" else 1.0)
        self.position.x = max(arena.left + 12, min(self.position.x + direction * speed * dt, arena.right - self.rect.width - 12))
        self.rect.x = round(self.position.x)
        self.facing = direction

    def _begin_recovery(self) -> None:
        attack = self.current_attack or "ground_slam"
        base = attack.removeprefix("fast_").removeprefix("double_")
        if base == "charge_leap": base = "leap_slam"
        duration = self.config.timings.get(f"{base}_recovery", 0.65)
        vulnerable = attack in {"ground_slam", "fast_ground_slam", "ember_rain", "leap_slam", "charge_leap", "core_burst"}
        self.set_state(BossState.RECOVER, duration, vulnerable)

    def _projectile(self, projectile_id: str, position, velocity, lifetime: float, size: tuple[int, int], terrain: bool) -> Projectile:
        return Projectile(projectile_id, position, pygame.Vector2(velocity), 1, Faction.ENEMY, lifetime, owner_id=self.boss_id, terrain_collision=terrain, size=size)

    def draw(self, surface: pygame.Surface, offset: tuple[int, int]) -> None:
        rect = self.rect.move(offset)
        intensity = min(1.0, self.phase / 3 + 0.12 * math.sin(self.glow * 6))
        if self.state is BossState.DEFEATED:
            collapse = 1.0 - self.state_timer / max(self.config.defeat_duration, 0.01)
            rect.y += round(collapse * 45); rect.height = max(12, round(rect.height * (1.0 - collapse * 0.6)))
        pygame.draw.ellipse(surface, (43, 36, 34), rect.inflate(18, 10))
        pygame.draw.rect(surface, (91, 86, 75), rect, border_radius=24)
        pygame.draw.rect(surface, (117, 126, 87), (rect.x + 8, rect.y + 18, 18, rect.height - 35), border_radius=8)
        pygame.draw.rect(surface, (117, 126, 87), (rect.right - 26, rect.y + 18, 18, rect.height - 35), border_radius=8)
        core = (rect.centerx, rect.centery - 8)
        core_color = (255, round(115 + 80 * intensity), 58)
        radius = 20 + self.phase * 3 + (4 if self.state in {BossState.TELEGRAPH, BossState.PHASE_TRANSITION} else 0)
        pygame.draw.circle(surface, (54, 40, 38), core, radius + 8)
        pygame.draw.circle(surface, core_color, core, radius)
        pygame.draw.circle(surface, (255, 237, 170), core, max(5, radius // 3))
        crack = (255, 131, 56)
        for dx in (-38, -20, 24, 40):
            pygame.draw.line(surface, crack, (rect.centerx + dx, rect.y + 22), (rect.centerx + dx // 2, rect.centery), 3)
        if self.vulnerable:
            pygame.draw.circle(surface, (255, 246, 183), core, radius + 12, 4)
        if self.state is BossState.TELEGRAPH:
            pygame.draw.circle(surface, (255, 194, 83), core, radius + 18, 3)
