"""Nova's responsive platform movement and procedural placeholder rendering."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable

import pygame

from entities.entity import Entity
from settings import (
    GOD_MODE,
    PLAYER_ANIMATION,
    PLAYER_MAX_HEALTH,
    PLAYER_PHYSICS,
    PLAYER_STARTING_LIVES,
    PLAYER_INVULNERABILITY_DURATION,
    PlayerPhysics,
    SHOW_COLLISION_BOXES,
)
from systems.player_animation import (
    PlayerAnimationState,
    build_player_animation_controller,
)
from systems.combat import DamageResult, DamageSource
from world.collision import CollisionEngine, CollisionResult


@dataclass(slots=True)
class PlayerControls:
    move_axis: float = 0.0
    jump_pressed: bool = False
    jump_held: bool = False
    jump_released: bool = False


@dataclass(frozen=True, slots=True)
class PlayerModifiers:
    speed: float = 1.0
    acceleration: float = 1.0
    jump: float = 1.0
    double_jump: bool = False


def move_toward(value: float, target: float, amount: float) -> float:
    if value < target:
        return min(value + amount, target)
    if value > target:
        return max(value - amount, target)
    return target


class Player(Entity):
    WIDTH = 44
    HEIGHT = 62

    def __init__(
        self,
        position: tuple[float, float],
        physics: PlayerPhysics = PLAYER_PHYSICS,
    ) -> None:
        super().__init__(position, (self.WIDTH, self.HEIGHT))
        self.physics = physics
        self.grounded = False
        self.facing = 1
        self.coyote_timer = 0.0
        self.jump_buffer_timer = 0.0
        self.jump_hold_timer = 0.0
        self.on_slippery = False
        self.hit_hazard = False
        self.animation = build_player_animation_controller()
        self.animation_events: tuple[str, ...] = ()
        self.is_dead = False
        self._hurt_active = False
        self._hurt_timer = 0.0
        self._attack_active = False
        self._land_active = False
        self.max_health = PLAYER_MAX_HEALTH
        self.health = self.max_health
        self.lives = PLAYER_STARTING_LIVES
        self.invulnerability_timer = 0.0
        self.previous_rect = self.rect.copy()
        self.modifiers = PlayerModifiers()
        self.extra_jump_available = False
        self.damage_absorber: Callable[[DamageSource], bool] | None = None
        self.double_jump_effect_timer = 0.0

    def update(
        self,
        dt: float,
        controls: PlayerControls,
        collision: CollisionEngine,
        modifiers: PlayerModifiers = PlayerModifiers(),
    ) -> None:
        dt = min(max(dt, 0.0), 0.05)
        self.previous_rect = self.rect.copy()
        self.modifiers = modifiers
        if self.grounded:
            self.extra_jump_available = modifiers.double_jump
        self.invulnerability_timer = max(0.0, self.invulnerability_timer - dt)
        self.double_jump_effect_timer = max(0.0, self.double_jump_effect_timer - dt)
        was_grounded = self.grounded
        if self.is_dead:
            controls = PlayerControls()
        self._update_timers(dt, controls)
        self._update_horizontal_velocity(dt, controls.move_axis)
        if not self.is_dead:
            self._try_buffered_jump()

        if controls.jump_released and self.velocity.y < 0.0:
            self.velocity.y *= self.physics.jump_cut_multiplier
            self.jump_hold_timer = 0.0

        holding_jump = controls.jump_held and self.velocity.y < 0.0 and self.jump_hold_timer > 0.0
        gravity_scale = self.physics.held_jump_gravity_scale if holding_jump else 1.0
        if holding_jump:
            self.jump_hold_timer = max(0.0, self.jump_hold_timer - dt)
        self.velocity.y = min(
            self.velocity.y + self.physics.gravity * gravity_scale * dt,
            self.physics.maximum_fall_speed,
        )

        fall_speed_before_collision = self.velocity.y
        result = collision.move(self.position, self.velocity, self.rect, dt)
        self._apply_collision_result(result)
        if (
            not was_grounded
            and result.grounded
            and fall_speed_before_collision >= PLAYER_ANIMATION.landing_speed_threshold
        ):
            self._land_active = True
            self.animation.play(PlayerAnimationState.LAND.value, restart=True)
        self._update_animation(dt)

    def _update_timers(self, dt: float, controls: PlayerControls) -> None:
        if self.grounded:
            self.coyote_timer = self.physics.coyote_time
        else:
            self.coyote_timer = max(0.0, self.coyote_timer - dt)

        if controls.jump_pressed:
            self.jump_buffer_timer = self.physics.jump_buffer_time
        else:
            self.jump_buffer_timer = max(0.0, self.jump_buffer_timer - dt)

    def _update_horizontal_velocity(self, dt: float, axis: float) -> None:
        axis = max(-1.0, min(1.0, axis))
        if axis:
            self.facing = 1 if axis > 0.0 else -1
            acceleration = (
                self.physics.ground_acceleration if self.grounded else self.physics.air_acceleration
            )
            acceleration *= self.modifiers.acceleration
            target = axis * self.physics.max_run_speed * self.modifiers.speed
        else:
            if self.grounded and self.on_slippery:
                acceleration = self.physics.slippery_deceleration
            else:
                acceleration = (
                    self.physics.ground_deceleration if self.grounded else self.physics.air_deceleration
                )
            target = 0.0
        self.velocity.x = move_toward(self.velocity.x, target, acceleration * dt)

    def _try_buffered_jump(self) -> None:
        if self.jump_buffer_timer <= 0.0:
            return
        if self.coyote_timer <= 0.0:
            if not self.modifiers.double_jump or not self.extra_jump_available:
                return
            self.extra_jump_available = False
            self.double_jump_effect_timer = 0.28
        self.velocity.y = -self.physics.jump_speed * self.modifiers.jump
        self.grounded = False
        self.coyote_timer = 0.0
        self.jump_buffer_timer = 0.0
        self.jump_hold_timer = self.physics.maximum_jump_hold

    def _apply_collision_result(self, result: CollisionResult) -> None:
        self.grounded = result.grounded
        self.on_slippery = result.on_slippery
        self.hit_hazard = result.hit_hazard

    def _update_animation(self, dt: float) -> None:
        state = self._select_animation_state()
        self.animation.flip_x = self.facing < 0
        self.animation.play(state.value)
        self.animation_events = self.animation.update(dt)

        if self._hurt_active:
            self._hurt_timer = max(0.0, self._hurt_timer - dt)
            if self._hurt_timer <= 0.0 and self.animation.finished:
                self._hurt_active = False
        if self._attack_active and self.animation.current_name == PlayerAnimationState.ATTACK.value:
            if self.animation.finished:
                self._attack_active = False
        if self._land_active and self.animation.current_name == PlayerAnimationState.LAND.value:
            if self.animation.finished:
                self._land_active = False

    def _select_animation_state(self) -> PlayerAnimationState:
        if self.is_dead:
            return PlayerAnimationState.DEATH
        if self._hurt_active:
            return PlayerAnimationState.HURT
        if self._attack_active:
            return PlayerAnimationState.ATTACK
        if self._land_active:
            return PlayerAnimationState.LAND
        if not self.grounded:
            threshold = PLAYER_ANIMATION.apex_velocity_threshold
            if self.velocity.y < -threshold:
                return PlayerAnimationState.JUMP
            if self.velocity.y > threshold:
                return PlayerAnimationState.FALL
            if self.animation.current_name == PlayerAnimationState.JUMP.value:
                return PlayerAnimationState.JUMP
            return PlayerAnimationState.FALL
        if abs(self.velocity.x) > 25.0:
            return PlayerAnimationState.RUN
        return PlayerAnimationState.IDLE

    def trigger_hurt(self) -> None:
        """Safe Phase 4 hook for future damage handling."""
        if self.is_dead:
            return
        self._hurt_active = True
        self._hurt_timer = PLAYER_ANIMATION.hurt_duration
        self._attack_active = False
        self._land_active = False
        self.animation.play(PlayerAnimationState.HURT.value, restart=True)

    def trigger_attack(self) -> None:
        """Start the visual attack only; combat is intentionally not implemented."""
        if self.is_dead or self._hurt_active:
            return
        self._attack_active = True
        self._land_active = False
        self.animation.play(PlayerAnimationState.ATTACK.value, restart=True)

    def trigger_death(self) -> None:
        if self.is_dead:
            return
        self.is_dead = True
        self._hurt_active = False
        self._attack_active = False
        self._land_active = False
        self.animation.play(PlayerAnimationState.DEATH.value, restart=True)

    def take_damage(self, amount: int = 1) -> bool:
        """Backward-compatible hazard damage helper."""
        return self.apply_damage(amount, DamageSource.HAZARD).died

    def apply_damage(
        self,
        amount: int,
        source: DamageSource,
        knockback: pygame.Vector2 | None = None,
    ) -> DamageResult:
        if amount <= 0 or GOD_MODE or self.is_dead:
            return DamageResult(False)
        if source is not DamageSource.HAZARD and self.invulnerability_timer > 0.0:
            return DamageResult(False)
        if self.damage_absorber and self.damage_absorber(source):
            return DamageResult(False, absorbed=True)
        self.health = max(0, self.health - amount)
        died = self.health == 0
        if died:
            self.trigger_death()
        else:
            self.trigger_hurt()
            if source is not DamageSource.HAZARD:
                self.invulnerability_timer = PLAYER_INVULNERABILITY_DURATION
            if knockback:
                self.velocity.update(knockback)
                self.grounded = False
        return DamageResult(True, died, amount)

    def stabilize_for_completion(self) -> None:
        """Resolve a committed boss defeat ahead of a simultaneous player death."""
        self.is_dead = False
        self.health = max(1, self.health)
        self.invulnerability_timer = PLAYER_INVULNERABILITY_DURATION
        self.velocity.update()
        self._hurt_active = False
        self._attack_active = False

    def bounce_from_stomp(self, speed: float) -> None:
        self.velocity.y = -abs(speed)
        self.grounded = False

    def heal(self, amount: int = 1) -> int:
        if amount <= 0:
            return 0
        previous = self.health
        self.health = min(self.max_health, self.health + amount)
        return self.health - previous

    def lose_life_and_restore(self) -> None:
        self.lives = max(0, self.lives - 1)
        self.health = self.max_health

    @property
    def death_animation_finished(self) -> bool:
        return (
            self.is_dead
            and self.animation.current_name == PlayerAnimationState.DEATH.value
            and self.animation.finished
        )

    def respawn(self, position: tuple[float, float]) -> None:
        self.reposition(position)
        self.is_dead = False
        self._hurt_active = False
        self._hurt_timer = 0.0
        self._attack_active = False
        self._land_active = False
        self.animation.flip_x = self.facing < 0
        self.animation.play(PlayerAnimationState.IDLE.value, restart=True)
        self.animation_events = ()

    def reposition(self, position: tuple[float, float]) -> None:
        """Move to a safe spawn while preserving health and active visual reactions."""
        self.position.update(position)
        self.velocity.update(0.0, 0.0)
        self.sync_rect()
        self.grounded = False
        self.on_slippery = False
        self.hit_hazard = False
        self.coyote_timer = 0.0
        self.jump_buffer_timer = 0.0
        self.jump_hold_timer = 0.0
        self.invulnerability_timer = 0.0
        self.previous_rect = self.rect.copy()

    def draw(self, surface: pygame.Surface, offset: tuple[int, int] = (0, 0)) -> None:
        draw_rect = self.rect.move(offset)
        shadow = pygame.Rect(draw_rect.x - 5, draw_rect.bottom - 8, draw_rect.width + 10, 12)
        pygame.draw.ellipse(surface, (10, 13, 31, 100), shadow)
        if self.invulnerability_timer > 0.0 and int(self.invulnerability_timer * 16) % 2 == 0:
            if SHOW_COLLISION_BOXES:
                pygame.draw.rect(surface, (75, 255, 165), draw_rect, 2)
            return
        frame = self.animation.current_frame
        frame_rect = frame.get_rect(midbottom=draw_rect.midbottom)
        surface.blit(frame, frame_rect)
        if self.double_jump_effect_timer > 0.0:
            radius = round(18 + (0.28 - self.double_jump_effect_timer) * 80)
            pygame.draw.circle(surface, (210, 174, 255), draw_rect.midbottom, radius, 3)

        if SHOW_COLLISION_BOXES:
            pygame.draw.rect(surface, (75, 255, 165), draw_rect, 2)
