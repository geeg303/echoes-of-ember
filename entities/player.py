"""Nova's responsive platform movement and procedural placeholder rendering."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from entities.entity import Entity
from settings import PLAYER_PHYSICS, PlayerPhysics, SHOW_COLLISION_BOXES
from world.collision import CollisionEngine, CollisionResult


@dataclass(slots=True)
class PlayerControls:
    move_axis: float = 0.0
    jump_pressed: bool = False
    jump_held: bool = False
    jump_released: bool = False


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

    def update(
        self,
        dt: float,
        controls: PlayerControls,
        collision: CollisionEngine,
    ) -> None:
        dt = min(max(dt, 0.0), 0.05)
        self._update_timers(dt, controls)
        self._update_horizontal_velocity(dt, controls.move_axis)
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

        result = collision.move(self.position, self.velocity, self.rect, dt)
        self._apply_collision_result(result)

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
            target = axis * self.physics.max_run_speed
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
        if self.jump_buffer_timer <= 0.0 or self.coyote_timer <= 0.0:
            return
        self.velocity.y = -self.physics.jump_speed
        self.grounded = False
        self.coyote_timer = 0.0
        self.jump_buffer_timer = 0.0
        self.jump_hold_timer = self.physics.maximum_jump_hold

    def _apply_collision_result(self, result: CollisionResult) -> None:
        self.grounded = result.grounded
        self.on_slippery = result.on_slippery
        self.hit_hazard = result.hit_hazard

    def respawn(self, position: tuple[float, float]) -> None:
        self.position.update(position)
        self.velocity.update(0.0, 0.0)
        self.sync_rect()
        self.grounded = False
        self.on_slippery = False
        self.hit_hazard = False
        self.coyote_timer = 0.0
        self.jump_buffer_timer = 0.0
        self.jump_hold_timer = 0.0

    def draw(self, surface: pygame.Surface, offset: tuple[int, int] = (0, 0)) -> None:
        # An original luminous explorer silhouette, generated without external art.
        draw_rect = self.rect.move(offset)
        shadow = pygame.Rect(draw_rect.x - 5, draw_rect.bottom - 8, draw_rect.width + 10, 12)
        pygame.draw.ellipse(surface, (10, 13, 31, 100), shadow)

        body = draw_rect.inflate(-8, -10)
        pygame.draw.rect(surface, (59, 55, 108), body, border_radius=13)
        pygame.draw.rect(surface, (238, 104, 72), (body.x, body.y + 29, body.width, 12), border_radius=6)

        head_center = (draw_rect.centerx + self.facing * 2, draw_rect.y + 16)
        pygame.draw.circle(surface, (242, 190, 126), head_center, 13)
        hood_points = [
            (draw_rect.centerx - 17, draw_rect.y + 18),
            (draw_rect.centerx, draw_rect.y - 3),
            (draw_rect.centerx + 18, draw_rect.y + 19),
        ]
        pygame.draw.polygon(surface, (82, 63, 135), hood_points)
        eye = (head_center[0] + self.facing * 6, head_center[1] + 1)
        pygame.draw.circle(surface, (255, 238, 165), eye, 3)

        ember = (draw_rect.centerx - self.facing * 14, draw_rect.y + 35)
        pygame.draw.circle(surface, (255, 172, 62), ember, 7)
        pygame.draw.circle(surface, (255, 235, 142), ember, 3)

        if SHOW_COLLISION_BOXES:
            pygame.draw.rect(surface, (75, 255, 165), draw_rect, 2)
