"""Screen-space dialogue presentation with robust wrapping and choice focus."""
from __future__ import annotations
import pygame
from core.input_manager import Action
def wrap_text(font,text,width):
 lines=[]
 for paragraph in text.split("\n"):
  current=""
  for word in paragraph.split():
   trial=f"{current} {word}".strip()
   if current and font.size(trial)[0]>width:lines.append(current);current=word
   else:current=trial
  lines.append(current)
 return lines or [""]
class DialogueBox:
 def __init__(self,title,font,small):self.title=title;self.font=font;self.small=small
 def draw(self,surface,dialogue,input_manager):
  node=dialogue.node
  if node is None:return
  box=pygame.Rect(110,430,1060,250);shade=pygame.Surface(surface.get_size(),pygame.SRCALPHA);shade.fill((0,0,0,72));surface.blit(shade,(0,0));pygame.draw.rect(surface,(16,23,43),box,border_radius=20);pygame.draw.rect(surface,(229,158,77),box,3,border_radius=20)
  speaker=node.speaker or "EMBER ECHO";surface.blit(self.title.render(speaker.upper(),True,(255,210,126)),(145,452))
  for i,line in enumerate(wrap_text(self.font,dialogue.visible_text,970)[:4]):surface.blit(self.font.render(line,True,(232,232,221)),(150,500+i*31))
  if dialogue.text_complete and dialogue.available_choices:
   for i,c in enumerate(dialogue.available_choices):surface.blit(self.small.render(("◆ " if i==dialogue.choice_index else "  ")+c.label,True,(255,211,113) if i==dialogue.choice_index else (197,207,225)),(650,500+i*32))
  prompt=f"[{input_manager.get_prompt(Action.CONFIRM)}] {'SELECT' if dialogue.available_choices else 'CONTINUE'}   [{input_manager.get_prompt(Action.BACK)}] CLOSE"
  surface.blit(self.small.render(prompt,True,(177,195,224)),(150,646))
