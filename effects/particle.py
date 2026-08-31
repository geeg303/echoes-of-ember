"""Small delta-time particle value object with procedural rendering."""

from __future__ import annotations

from dataclasses import dataclass
import math
import pygame

from effects.definitions import EffectPriority, EffectSpace, ParticlePrimitive


@dataclass(slots=True)
class Particle:
    position: pygame.Vector2
    velocity: pygame.Vector2
    acceleration: pygame.Vector2
    age: float
    lifetime: float
    start_size: float
    end_size: float
    start_alpha: int
    end_alpha: int
    rotation: float
    angular_velocity: float
    drag: float
    primitive: ParticlePrimitive
    color: tuple[int, int, int]
    space: EffectSpace
    priority: EffectPriority
    effect_id: str

    @property
    def active(self) -> bool:
        return self.age < self.lifetime

    @property
    def progress(self) -> float:
        return max(0.0, min(1.0, self.age / max(self.lifetime, 0.0001)))

    @property
    def size(self) -> float:
        return self.start_size + (self.end_size - self.start_size) * self.progress

    @property
    def alpha(self) -> int:
        return round(self.start_alpha + (self.end_alpha - self.start_alpha) * self.progress)

    def update(self, dt: float) -> None:
        if not self.active:
            return
        dt = max(0.0, dt)
        self.age += dt
        self.velocity += self.acceleration * dt
        if self.drag > 0:
            self.velocity *= math.exp(-self.drag * dt)
        self.position += self.velocity * dt
        self.rotation += self.angular_velocity * dt

    def draw(self, surface: pygame.Surface, camera_offset: tuple[int, int] = (0, 0)) -> None:
        if not self.active or self.alpha <= 0 or self.size <= 0:
            return
        offset = camera_offset if self.space is EffectSpace.WORLD else (0, 0)
        center = pygame.Vector2(self.position.x + offset[0], self.position.y + offset[1])
        color = (*self.color, self.alpha)
        size = max(1, round(self.size))
        if self.primitive is ParticlePrimitive.CIRCLE:
            pygame.draw.circle(surface, color, center, size)
        elif self.primitive is ParticlePrimitive.SPARK:
            direction = pygame.Vector2(max(2, size * 2.2), 0).rotate(self.rotation)
            pygame.draw.line(surface, color, center - direction / 2, center + direction / 2, max(1, size // 3))
        elif self.primitive is ParticlePrimitive.RECT:
            half = pygame.Vector2(size, size * 0.65)
            points = [center + pygame.Vector2(x, y).rotate(self.rotation) for x, y in ((-half.x,-half.y),(half.x,-half.y),(half.x,half.y),(-half.x,half.y))]
            pygame.draw.polygon(surface, color, points)
        elif self.primitive is ParticlePrimitive.GLOW:
            pygame.draw.circle(surface, (*self.color, max(1, self.alpha // 4)), center, size * 2)
            pygame.draw.circle(surface, color, center, size)
        else:
            pygame.draw.circle(surface, color, center, size)
            pygame.draw.circle(surface, (*self.color, max(1, self.alpha // 2)), center, size + 3, 2)
