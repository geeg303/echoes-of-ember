"""Semantic helpers shared by integration and scenario tests."""
from __future__ import annotations

from systems.level_completion import CompletionRating, ExitType, LevelResult


def advance_frames(game, count: int, dt: float = 1 / 60, *, draw: bool = False) -> None:
    for _ in range(count):
        game.update(dt)
        if draw:
            game.draw()


def activate_goal(game) -> None:
    """Use the real goal proximity and interaction path."""
    game.player.reposition((game.goal.rect.x + 10, game.goal.rect.bottom - game.player.rect.height))
    game._interact_pressed = True
    game.update(0)
    game.update(2)


def campaign_result(
    level_id: str,
    *,
    score: int = 100,
    exit_type: ExitType = ExitType.NORMAL,
    exit_id: str = "ember_gate",
    secrets: int = 0,
) -> LevelResult:
    return LevelResult(
        level_id, True, 30.0, score,
        0, 0, 0, 0, 0, 0, 0, 0,
        0, 3, 3, 0, CompletionRating.BRONZE,
        secrets, secrets, 0, exit_type, exit_id,
    )

