"""Temporary World 1 completion summary."""
from __future__ import annotations
import pygame
from systems.level_completion import format_time

class WorldCompleteScreen:
    def __init__(self, title: pygame.font.Font, font: pygame.font.Font, small: pygame.font.Font) -> None:
        self.title, self.font, self.small = title, font, small
    def draw(self, surface: pygame.Surface, progress: object) -> None:
        surface.fill((10, 17, 38))
        heading = self.title.render("VERDANT REACHES COMPLETE", True, (255, 218, 128))
        surface.blit(heading, heading.get_rect(center=(640, 115)))
        shards = progress.aggregate("ember_shards_collected", "ember_shards_total")
        rare = progress.aggregate("rare_crystals_collected", "rare_crystals_total")
        tokens = progress.aggregate("secret_tokens_collected", "secret_tokens_total")
        secrets = progress.secrets
        enemies = progress.aggregate("enemies_defeated", "enemies_total")
        rows = [("LEVELS", f"{progress.levels_completed} / {len(progress.registry.level_ids)}"), ("SCORE", str(progress.score)), ("TIME", format_time(progress.completion_time)), ("EMBER SHARDS", f"{shards[0]} / {shards[1]}"), ("RARE CRYSTALS", f"{rare[0]} / {rare[1]}"), ("SECRET TOKENS", f"{tokens[0]} / {tokens[1]}"), ("SECRETS FOUND", f"{secrets[0]} / {secrets[1]}"), ("ENEMIES", f"{enemies[0]} / {enemies[1]}"), ("DEATHS", str(progress.deaths))]
        for index, (label, value) in enumerate(rows):
            y = 185 + index * 43
            surface.blit(self.font.render(label, True, (178, 198, 226)), (390, y))
            image = self.font.render(value, True, (246, 239, 208))
            surface.blit(image, image.get_rect(topright=(890, y)))
        prompt = self.small.render("ENTER / SPACE  REPLAY WORLD     ESC  QUIT", True, (202, 215, 238))
        surface.blit(prompt, prompt.get_rect(center=(640, 635)))
