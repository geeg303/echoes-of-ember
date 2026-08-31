"""Central owner for bounded procedural visual effects.

Effects are cosmetic observers and never feed particle state into gameplay.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import random
import pygame
from effects import EFFECT_DEFINITIONS, EffectDefinition, EffectPriority, EffectSpace, Particle

class EffectQuality(str, Enum):
    FULL="full"; REDUCED="reduced"; OFF="off"

@dataclass(slots=True)
class ContinuousEmitter:
    owner_id: str
    effect_id: str
    position: pygame.Vector2
    region: pygame.Rect | None = None
    accumulator: float = 0.0

@dataclass(slots=True)
class ScreenFlash:
    color: tuple[int,int,int]
    opacity: int
    duration: float
    age: float = 0.0
    @property
    def active(self)->bool: return self.age < self.duration
    @property
    def alpha(self)->int: return round(self.opacity*max(0.0,1.0-self.age/max(self.duration,.001)))

class EffectsSystem:
    """Updates, culls, renders and caps transient visual effects."""
    def __init__(self, definitions:dict[str,EffectDefinition]|None=None, *, capacity:int=600, seed:int=0xEFFE, quality:EffectQuality=EffectQuality.FULL)->None:
        self.definitions=definitions or EFFECT_DEFINITIONS
        self.capacity=max(1,capacity); self.quality=quality
        self.particles:list[Particle]=[]; self.emitters:dict[str,ContinuousEmitter]={}
        self.flashes:list[ScreenFlash]=[]; self._shake_requests:list[tuple[float,float]]=[]
        self._rng=random.Random(seed); self._overlay:pygame.Surface|None=None; self._overlay_size=(0,0)
    @property
    def particle_count(self)->int: return len(self.particles)
    @property
    def emitter_count(self)->int: return len(self.emitters)
    @property
    def ambient_count(self)->int: return sum(p.priority is EffectPriority.AMBIENT for p in self.particles)
    @property
    def gameplay_count(self)->int: return sum(p.priority is not EffectPriority.AMBIENT for p in self.particles)
    @property
    def screen_effect_count(self)->int: return sum(p.space is EffectSpace.SCREEN for p in self.particles)+len(self.flashes)
    def set_quality(self,quality:EffectQuality)->None:
        self.quality=quality
        if quality is EffectQuality.OFF: self.particles=[p for p in self.particles if p.priority is EffectPriority.CRITICAL]
    def toggle_optional(self)->EffectQuality:
        self.set_quality(EffectQuality.OFF if self.quality is not EffectQuality.OFF else EffectQuality.FULL); return self.quality
    def spawn(self,effect_id:str,position:tuple[float,float]|pygame.Vector2,*,count_scale:float=1.0)->int:
        try: definition=self.definitions[effect_id]
        except KeyError as exc: raise ValueError(f"Unknown effect definition: {effect_id}") from exc
        return self._spawn_definition(definition,pygame.Vector2(position),max(0,round(definition.count*max(0.0,count_scale))))
    def _spawn_definition(self,d:EffectDefinition,origin:pygame.Vector2,count:int)->int:
        if self.quality is EffectQuality.OFF and d.priority is not EffectPriority.CRITICAL: return 0
        if self.quality is EffectQuality.REDUCED and d.priority is not EffectPriority.CRITICAL: count=max(1,count//2) if count else 0
        count=min(count,max(0,d.max_particles-sum(p.effect_id==d.effect_id for p in self.particles))); spawned=0
        for _ in range(count):
            if not self._reserve_slot(d.priority): break
            angle=d.direction+self._rng.uniform(-d.spread/2,d.spread/2); velocity=pygame.Vector2(); velocity.from_polar((self._rng.uniform(*d.speed),angle))
            offset=pygame.Vector2()
            if d.spawn_radius: offset.from_polar((self._rng.uniform(0,d.spawn_radius),self._rng.uniform(0,360)))
            self.particles.append(Particle(origin+offset,velocity,pygame.Vector2(d.acceleration),0.0,self._rng.uniform(*d.lifetime),self._rng.uniform(*d.start_size),self._rng.uniform(*d.end_size),d.alpha[0],d.alpha[1],self._rng.uniform(0,360),self._rng.uniform(-240,240),d.drag,d.primitive,self._rng.choice(d.colors),d.space,d.priority,d.effect_id)); spawned+=1
        return spawned
    def _reserve_slot(self,priority:EffectPriority)->bool:
        if len(self.particles)<self.capacity: return True
        for target in (EffectPriority.AMBIENT,EffectPriority.NORMAL):
            if target>=priority: break
            for i,p in enumerate(self.particles):
                if p.priority is target: self.particles.pop(i); return True
        return False
    def start_emitter(self,owner_id:str,effect_id:str,position:tuple[float,float]|pygame.Vector2,*,region:pygame.Rect|None=None)->None:
        d=self.definitions.get(effect_id)
        if d is None: raise ValueError(f"Unknown effect definition: {effect_id}")
        if d.emission_rate<=0: raise ValueError(f"Effect {effect_id!r} is not a continuous emitter")
        self.emitters[owner_id]=ContinuousEmitter(owner_id,effect_id,pygame.Vector2(position),region)
    def update_emitter_position(self,owner_id:str,position:tuple[float,float]|pygame.Vector2)->None:
        if owner_id in self.emitters: self.emitters[owner_id].position.update(position)
    def stop_emitter(self,owner_id:str)->None: self.emitters.pop(owner_id,None)
    def stop_emitters(self,owner_prefix:str)->None:
        for owner_id in tuple(self.emitters):
            if owner_id.startswith(owner_prefix): self.emitters.pop(owner_id)
    def request_flash(self,color:tuple[int,int,int],opacity:int=72,duration:float=.16)->None: self.flashes.append(ScreenFlash(color,max(0,min(112,opacity)),max(.01,duration)))
    def request_shake(self,intensity:float,duration:float)->None: self._shake_requests.append((max(0.0,min(18.0,intensity)),max(0.0,min(.6,duration))))
    def apply_shake(self,camera:object)->None:
        if not self._shake_requests: return
        intensity=max(x for x,_ in self._shake_requests); duration=max(y for _,y in self._shake_requests); shake=getattr(camera,"shake",None)
        if callable(shake) and intensity>0 and duration>0: shake(intensity,duration)
        self._shake_requests.clear()
    def update(self,dt:float,viewport:pygame.Rect|None=None)->None:
        dt=max(0.0,dt)
        for emitter in self.emitters.values():
            d=self.definitions[emitter.effect_id]
            if self.quality is EffectQuality.OFF and d.priority is not EffectPriority.CRITICAL: continue
            if viewport is not None and d.space is EffectSpace.WORLD:
                padded=viewport.inflate(320,240)
                if emitter.region is not None and not padded.colliderect(emitter.region): continue
                if emitter.region is None and not padded.collidepoint(emitter.position): continue
            rate=d.emission_rate*(.5 if self.quality is EffectQuality.REDUCED else 1.0); emitter.accumulator+=rate*dt; amount=int(emitter.accumulator); emitter.accumulator-=amount
            for _ in range(amount):
                origin=pygame.Vector2(emitter.position)
                if emitter.region is not None:
                    region=emitter.region.clip(viewport.inflate(160,120)) if viewport is not None and d.space is EffectSpace.WORLD else emitter.region
                    if region.width<=0 or region.height<=0: continue
                    origin.update(self._rng.uniform(region.left,region.right),self._rng.uniform(region.top,region.bottom))
                self._spawn_definition(d,origin,1)
        for particle in self.particles: particle.update(dt)
        self.particles=[p for p in self.particles if p.active]
        for flash in self.flashes: flash.age+=dt
        self.flashes=[f for f in self.flashes if f.active]
    def draw_world(self,surface:pygame.Surface,camera_offset:tuple[int,int],viewport:pygame.Rect)->None:
        overlay=self._prepare_overlay(surface); padded=viewport.inflate(160,120)
        for particle in self.particles:
            if particle.space is EffectSpace.WORLD and padded.collidepoint(particle.position): particle.draw(overlay,camera_offset)
        surface.blit(overlay,(0,0))
    def draw_screen(self,surface:pygame.Surface)->None:
        overlay=self._prepare_overlay(surface)
        for particle in self.particles:
            if particle.space is EffectSpace.SCREEN: particle.draw(overlay)
        for flash in self.flashes: overlay.fill((*flash.color,flash.alpha),special_flags=pygame.BLEND_RGBA_ADD)
        surface.blit(overlay,(0,0))
    def _prepare_overlay(self,surface:pygame.Surface)->pygame.Surface:
        if self._overlay is None or self._overlay_size!=surface.get_size(): self._overlay_size=surface.get_size(); self._overlay=pygame.Surface(self._overlay_size,pygame.SRCALPHA)
        self._overlay.fill((0,0,0,0)); return self._overlay
    def clear(self)->None:
        self.particles.clear(); self.emitters.clear(); self.flashes.clear(); self._shake_requests.clear()
