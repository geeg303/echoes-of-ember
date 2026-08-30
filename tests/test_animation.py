"""Reusable animation controller timing, events, completion, and flipping."""

from __future__ import annotations

import pygame
import pytest

from systems.animation import AnimationClip, AnimationController


def colored_surface(left: tuple[int, int, int], right: tuple[int, int, int]) -> pygame.Surface:
    surface = pygame.Surface((2, 1))
    surface.set_at((0, 0), left)
    surface.set_at((1, 0), right)
    return surface


def test_playing_same_animation_does_not_reset_timing() -> None:
    frames = [pygame.Surface((2, 2)), pygame.Surface((2, 2))]
    controller = AnimationController([AnimationClip.from_surfaces("run", frames, fps=10)])
    controller.update(0.06)
    controller.play("run")
    controller.update(0.05)
    assert controller.frame_index == 1


def test_non_looping_completion_and_reset() -> None:
    frames = [pygame.Surface((2, 2)), pygame.Surface((2, 2))]
    controller = AnimationController(
        [AnimationClip.from_surfaces("land", frames, fps=10, loop=False)]
    )
    controller.update(0.21)
    assert controller.finished
    assert controller.frame_index == 1
    controller.reset()
    assert not controller.finished and controller.frame_index == 0


def test_events_emit_once_when_entering_frame() -> None:
    frames = [pygame.Surface((2, 2)), pygame.Surface((2, 2))]
    controller = AnimationController(
        [
            AnimationClip.from_surfaces(
                "attack",
                frames,
                fps=10,
                loop=False,
                frame_events={1: ("attack_hit",)},
            )
        ]
    )
    assert controller.update(0.11) == ("attack_hit",)
    assert controller.update(0.01) == ()


def test_horizontal_flip_is_visual_only() -> None:
    red = (255, 0, 0)
    blue = (0, 0, 255)
    controller = AnimationController(
        [AnimationClip.from_surfaces("idle", [colored_surface(red, blue)], fps=1)]
    )
    controller.flip_x = True
    assert controller.current_frame.get_at((0, 0))[:3] == blue
    assert controller.current_frame.get_at((1, 0))[:3] == red


def test_invalid_animation_configuration_is_rejected() -> None:
    with pytest.raises(ValueError, match="fps"):
        AnimationClip.from_surfaces("bad", [pygame.Surface((1, 1))], fps=0)
    with pytest.raises(ValueError, match="at least one"):
        AnimationClip("bad", ())

