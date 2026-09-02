"""Capture representative deterministic screens for human polish review."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from core.game import Game
from core.settings_manager import SettingsManager


def capture(output: Path) -> tuple[Path, ...]:
    output.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []

    def save(name: str, game: Game) -> None:
        game.draw()
        path = output / f"{name}.png"
        pygame.image.save(game.canvas, path)
        created.append(path)

    def make(**kwargs) -> Game:
        return Game(
            settings_manager=SettingsManager(output / "capture_settings.json"),
            achievements_enabled=False,
            persistence=False,
            **kwargs,
        )

    game = make(start_frontend=True)
    try:
        save("main_menu", game)
        game.open_settings("frontend")
        save("settings", game)
        game.close_settings()
        game.open_achievements()
        save("achievements", game)
    finally:
        game.shutdown()

    game = make(start_on_map=True)
    try:
        save("world_map", game)
    finally:
        game.shutdown()

    game = make(level_id="verdant_01")
    try:
        save("gameplay", game)
        game.open_pause()
        save("pause", game)
        game.resume_game()
        npc = game.npcs.npcs[0]
        game.player.reposition(npc.rect.topleft)
        game.dialogue.start(game.npcs.choose_dialogue(npc), npc.display_name.lower())
        game.app_mode = "dialogue"
        game.dialogue.update(2)
        save("dialogue", game)
        game._close_dialogue()
        game.app_mode = "gameplay"
        game.player.reposition((game.goal.rect.x + 10, game.goal.rect.bottom - game.player.rect.height))
        game._interact_pressed = True
        game.update(0)
        game.update(2)
        save("level_complete", game)
    finally:
        game.shutdown()

    game = make(level_id="verdant_boss")
    try:
        trigger = game.boss_system.definition.trigger
        game.player.reposition((trigger.centerx, trigger.bottom - game.player.rect.height))
        game.update(1 / 60)
        save("boss", game)
        game.app_mode = "game_over"
        save("game_over", game)
    finally:
        game.shutdown()
    return tuple(created)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("debug_output/polish_review"))
    args = parser.parse_args()
    for path in capture(args.output):
        print(path)


if __name__ == "__main__":
    main()
