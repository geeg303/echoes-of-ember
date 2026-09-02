"""Screen-space presentation for frozen level results."""

from __future__ import annotations
import pygame

from systems.level_completion import LevelResult, format_time
from core.input_manager import Action,InputManager


class LevelCompleteScreen:
    def __init__(self, title_font: pygame.font.Font, font: pygame.font.Font, small_font: pygame.font.Font) -> None:
        self.title_font = title_font
        self.font = font
        self.small_font = small_font

    def reset(self) -> None:
        return None

    def draw(self, surface: pygame.Surface, display_name: str, result: LevelResult, input_manager: InputManager | None = None) -> None:
        shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        shade.fill((8, 12, 29, 232))
        surface.blit(shade, (0, 0))
        panel = pygame.Rect(250, 70, 780, 580)
        pygame.draw.rect(surface, (20, 29, 57), panel, border_radius=24)
        pygame.draw.rect(surface, (226, 161, 76), panel, 4, border_radius=24)
        title = self.title_font.render(f"{display_name.upper()} COMPLETE", True, (255, 224, 151))
        surface.blit(title, title.get_rect(center=(640, 120)))
        rating = self.title_font.render(result.rating.value, True, (255, 188, 78))
        surface.blit(rating, rating.get_rect(center=(640, 174)))
        rows = [
            ("TIME", format_time(result.completion_time)),
            ("SCORE", f"{result.score:08d}"),
            ("EMBER SHARDS", f"{result.ember_shards_collected} / {result.ember_shards_total}"),
            ("RARE CRYSTALS", f"{result.rare_crystals_collected} / {result.rare_crystals_total}"),
            ("SECRET TOKEN", "FOUND" if result.secret_tokens_collected else "MISSING"),
            ("SECRETS", f"{result.secrets_discovered} / {result.secrets_total}"),
            ("ENEMIES DEFEATED", f"{result.enemies_defeated} / {result.enemies_total}"),
            ("LIVES REMAINING", str(result.lives_remaining)),
        ]
        for index, (label, value) in enumerate(rows):
            y = 215 + index * 44
            surface.blit(self.font.render(label, True, (174, 192, 222)), (350, y))
            value_image = self.font.render(value, True, (245, 241, 220))
            surface.blit(value_image, value_image.get_rect(topright=(930, y)))
        if result.exit_type.value == "secret_exit":
            banner = self.small_font.render("SECRET EXIT FOUND!", True, (219, 155, 255))
            surface.blit(banner, banner.get_rect(center=(640, 196)))
        message = (f"[{input_manager.get_prompt(Action.CONFIRM)}] CONTINUE   [{input_manager.get_prompt(Action.ATTACK)}] REPLAY   [{input_manager.get_prompt(Action.BACK)}] MAP" if input_manager else "ENTER / SPACE  CONTINUE TO MAP     R  REPLAY     M  WORLD MAP")
        prompt = self.small_font.render(message, True, (197, 211, 238))
        surface.blit(prompt, prompt.get_rect(center=(640, 604)))
