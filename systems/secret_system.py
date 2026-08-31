"""World-space discovery, optional challenge, and alternate-exit lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, field

import pygame

from world.secret_area import SecretArea, SecretDefinition, SecretState, SecretTrigger, SecretType


@dataclass(slots=True)
class SecretUpdate:
    score_awarded: int = 0
    messages: list[str] = field(default_factory=list)
    secret_exit_id: str | None = None


class SecretSystem:
    def __init__(self, definitions: tuple[SecretDefinition, ...]) -> None:
        self.definitions = definitions
        self.areas = {item.secret_id: SecretArea(item) for item in definitions}

    @property
    def discovered_count(self) -> int:
        return sum(area.state is not SecretState.UNDISCOVERED for area in self.areas.values())

    @property
    def completed_room_count(self) -> int:
        return sum(
            area.state is SecretState.COMPLETED
            and area.definition.kind in {SecretType.ROOM, SecretType.CHALLENGE}
            for area in self.areas.values()
        )

    def update(
        self,
        player_rect: pygame.Rect,
        interact_pressed: bool,
        defeated_enemy_ids: set[str],
    ) -> SecretUpdate:
        outcome = SecretUpdate()
        for area in self.areas.values():
            overlaps = area.rect.colliderect(player_rect)
            if area.state is SecretState.UNDISCOVERED and overlaps:
                area.state = SecretState.DISCOVERED
                outcome.messages.append("SECRET DISCOVERED")
                self._reward(area, outcome)
            if not overlaps:
                continue
            definition = area.definition
            if area.state is SecretState.DISCOVERED:
                area.state = SecretState.ENTERED
            if definition.kind is SecretType.CHALLENGE:
                if definition.trigger is SecretTrigger.REACH_TARGET:
                    self._complete(area, outcome)
                elif definition.trigger is SecretTrigger.DEFEAT_ALL and set(definition.enemy_ids) <= defeated_enemy_ids:
                    self._complete(area, outcome)
            elif definition.kind is SecretType.EXIT:
                if interact_pressed:
                    self._complete(area, outcome)
                    outcome.secret_exit_id = definition.secret_id
            else:
                self._complete(area, outcome)
        return outcome

    @staticmethod
    def _reward(area: SecretArea, outcome: SecretUpdate) -> None:
        if not area.reward_claimed and area.definition.kind is not SecretType.CHALLENGE:
            area.reward_claimed = True
            outcome.score_awarded += area.score_value

    def _complete(self, area: SecretArea, outcome: SecretUpdate) -> None:
        if area.state is SecretState.COMPLETED:
            return
        area.state = SecretState.COMPLETED
        if not area.reward_claimed:
            area.reward_claimed = True
            outcome.score_awarded += area.score_value
        if area.definition.kind is SecretType.CHALLENGE:
            outcome.messages.append("CHALLENGE COMPLETE")

    def draw(self, surface: pygame.Surface, view: pygame.Rect, offset: tuple[int, int]) -> None:
        for area in self.areas.values():
            if area.definition.kind is not SecretType.EXIT or not view.colliderect(area.rect):
                continue
            rect = area.rect.move(offset)
            color = (188, 114, 255) if area.state is SecretState.UNDISCOVERED else (255, 183, 88)
            pygame.draw.ellipse(surface, color, rect, 4)
            pygame.draw.circle(surface, (255, 232, 150), rect.center, 8)

