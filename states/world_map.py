"""Procedural Verdant Reaches overworld presentation and node information."""

from __future__ import annotations

import math

import pygame

from core.input_manager import Action,InputManager
from systems.level_completion import format_time
from world.world_map import ConnectionState, NodeState, NodeType, WorldMapRuntime


class WorldMapScreen:
    def __init__(self, runtime: WorldMapRuntime, title: pygame.font.Font, font: pygame.font.Font, small: pygame.font.Font, input_manager: InputManager | None = None) -> None:
        self.runtime = runtime
        self.title = title
        self.font = font
        self.small = small
        self.age = 0.0
        self.message = ""
        self.message_timer = 0.0
        self.input = input_manager

    def update(self, dt: float) -> None:
        self.age += dt
        self.runtime.update(dt)
        self.message_timer = max(0.0, self.message_timer - dt)

    def notify(self, message: str) -> None:
        self.message = message
        self.message_timer = 2.4

    def activate_current(self) -> tuple[str, str | None]:
        if self.runtime.travelling:
            return "none", None
        node = self.runtime.definition.nodes[self.runtime.current_node_id]
        state = self.runtime.node_state(node.node_id)
        if state in {NodeState.LOCKED, NodeState.HIDDEN}:
            self.notify("THE PATH IS STILL CLOSED")
            return "none", None
        if node.kind in {NodeType.LEVEL, NodeType.BOSS}:
            return "level", node.level_id
        if node.kind is NodeType.SECRET:
            self.notify("THE PATH BEYOND IS NOT YET OPEN")
            return "placeholder", None
        if node.kind is NodeType.WORLD_GOAL:
            return "world_summary", None
        self.notify("CHOOSE A GLOWING DESTINATION")
        return "none", None

    def draw(self, surface: pygame.Surface) -> None:
        self._background(surface)
        self._connections(surface)
        self._landmarks(surface)
        self._nodes(surface)
        self._avatar(surface)
        self._panel(surface)
        if self.message_timer > 0:
            image = self.font.render(self.message, True, (255, 230, 151))
            box = image.get_rect(center=(640, 92)).inflate(40, 20)
            pygame.draw.rect(surface, (18, 25, 51), box, border_radius=13)
            pygame.draw.rect(surface, (229, 166, 88), box, 2, border_radius=13)
            surface.blit(image, image.get_rect(center=box.center))

    def _background(self, surface: pygame.Surface) -> None:
        surface.fill((57, 83, 76))
        pygame.draw.rect(surface, (183, 164, 111), (30, 25, 1220, 670), border_radius=32)
        pygame.draw.rect(surface, (72, 105, 82), (55, 50, 1170, 620), border_radius=28)
        for index in range(18):
            x = 90 + (index * 137) % 1080
            y = 100 + (index * 83) % 410
            sway = round(math.sin(self.age * 0.8 + index) * 3)
            pygame.draw.circle(surface, (45, 91, 65), (x + sway, y), 26)
            pygame.draw.rect(surface, (78, 68, 53), (x - 4, y + 18, 8, 28))
        river = [(70, 590), (260, 545), (430, 575), (620, 505), (790, 540), (1000, 465), (1210, 500)]
        pygame.draw.lines(surface, (73, 141, 157), False, river, 26)
        pygame.draw.lines(surface, (143, 205, 199), False, river, 5)
        for index in range(10):
            x = 150 + index * 103
            y = 82 + round(math.sin(self.age + index) * 5)
            pygame.draw.circle(surface, (255, 190, 92), (x, y), 3)

    def _connections(self, surface: pygame.Surface) -> None:
        for connection in self.runtime.definition.connections:
            state = self.runtime.connection_state(connection)
            if state is ConnectionState.HIDDEN:
                continue
            points = [self.runtime.definition.nodes[connection.source].position, *connection.waypoints, self.runtime.definition.nodes[connection.target].position]
            color = {
                ConnectionState.LOCKED: (72, 76, 70),
                ConnectionState.AVAILABLE: (213, 171, 91),
                ConnectionState.TRAVERSED: (255, 211, 116),
            }[state]
            width = 3 if state is ConnectionState.LOCKED else 7
            pygame.draw.lines(surface, (45, 52, 52), False, points, width + 5)
            if state is ConnectionState.LOCKED:
                for start, end in zip(points, points[1:]):
                    for step in range(0, 10, 2):
                        a = pygame.Vector2(start).lerp(end, step / 10)
                        b = pygame.Vector2(start).lerp(end, min(1, (step + 1) / 10))
                        pygame.draw.line(surface, color, a, b, width)
            else:
                pygame.draw.lines(surface, color, False, points, width)

    def _landmarks(self, surface: pygame.Surface) -> None:
        pygame.draw.polygon(surface, (91, 74, 67), [(690, 510), (770, 390), (850, 510)])
        pygame.draw.polygon(surface, (128, 104, 83), [(720, 510), (770, 430), (815, 510)])
        pygame.draw.rect(surface, (98, 85, 76), (1025, 105, 100, 80))
        pygame.draw.arc(surface, (218, 132, 70), (1038, 75, 74, 95), 0, math.pi, 8)

    def _nodes(self, surface: pygame.Surface) -> None:
        for node in self.runtime.definition.nodes.values():
            state = self.runtime.node_state(node.node_id)
            if state is NodeState.HIDDEN:
                continue
            center = (round(node.position[0]), round(node.position[1]))
            if node.kind is NodeType.SECRET:
                color, radius = (185, 105, 236), 23
            elif node.kind is NodeType.BOSS:
                color, radius = ((255, 205, 92), 31) if state is NodeState.COMPLETED else ((255, 116, 64), 29)
            elif node.kind is NodeType.WORLD_GOAL:
                color, radius = (255, 165, 72), 31
            elif state is NodeState.LOCKED:
                color, radius = (75, 78, 79), 20
            elif state in {NodeState.COMPLETED, NodeState.MASTERED}:
                color, radius = (255, 211, 104), 24
            else:
                color, radius = (126, 222, 147), 22
            pygame.draw.circle(surface, (33, 40, 43), center, radius + 7)
            pygame.draw.circle(surface, color, center, radius)
            pygame.draw.circle(surface, (255, 241, 190), center, radius - 8, 3)
            if state is NodeState.MASTERED:
                pygame.draw.circle(surface, (255, 245, 174), center, radius + 11, 3)
            self._node_marker(surface, center, node.kind, state, radius)

    @staticmethod
    def _node_marker(surface: pygame.Surface, center: tuple[int, int], kind: NodeType, state: NodeState, radius: int) -> None:
        """Give map states a shape cue so they never rely on color alone."""
        x, y = center
        ink = (34, 39, 49)
        if state is NodeState.LOCKED:
            pygame.draw.arc(surface, ink, (x - 7, y - 11, 14, 14), 0, math.pi, 3)
            pygame.draw.rect(surface, ink, (x - 9, y - 3, 18, 14), border_radius=3)
            pygame.draw.circle(surface, (210, 211, 194), (x, y + 2), 2)
        elif state is NodeState.MASTERED:
            points=[]
            for index in range(10):
                angle=-math.pi/2+index*math.pi/5;length=9 if index%2==0 else 4
                points.append((round(x+math.cos(angle)*length),round(y+math.sin(angle)*length)))
            pygame.draw.polygon(surface, ink, points)
        elif state is NodeState.COMPLETED:
            pygame.draw.lines(surface, ink, False, [(x-8,y),(x-2,y+7),(x+10,y-8)], 4)
        elif kind is NodeType.SECRET:
            pygame.draw.circle(surface, ink, center, 5, 2)
            pygame.draw.circle(surface, ink, (x, y + 9), 2)
        elif kind is NodeType.BOSS:
            pygame.draw.polygon(surface, ink, [(x,y-10),(x+10,y),(x,y+10),(x-10,y)], 3)
        elif kind is NodeType.WORLD_GOAL:
            pygame.draw.polygon(surface, ink, [(x,y-11),(x+10,y+8),(x-10,y+8)], 3)
        elif state is NodeState.AVAILABLE:
            pygame.draw.circle(surface, ink, center, 5)

    def _avatar(self, surface: pygame.Surface) -> None:
        x, y = round(self.runtime.avatar_position.x), round(self.runtime.avatar_position.y)
        bob = round(math.sin(self.age * 5) * 2)
        pygame.draw.circle(surface, (255, 139, 70), (x, y - 22 + bob), 10)
        pygame.draw.polygon(surface, (53, 68, 102), [(x - 11, y - 13 + bob), (x + 11, y - 13 + bob), (x + 15, y + 10 + bob), (x - 15, y + 10 + bob)])
        pygame.draw.circle(surface, (255, 226, 167), (x, y - 25 + bob), 4)

    def _panel(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(60, 545, 1160, 125)
        pygame.draw.rect(surface, (14, 23, 42, 225), panel, border_radius=18)
        pygame.draw.rect(surface, (151, 177, 151), panel, 2, border_radius=18)
        node = self.runtime.definition.nodes[self.runtime.current_node_id]
        state = self.runtime.node_state(node.node_id)
        heading = self.title.render(node.title.upper(), True, (255, 226, 151))
        surface.blit(heading, (82, 558))
        status = self.small.render(state.value.upper(), True, (177, 201, 204))
        surface.blit(status, (84, 608))
        if node.level_id and node.level_id in self.runtime.progress.results:
            result = self.runtime.progress.results[node.level_id]
            details = [
                f"RATING {result.rating.value}", f"SCORE {result.score:08d}", f"TIME {format_time(result.completion_time)}",
                f"SHARDS {result.ember_shards_collected}/{result.ember_shards_total}",
                f"RARE {result.rare_crystals_collected}/{result.rare_crystals_total}",
                f"TOKEN {'FOUND' if result.secret_tokens_collected else 'MISSING'}", f"SECRETS {result.secrets_discovered}/{result.secrets_total}",
            ]
        elif node.kind in {NodeType.LEVEL, NodeType.BOSS}:
            details = ["ASHEN WARDEN DEFEATED" if node.kind is NodeType.BOSS and state is NodeState.COMPLETED else "NOT YET COMPLETED"]
        elif node.kind is NodeType.SECRET:
            details = ["A HIDDEN PATH HAS BEEN REVEALED"]
        else:
            details = ([f"[{self.input.get_prompt(Action.CONFIRM)}] SELECT", "STICK / D-PAD  TRAVEL", f"[{self.input.get_prompt(Action.BACK)}] MAIN MENU"] if self.input else ["ENTER / SPACE  SELECT", "ARROWS / WASD  TRAVEL", "ESC  MAIN MENU"])
        image = self.small.render("     ".join(details), True, (219, 224, 218))
        surface.blit(image, (300, 611))
