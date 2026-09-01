"""Procedural, non-solid, non-damaging NPC world entity."""
from __future__ import annotations
from dataclasses import dataclass
import math,pygame
@dataclass(frozen=True,slots=True)
class NPCVariant:dialogue_id:str;priority:int;conditions:tuple[dict,...]
class NPC:
 def __init__(self,npc_id,display_name,position,interaction_radius,style,facing,variants):
  self.npc_id=npc_id;self.display_name=display_name;self.position=pygame.Vector2(position);self.rect=pygame.Rect(round(position[0]),round(position[1]),42,64);self.interaction_radius=interaction_radius;self.style=style;self.facing=1 if facing=="right" else -1;self.variants=variants;self.age=0.;self.talking=False
 def update(self,dt,player_rect):
  self.age+=max(0,dt)
  if self.talking:self.facing=1 if player_rect.centerx>=self.rect.centerx else -1
 def in_range(self,player_rect):return self.rect.inflate(self.interaction_radius*2,self.interaction_radius).colliderect(player_rect)
 def draw(self,surface,offset,prompt=None,prompt_font=None):
  r=self.rect.move(offset);bob=round(math.sin(self.age*2.2)*2);colors={"mira":((48,91,112),(245,142,73)),"orin":((79,112,67),(215,197,124)),"talen":((111,69,58),(232,109,65)),"vesper":((78,58,116),(190,148,238))};body,accent=colors.get(self.style,((65,79,105),(230,151,72)))
  pygame.draw.circle(surface,(244,210,164),(r.centerx,r.top+14+bob),10);pygame.draw.rect(surface,body,(r.x+7,r.y+24+bob,28,36),border_radius=7);pygame.draw.line(surface,accent,(r.x+8,r.y+34+bob),(r.x+34,r.y+34+bob),5)
  eye=r.centerx+(4*self.facing);pygame.draw.circle(surface,(31,35,45),(eye,r.top+13+bob),2)
  if prompt:
   img=prompt_font.render(prompt,True,(255,242,194));surface.blit(img,img.get_rect(midbottom=(r.centerx,r.top-7)))
