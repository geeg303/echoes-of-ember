"""Reusable moving, falling, and disappearing world platforms."""

from __future__ import annotations

from enum import Enum
import pygame


class PlatformState(str, Enum):
    STABLE = "stable"
    WARNING = "warning"
    FALLING = "falling"
    HIDDEN = "hidden"


class MovingPlatform:
    def __init__(self, object_id: str, position: tuple[float, float], movement: str, distance: float, speed: float, size: tuple[int, int] = (128, 22)) -> None:
        self.object_id = object_id
        self.origin = pygame.Vector2(position)
        self.position = pygame.Vector2(position)
        self.movement = movement
        self.distance = distance
        self.speed = speed
        self.direction = 1.0
        self.offset = 0.0
        self.delta = pygame.Vector2()
        self.rect = pygame.Rect(round(position[0]), round(position[1]), *size)
        self.previous_rect = self.rect.copy()
        self.solid = True

    def update(self, dt: float) -> None:
        self.previous_rect = self.rect.copy()
        old = self.position.copy()
        self.offset += self.direction * self.speed * dt
        if self.offset >= self.distance:
            self.offset = self.distance
            self.direction = -1.0
        elif self.offset <= 0.0:
            self.offset = 0.0
            self.direction = 1.0
        self.position.update(self.origin)
        if self.movement == "horizontal":
            self.position.x += self.offset
        else:
            self.position.y += self.offset
        self.rect.topleft = (round(self.position.x), round(self.position.y))
        self.delta = self.position - old

    def trigger(self) -> None:
        return None

    def draw(self, surface: pygame.Surface, offset: tuple[int, int]) -> None:
        rect = self.rect.move(offset)
        pygame.draw.rect(surface, (79, 151, 153), rect, border_radius=7)
        pygame.draw.rect(surface, (165, 232, 199), rect, 3, border_radius=7)
        for x in range(rect.x + 16, rect.right - 8, 28):
            pygame.draw.circle(surface, (255, 214, 118), (x, rect.centery), 3)


class FallingPlatform(MovingPlatform):
    def __init__(self, object_id: str, position: tuple[float, float], activation_delay: float, fall_acceleration: float, reset_delay: float, size: tuple[int, int] = (112, 22)) -> None:
        super().__init__(object_id, position, "vertical", 0, 0, size)
        self.activation_delay = activation_delay
        self.fall_acceleration = fall_acceleration
        self.reset_delay = reset_delay
        self.state = PlatformState.STABLE
        self.timer = 0.0
        self.fall_speed = 0.0

    def trigger(self) -> None:
        if self.state is PlatformState.STABLE:
            self.state = PlatformState.WARNING
            self.timer = self.activation_delay

    def update(self, dt: float) -> None:
        self.previous_rect = self.rect.copy()
        old = self.position.copy()
        if self.state is PlatformState.WARNING:
            self.timer -= dt
            if self.timer <= 0:
                self.state = PlatformState.FALLING
        elif self.state is PlatformState.FALLING:
            self.fall_speed += self.fall_acceleration * dt
            self.position.y += self.fall_speed * dt
            if self.position.y > self.origin.y + 700:
                self.state = PlatformState.HIDDEN
                self.solid = False
                self.timer = self.reset_delay
        elif self.state is PlatformState.HIDDEN:
            self.timer -= dt
            if self.timer <= 0:
                self.position.update(self.origin)
                self.fall_speed = 0.0
                self.state = PlatformState.STABLE
                self.solid = True
        self.rect.topleft = (round(self.position.x), round(self.position.y))
        self.delta = self.position - old

    def draw(self, surface: pygame.Surface, offset: tuple[int, int]) -> None:
        if self.state is PlatformState.HIDDEN:
            return
        rect = self.rect.move(offset)
        color = (238, 161, 79) if self.state is PlatformState.WARNING and int(self.timer * 14) % 2 else (137, 94, 90)
        pygame.draw.rect(surface, color, rect, border_radius=6)
        pygame.draw.line(surface, (70, 47, 58), rect.topleft, rect.bottomright, 3)


class DisappearingPlatform(MovingPlatform):
    def __init__(self, object_id: str, position: tuple[float, float], visible_duration: float, warning_duration: float, hidden_duration: float, size: tuple[int, int] = (112, 20)) -> None:
        super().__init__(object_id, position, "horizontal", 0, 0, size)
        self.visible_duration = visible_duration
        self.warning_duration = warning_duration
        self.hidden_duration = hidden_duration
        self.state = PlatformState.STABLE
        self.timer = visible_duration

    def update(self, dt: float) -> None:
        self.previous_rect = self.rect.copy()
        self.delta.update()
        self.timer -= dt
        if self.timer > 0:
            return
        if self.state is PlatformState.STABLE:
            self.state = PlatformState.WARNING
            self.timer = self.warning_duration
        elif self.state is PlatformState.WARNING:
            self.state = PlatformState.HIDDEN
            self.timer = self.hidden_duration
            self.solid = False
        else:
            self.state = PlatformState.STABLE
            self.timer = self.visible_duration
            self.solid = True

    def draw(self, surface: pygame.Surface, offset: tuple[int, int]) -> None:
        if self.state is PlatformState.HIDDEN:
            return
        rect = self.rect.move(offset)
        color = (202, 153, 255) if self.state is PlatformState.STABLE or int(self.timer * 16) % 2 else (105, 82, 139)
        pygame.draw.rect(surface, color, rect, border_radius=9)
        pygame.draw.rect(surface, (239, 218, 255), rect, 2, border_radius=9)
