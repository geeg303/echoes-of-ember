"""Controller-ready profile achievement browser."""
from __future__ import annotations
import pygame
from core.input_manager import Action
from systems.achievement_system import Visibility
CATEGORIES=("all","progression","exploration","combat","secrets","collectibles","story","challenge")
class AchievementScreen:
 def __init__(self,manager,title,font,small):self.manager=manager;self.title=title;self.font=font;self.small=small;self.category=0;self.focus=0
 @property
 def entries(self):
  category=CATEGORIES[self.category];return tuple(x for x in self.manager.definitions if category=="all" or x.category==category)
 def handle(self,action):
  if action is Action.BACK:return "back"
  if action in {Action.MENU_LEFT,Action.MENU_RIGHT}:self.category=(self.category+(-1 if action is Action.MENU_LEFT else 1))%len(CATEGORIES);self.focus=0;return "move"
  if action in {Action.MENU_UP,Action.MENU_DOWN} and self.entries:self.focus=max(0,min(len(self.entries)-1,self.focus+(-1 if action is Action.MENU_UP else 1)));return "move"
  return "none"
 def draw(self,surface,input_manager):
  surface.fill((10,15,30));panel=pygame.Rect(110,45,1060,630);pygame.draw.rect(surface,(17,24,43),panel,border_radius=22);pygame.draw.rect(surface,(229,154,76),panel,3,border_radius=22)
  head=self.title.render("ACHIEVEMENTS",True,(255,218,143));surface.blit(head,(145,72));count=self.small.render(f"UNLOCKED {self.manager.unlocked_count} / {len(self.manager.definitions)}",True,(190,205,228));surface.blit(count,(850,90))
  cat=self.font.render(f"‹  {CATEGORIES[self.category].upper()}  ›",True,(255,190,91));surface.blit(cat,cat.get_rect(center=(640,145)))
  entries=self.entries;start=max(0,min(self.focus-2,max(0,len(entries)-5)))
  for row,definition in enumerate(entries[start:start+5]):
   idx=start+row;unlocked=definition.id in self.manager.profile.unlocked;hidden=definition.visibility is Visibility.HIDDEN and not unlocked;rect=pygame.Rect(150,180+row*88,980,76)
   pygame.draw.rect(surface,(67,49,48) if idx==self.focus else (27,35,55),rect,border_radius=12)
   if idx==self.focus:pygame.draw.rect(surface,(245,173,79),rect,2,border_radius=12)
   title="???" if hidden else definition.title;desc="Secret Achievement" if hidden else definition.description;color=(255,210,117) if unlocked else (166,177,196)
   surface.blit(self.font.render(("◆ " if unlocked else "◇ ")+title,True,color),(172,192+row*88));surface.blit(self.small.render(desc,True,(194,202,217)),(174,224+row*88));surface.blit(self.small.render(definition.category.upper(),True,(137,161,190)),(930,194+row*88))
   cond=definition.condition
   if not unlocked and cond.get("type")=="counter_at_least":
    current=min(self.manager.profile.counters.get(cond["counter"],0),cond["value"]);surface.blit(self.small.render(f"{current} / {cond['value']}",True,(241,183,93)),(1000,225+row*88))
  footer=f"[{input_manager.get_prompt(Action.MENU_LEFT)} / {input_manager.get_prompt(Action.MENU_RIGHT)}] FILTER   [{input_manager.get_prompt(Action.BACK)}] BACK";surface.blit(self.small.render(footer,True,(175,190,214)),(150,645))
