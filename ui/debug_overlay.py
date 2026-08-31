"""Compact development diagnostics for movement and animation."""

from __future__ import annotations

import pygame

from entities.player import Player
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from systems.effects_system import EffectsSystem


class DebugOverlay:
    def __init__(self, font: pygame.font.Font) -> None:
        self.font = font

    def draw(self, surface: pygame.Surface, player: Player, effects: "EffectsSystem | None" = None) -> None:
        lines = [
            f"ANIM  {player.animation.current_name}  frame {player.animation.frame_index}",
            f"FACE  {'right' if player.facing > 0 else 'left'}",
            f"GROUND  {player.grounded}",
            f"VEL  {player.velocity.x:7.1f}, {player.velocity.y:7.1f}",
        ]
        if effects is not None:
            lines.extend((f"FX  {effects.particle_count}  emit {effects.emitter_count}", f"FX A/G/S  {effects.ambient_count}/{effects.gameplay_count}/{effects.screen_effect_count}"))
        panel = pygame.Surface((320, 12 + len(lines) * 23), pygame.SRCALPHA)
        panel.fill((9, 13, 31, 178))
        pygame.draw.rect(panel, (109, 126, 181, 210), panel.get_rect(), 2, border_radius=8)
        for index, line in enumerate(lines):
            label = self.font.render(line, True, (220, 230, 246))
            panel.blit(label, (12, 8 + index * 23))
        surface.blit(panel, (16, surface.get_height() - panel.get_height() - 16))

