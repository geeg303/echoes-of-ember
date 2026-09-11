"""Data-driven Ember Current definitions, runtime influence, and rendering."""
from __future__ import annotations
from dataclasses import dataclass
import math
import pygame

CURRENT_TARGETS = frozenset({"player", "player_projectiles", "flyers"})
CURRENT_STYLES = frozenset({"glassreach", "lift", "strong"})
MAX_CURRENT_INFLUENCE = 1800.0

@dataclass(frozen=True, slots=True)
class EmberCurrentDefinition:
    current_id: str
    bounds: pygame.Rect
    direction: pygame.Vector2
    strength: float
    affects: frozenset[str]
    enabled: bool = True
    style: str = "glassreach"

@dataclass(slots=True)
class EmberCurrentRuntime:
    definition: EmberCurrentDefinition
    enabled: bool

class EmberCurrentSystem:
    def __init__(self, definitions: tuple[EmberCurrentDefinition, ...] = ()) -> None:
        self.definitions = definitions
        self.currents = {item.current_id: EmberCurrentRuntime(item, item.enabled) for item in definitions}
    def reset(self) -> None:
        self.currents = {item.current_id: EmberCurrentRuntime(item, item.enabled) for item in self.definitions}
    def influence(self, rect: pygame.Rect, target: str) -> pygame.Vector2:
        total = pygame.Vector2()
        for runtime in self.currents.values():
            definition = runtime.definition
            if runtime.enabled and target in definition.affects and definition.bounds.colliderect(rect): total += definition.direction * definition.strength
        if total.length_squared() > MAX_CURRENT_INFLUENCE ** 2: total.scale_to_length(MAX_CURRENT_INFLUENCE)
        return total
    def overlapping_ids(self, rect: pygame.Rect, target: str = "player") -> tuple[str, ...]:
        return tuple(r.definition.current_id for r in self.currents.values() if r.enabled and target in r.definition.affects and r.definition.bounds.colliderect(rect))
    def set_enabled(self, current_id: str, enabled: bool) -> None:self.currents[current_id].enabled = enabled
    def reverse(self, current_id: str) -> None:
        runtime=self.currents[current_id];d=runtime.definition
        runtime.definition=EmberCurrentDefinition(d.current_id,d.bounds.copy(),-d.direction,d.strength,d.affects,d.enabled,d.style)
    def draw(self, surface: pygame.Surface, view: pygame.Rect, offset: tuple[int, int]) -> None:
        padded=view.inflate(128,128)
        for runtime in self.currents.values():
            if not runtime.enabled or not padded.colliderect(runtime.definition.bounds):continue
            d=runtime.definition;rect=d.bounds.move(offset);pygame.draw.rect(surface,(116,205,221),rect,2)
            base_spacing=56 if d.strength<700 else 42 if d.strength<1200 else 30
            visible=rect.clip(surface.get_rect());spacing=max(base_spacing,math.ceil(math.sqrt(max(1,visible.width*visible.height)/72)))
            direction=d.direction;side=pygame.Vector2(-direction.y,direction.x)*5
            for y in range(visible.top+spacing//2,visible.bottom,spacing):
                for x in range(visible.left+spacing//2,visible.right,spacing):
                    start=pygame.Vector2(x,y)-direction*12;end=pygame.Vector2(x,y)+direction*12
                    pygame.draw.line(surface,(210,247,235),start,end,2);pygame.draw.polygon(surface,(210,247,235),[end,end-direction*8+side,end-direction*8-side])

def parse_ember_currents(raw: object) -> tuple[EmberCurrentDefinition, ...]:
    definitions=[]
    for item in raw if isinstance(raw,list) else []:
        x,y,width,height=item["bounds"];direction=pygame.Vector2(item["direction"]);direction.normalize_ip()
        definitions.append(EmberCurrentDefinition(str(item["id"]),pygame.Rect(round(x),round(y),round(width),round(height)),direction,float(item["strength"]),frozenset(item["affects"]),bool(item.get("enabled",True)),str(item.get("style","glassreach"))))
    return tuple(definitions)
