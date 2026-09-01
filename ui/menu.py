"""Reusable keyboard-first menu controls, focus, sliders, selectors, and dialogs."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from collections.abc import Callable
import pygame
from core.input_manager import Action

class MenuAction(str,Enum):
    UP="menu_up"; DOWN="menu_down"; LEFT="menu_left"; RIGHT="menu_right"; CONFIRM="confirm"; BACK="back"; PAUSE="pause"

def menu_action_from_input(action:Action)->MenuAction|None:
    return {Action.MENU_UP:MenuAction.UP,Action.MENU_DOWN:MenuAction.DOWN,Action.MENU_LEFT:MenuAction.LEFT,Action.MENU_RIGHT:MenuAction.RIGHT,Action.CONFIRM:MenuAction.CONFIRM,Action.BACK:MenuAction.BACK,Action.PAUSE:MenuAction.PAUSE}.get(action)

def action_for_key(key:int)->MenuAction|None:
    mapping={pygame.K_UP:MenuAction.UP,pygame.K_w:MenuAction.UP,pygame.K_DOWN:MenuAction.DOWN,pygame.K_s:MenuAction.DOWN,pygame.K_LEFT:MenuAction.LEFT,pygame.K_a:MenuAction.LEFT,pygame.K_RIGHT:MenuAction.RIGHT,pygame.K_d:MenuAction.RIGHT,pygame.K_RETURN:MenuAction.CONFIRM,pygame.K_SPACE:MenuAction.CONFIRM,pygame.K_ESCAPE:MenuAction.BACK}
    return mapping.get(key)
@dataclass(slots=True)
class MenuItem:
    label:str; item_id:str; enabled:bool=True; detail:str=""
class Menu:
    def __init__(self,items:list[MenuItem]|None=None)->None:self.items=items or [];self.focus=0;self._ensure_focus(1)
    @property
    def focused(self)->MenuItem|None:return self.items[self.focus] if self.items else None
    def set_items(self,items:list[MenuItem],preferred:str|None=None)->None:
        old=preferred or (self.focused.item_id if self.focused else None);self.items=items;self.focus=next((i for i,x in enumerate(items) if x.item_id==old and x.enabled),0);self._ensure_focus(1)
    def move(self,direction:int)->bool:
        if not self.items:return False
        start=self.focus
        for _ in self.items:
            self.focus=(self.focus+direction)%len(self.items)
            if self.items[self.focus].enabled:return self.focus!=start
        return False
    def _ensure_focus(self,direction:int)->None:
        if self.items and not self.items[self.focus].enabled:self.move(direction)
@dataclass(slots=True)
class Slider:
    label:str; value:float; step:float=.05
    def adjust(self,direction:int)->float:self.value=max(0,min(1,round((self.value+direction*self.step)*100)/100));return self.value
@dataclass(slots=True)
class Selector:
    label:str; options:tuple[str,...]; index:int=0
    @property
    def value(self)->str:return self.options[self.index]
    def adjust(self,direction:int)->str:self.index=(self.index+direction)%len(self.options);return self.value
@dataclass(slots=True)
class ConfirmationDialog:
    title:str; message:str; confirm_label:str; on_confirm:Callable[[],None]; focus_cancel:bool=True
    def handle(self,action:MenuAction)->bool:
        if action in {MenuAction.LEFT,MenuAction.RIGHT,MenuAction.UP,MenuAction.DOWN}:self.focus_cancel=not self.focus_cancel;return True
        if action is MenuAction.BACK:self.focus_cancel=True;return False
        if action is MenuAction.CONFIRM:
            if not self.focus_cancel:self.on_confirm()
            return False
        return True

def draw_menu(surface:pygame.Surface,title_font:pygame.font.Font,font:pygame.font.Font,small:pygame.font.Font,title:str,menu:Menu,subtitle:str="",footer:str="")->None:
    compact=len(menu.items)>=7; panel=pygame.Rect(350,55 if compact else 105,580,610 if compact else 520);pygame.draw.rect(surface,(11,17,34,225),panel,border_radius=24);pygame.draw.rect(surface,(230,151,70),panel,3,border_radius=24)
    image=title_font.render(title,True,(255,218,143));surface.blit(image,image.get_rect(center=(640,102 if compact else 155)))
    if subtitle:
        sub=small.render(subtitle,True,(190,202,221));surface.blit(sub,sub.get_rect(center=(640,140 if compact else 196)))
    y=170 if compact else 235; step=48 if compact else 62
    for index,item in enumerate(menu.items):
        focused=index==menu.focus; color=(255,214,117) if focused else (215,222,235) if item.enabled else (104,111,126)
        rect=pygame.Rect(400,y-8,480,54)
        if focused:pygame.draw.rect(surface,(89,51,42),rect,border_radius=12);pygame.draw.rect(surface,(255,169,72),rect,3,border_radius=12)
        marker="◆ " if focused else "  "; label=font.render(marker+item.label,True,color);surface.blit(label,(420,y))
        if item.detail:surface.blit(small.render(item.detail,True,color),(680,y+5))
        y+=step
    if footer:
        hint=small.render(footer,True,(172,188,214));surface.blit(hint,hint.get_rect(center=(640,panel.bottom-18)))

def draw_dialog(surface:pygame.Surface,title_font:pygame.font.Font,font:pygame.font.Font,dialog:ConfirmationDialog)->None:
    shade=pygame.Surface(surface.get_size(),pygame.SRCALPHA);shade.fill((0,0,0,165));surface.blit(shade,(0,0));panel=pygame.Rect(330,220,620,280);pygame.draw.rect(surface,(20,24,43),panel,border_radius=20);pygame.draw.rect(surface,(236,146,74),panel,3,border_radius=20)
    surface.blit(title_font.render(dialog.title,True,(255,210,127)),(380,260));surface.blit(font.render(dialog.message,True,(220,225,237)),(380,325))
    labels=(dialog.confirm_label,"CANCEL")
    for i,label in enumerate(labels):
        cancel=i==1;focused=dialog.focus_cancel==cancel;rect=pygame.Rect(390+i*270,400,230,55);pygame.draw.rect(surface,(112,54,44) if not cancel else (57,66,86),rect,border_radius=10)
        if focused:pygame.draw.rect(surface,(255,190,82),rect,4,border_radius=10)
        text=font.render(label,True,(255,239,203));surface.blit(text,text.get_rect(center=rect.center))
