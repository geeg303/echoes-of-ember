"""Nova-specific placeholder art and animation clip configuration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pygame

from settings import PLAYER_ANIMATION
from systems.animation import AnimationClip, AnimationController


class PlayerAnimationState(str, Enum):
    IDLE = "idle"
    RUN = "run"
    JUMP = "jump"
    FALL = "fall"
    LAND = "land"
    HURT = "hurt"
    ATTACK = "attack"
    DEATH = "death"


@dataclass(frozen=True, slots=True)
class AnimationSpec:
    frame_count: int
    fps: float
    loop: bool
    events: dict[int, tuple[str, ...]]


PLAYER_ANIMATION_SPECS: dict[PlayerAnimationState, AnimationSpec] = {
    PlayerAnimationState.IDLE: AnimationSpec(4, 4.0, True, {}),
    PlayerAnimationState.RUN: AnimationSpec(6, 12.0, True, {1: ("footstep",), 4: ("footstep",)}),
    PlayerAnimationState.JUMP: AnimationSpec(2, 8.0, True, {}),
    PlayerAnimationState.FALL: AnimationSpec(2, 6.0, True, {}),
    PlayerAnimationState.LAND: AnimationSpec(3, 14.0, False, {0: ("land",)}),
    PlayerAnimationState.HURT: AnimationSpec(3, 10.0, False, {0: ("hurt",)}),
    PlayerAnimationState.ATTACK: AnimationSpec(4, 14.0, False, {2: ("attack_hit",)}),
    PlayerAnimationState.DEATH: AnimationSpec(5, 8.0, False, {0: ("death",)}),
}


def build_player_animation_controller() -> AnimationController:
    clips: list[AnimationClip] = []
    for state, spec in PLAYER_ANIMATION_SPECS.items():
        frames = [
            _draw_nova_frame(state, frame_index, spec.frame_count)
            for frame_index in range(spec.frame_count)
        ]
        clips.append(
            AnimationClip.from_surfaces(
                state.value,
                frames,
                fps=spec.fps,
                loop=spec.loop,
                frame_events=spec.events,
            )
        )
    controller = AnimationController(clips)
    controller.play(PlayerAnimationState.IDLE.value, restart=True)
    return controller


def _draw_nova_frame(
    state: PlayerAnimationState,
    frame_index: int,
    frame_count: int,
) -> pygame.Surface:
    width, height = PLAYER_ANIMATION.visual_size
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    phase = frame_index / max(1, frame_count - 1)
    center_x = width // 2
    feet_y = height - 4

    bob = 0
    body_height = 39
    body_width = 31
    body_color = (65, 57, 116)
    scarf_color = (242, 103, 71)
    leg_a = -7
    leg_b = 7
    arm_a = -16
    arm_b = 16

    if state is PlayerAnimationState.IDLE:
        bob = (0, -1, -2, -1)[frame_index]
    elif state is PlayerAnimationState.RUN:
        cycle = (-8, -4, 4, 8, 4, -4)[frame_index]
        bob = -2 if frame_index in (1, 4) else 0
        leg_a, leg_b = cycle, -cycle
        arm_a, arm_b = -cycle - 11, cycle + 11
    elif state is PlayerAnimationState.JUMP:
        bob = -3
        body_height = 43
        leg_a, leg_b = -5, 5
        arm_a, arm_b = -20, 20
    elif state is PlayerAnimationState.FALL:
        body_height = 36
        body_width = 34
        leg_a, leg_b = -10, 10
        arm_a, arm_b = -22, 22
    elif state is PlayerAnimationState.LAND:
        compression = (8, 5, 2)[frame_index]
        bob = compression
        body_height -= compression
        body_width += compression // 2
        leg_a, leg_b = -11, 11
    elif state is PlayerAnimationState.HURT:
        bob = (0, -2, 1)[frame_index]
        body_color = (219, 84, 113) if frame_index % 2 == 0 else (255, 218, 196)
        scarf_color = (255, 230, 125)
        arm_a, arm_b = -22, 13
    elif state is PlayerAnimationState.ATTACK:
        bob = -1
        arm_b = (15, 23, 27, 17)[frame_index]
        leg_a, leg_b = -4, 7
    elif state is PlayerAnimationState.DEATH:
        bob = round(phase * 12)
        body_height = max(18, 39 - round(phase * 18))
        body_width = 34 + round(phase * 5)
        body_color = (72, 62, 94)

    foot_base = feet_y + bob
    glow_radius = 8 + (frame_index % 2) * 2
    glow = pygame.Surface((30, 30), pygame.SRCALPHA)
    pygame.draw.circle(glow, (255, 154, 57, 48), (15, 15), glow_radius + 5)
    pygame.draw.circle(glow, (255, 191, 76, 210), (15, 15), glow_radius)
    surface.blit(glow, (center_x - 29, foot_base - 49))

    leg_top = foot_base - 20
    pygame.draw.line(surface, (42, 43, 76), (center_x - 6, leg_top), (center_x + leg_a, foot_base), 7)
    pygame.draw.line(surface, (42, 43, 76), (center_x + 6, leg_top), (center_x + leg_b, foot_base), 7)

    body_rect = pygame.Rect(0, 0, body_width, body_height)
    body_rect.midbottom = (center_x, foot_base - 16)
    pygame.draw.rect(surface, body_color, body_rect, border_radius=9)
    scarf_y = body_rect.y + round(body_rect.height * 0.58)
    pygame.draw.rect(surface, scarf_color, (body_rect.x, scarf_y, body_rect.width, 8), border_radius=4)

    shoulder_y = body_rect.y + 13
    pygame.draw.line(surface, body_color, (body_rect.x + 4, shoulder_y), (center_x + arm_a, shoulder_y + 19), 7)
    pygame.draw.line(surface, body_color, (body_rect.right - 4, shoulder_y), (center_x + arm_b, shoulder_y + 18), 7)

    head_center = (center_x + 2, body_rect.y - 4)
    pygame.draw.circle(surface, (242, 190, 126), head_center, 12)
    hood = [
        (head_center[0] - 16, head_center[1] + 3),
        (head_center[0] - 2, head_center[1] - 19),
        (head_center[0] + 17, head_center[1] + 4),
    ]
    pygame.draw.polygon(surface, (86, 68, 142), hood)
    pygame.draw.circle(surface, (255, 240, 166), (head_center[0] + 7, head_center[1]), 3)

    if state is PlayerAnimationState.ATTACK and frame_index >= 1:
        pulse_center = (min(width - 6, center_x + arm_b + 5), shoulder_y + 17)
        pygame.draw.circle(surface, (255, 137, 62, 90), pulse_center, 9 + frame_index)
        pygame.draw.circle(surface, (255, 232, 137), pulse_center, 5)
    if state is PlayerAnimationState.HURT:
        pygame.draw.line(surface, (255, 245, 190), (8, 18 + frame_index * 4), (18, 12 + frame_index * 4), 3)
    return surface

