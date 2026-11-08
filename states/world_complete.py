"""Per-world completion summary, driven by the world registry."""

from __future__ import annotations
import pygame
from systems.level_completion import format_time
from core.input_manager import Action, InputManager


class WorldCompleteScreen:
    def __init__(self, title: pygame.font.Font, font: pygame.font.Font, small: pygame.font.Font) -> None:
        self.title, self.font, self.small = title, font, small

    @staticmethod
    def heading(progress: object) -> str:
        return f"{progress.registry.display_name.upper()} COMPLETE"

    @staticmethod
    def rows(progress: object) -> list[tuple[str, str]]:
        registry = progress.registry
        boss_rows = [
            (
                "BOSS",
                f"{registry.boss_display_names.get(boss_id, boss_id).upper()} — "
                + ("DEFEATED" if boss_id in progress.defeated_bosses else "UNDEFEATED"),
            )
            for boss_id in registry.boss_ids
        ]
        shards = progress.aggregate("ember_shards_collected", "ember_shards_total")
        rare = progress.aggregate("rare_crystals_collected", "rare_crystals_total")
        tokens = progress.aggregate("secret_tokens_collected", "secret_tokens_total")
        secrets = progress.secrets
        enemies = progress.aggregate("enemies_defeated", "enemies_total")
        return [
            *boss_rows,
            ("LEVELS", f"{progress.levels_completed} / {len(progress.registry.level_ids)}"),
            ("SCORE", str(progress.score)),
            ("TIME", format_time(progress.completion_time)),
            ("EMBER SHARDS", f"{shards[0]} / {shards[1]}"),
            ("RARE CRYSTALS", f"{rare[0]} / {rare[1]}"),
            ("SECRET TOKENS", f"{tokens[0]} / {tokens[1]}"),
            ("SECRETS FOUND", f"{secrets[0]} / {secrets[1]}"),
            ("ENEMIES", f"{enemies[0]} / {enemies[1]}"),
            ("DEATHS", str(progress.deaths)),
        ]

    def draw(self, surface: pygame.Surface, progress: object, input_manager: InputManager | None = None) -> None:
        surface.fill((10, 17, 38))
        heading = self.title.render(self.heading(progress), True, (255, 218, 128))
        surface.blit(heading, heading.get_rect(center=(640, 115)))
        rows = self.rows(progress)
        for index, (label, value) in enumerate(rows):
            y = 165 + index * 40
            surface.blit(self.font.render(label, True, (178, 198, 226)), (390, y))
            image = self.font.render(value, True, (246, 239, 208))
            surface.blit(image, image.get_rect(topright=(890, y)))
        prompt_text = (
            f"[{input_manager.get_prompt(Action.CONFIRM)}] RETURN TO MAP"
            if input_manager
            else "ENTER / SPACE  RETURN TO MAP"
        )
        prompt = self.small.render(prompt_text, True, (202, 215, 238))
        surface.blit(prompt, prompt.get_rect(center=(640, 635)))
