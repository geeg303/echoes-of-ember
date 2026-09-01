"""Title, main menu, credits, and SaveManager-backed three-slot front end."""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Protocol
import math,pygame
from core.save_manager import SaveManager,SlotState,SlotSummary
from core.input_manager import Action
from ui.menu import ConfirmationDialog,Menu,MenuAction,MenuItem,draw_dialog,draw_menu
class FrontendScreen(str,Enum):MAIN="main";SLOTS="slots";SLOT_ACTION="slot_action";SETTINGS="settings";CREDITS="credits"
class FrontendHost(Protocol):
    running:bool
    def start_campaign(self,slot_id:int,new_game:bool=False)->None:...
    def open_settings(self,parent:str)->None:...
class FrontendController:
    def __init__(self,host:FrontendHost,manager:SaveManager,title:pygame.font.Font,font:pygame.font.Font,small:pygame.font.Font,audio)->None:
        self.host=host;self.manager=manager;self.title_font=title;self.font=font;self.small=small;self.audio=audio;self.screen=FrontendScreen.MAIN;self.menu=Menu();self.dialog:ConfirmationDialog|None=None;self.slot_mode="load";self.selected_slot=1;self.age=0.;self.summaries:tuple[SlotSummary,...]=();self.refresh_slots();self._main()
    def refresh_slots(self)->None:self.summaries=self.manager.list_slots()
    @property
    def continue_slot(self)->int|None:
        valid=[x for x in self.summaries if x.state in {SlotState.VALID,SlotState.RECOVERED}]
        if not valid:return None
        return max(valid,key=lambda x:x.updated_at or "").slot_id
    def _main(self)->None:
        self.screen=FrontendScreen.MAIN;c=self.continue_slot;self.menu.set_items([MenuItem("CONTINUE","continue",c is not None,"" if c else "NO SAVE"),MenuItem("NEW GAME","new"),MenuItem("LOAD GAME / SAVE SLOTS","load"),MenuItem("ACHIEVEMENTS","achievements"),MenuItem("SETTINGS","settings"),MenuItem("CREDITS","credits"),MenuItem("QUIT","quit")])
    def open_slots(self,mode:str)->None:self.slot_mode=mode;self.refresh_slots();self.screen=FrontendScreen.SLOTS;self.menu.set_items([MenuItem(f"SLOT {x.slot_id}",f"slot:{x.slot_id}",x.state is not SlotState.UNSUPPORTED_VERSION,self._summary(x)) for x in self.summaries]+[MenuItem("BACK","back")])
    def _summary(self,x:SlotSummary)->str:
        if x.state is SlotState.EMPTY:return "EMPTY"
        if x.state is SlotState.CORRUPT:return "CORRUPT — RESET AVAILABLE"
        if x.state is SlotState.UNSUPPORTED_VERSION:return "UNSUPPORTED NEWER SAVE"
        status="RECOVERED · " if x.state is SlotState.RECOVERED else ""
        return f"{status}{x.levels_completed}/5 · {format_play_time(x.play_time_seconds)}"
    def handle(self,action:MenuAction)->None:
        if self.dialog:
            keep=self.dialog.handle(action)
            if not keep:self.dialog=None
            self.audio.play_sound("ui_confirm" if action is MenuAction.CONFIRM else "ui_cancel" if action is MenuAction.BACK else "ui_move")
            return
        if action in {MenuAction.UP,MenuAction.DOWN}:
            moved=self.menu.move(-1 if action is MenuAction.UP else 1);self.audio.play_sound("ui_move" if moved else "ui_locked");return
        if action is MenuAction.BACK:
            if self.screen is FrontendScreen.MAIN:self.host.running=False
            elif self.screen in {FrontendScreen.SLOTS,FrontendScreen.CREDITS,FrontendScreen.SETTINGS}:self._main()
            elif self.screen is FrontendScreen.SLOT_ACTION:self.open_slots(self.slot_mode)
            self.audio.play_sound("ui_cancel");return
        if action is not MenuAction.CONFIRM:return
        item=self.menu.focused
        if not item or not item.enabled:self.audio.play_sound("ui_locked");return
        self.audio.play_sound("ui_confirm");self._activate(item.item_id)
    def _activate(self,item_id:str)->None:
        if self.screen is FrontendScreen.MAIN:
            if item_id=="continue":self.host.start_campaign(self.continue_slot or 1)
            elif item_id=="new":self.open_slots("new")
            elif item_id=="load":self.open_slots("load")
            elif item_id=="achievements":self.host.open_achievements()
            elif item_id=="settings":self.host.open_settings("frontend")
            elif item_id=="credits":self.screen=FrontendScreen.CREDITS;self.menu.set_items([MenuItem("BACK","back")])
            elif item_id=="quit":self.host.running=False
        elif self.screen is FrontendScreen.SLOTS:
            if item_id=="back":self._main();return
            slot=int(item_id.split(":")[1]);summary=self.summaries[slot-1];self.selected_slot=slot
            if self.slot_mode=="new":
                if summary.state is SlotState.EMPTY:self.host.start_campaign(slot,True)
                else:self.dialog=ConfirmationDialog(f"OVERWRITE SLOT {slot}?","Existing progress will be deleted.","OVERWRITE",lambda:self.host.start_campaign(slot,True))
            elif summary.state in {SlotState.VALID,SlotState.RECOVERED}:self.screen=FrontendScreen.SLOT_ACTION;self.menu.set_items([MenuItem("PLAY","play"),MenuItem("DELETE","delete"),MenuItem("BACK","back")])
            elif summary.state is SlotState.CORRUPT:self.screen=FrontendScreen.SLOT_ACTION;self.menu.set_items([MenuItem("RESET SLOT","reset"),MenuItem("DELETE","delete"),MenuItem("BACK","back")])
        elif self.screen is FrontendScreen.SLOT_ACTION:
            if item_id=="play":self.host.start_campaign(self.selected_slot)
            elif item_id=="reset":self.dialog=ConfirmationDialog(f"RESET SLOT {self.selected_slot}?","Corrupt data will be removed.","RESET",lambda:self.host.start_campaign(self.selected_slot,True))
            elif item_id=="delete":self.dialog=ConfirmationDialog(f"DELETE SLOT {self.selected_slot}?","This permanently removes this save.","DELETE",self._delete_selected)
            elif item_id=="back":self.open_slots(self.slot_mode)
        elif item_id=="back":self._main()
    def _delete_selected(self)->None:self.manager.delete(self.selected_slot);self.open_slots(self.slot_mode)
    def update(self,dt:float)->None:self.age+=dt
    def draw(self,surface:pygame.Surface)->None:
        self._background(surface)
        if self.screen is FrontendScreen.CREDITS:
            draw_menu(surface,self.title_font,self.font,self.small,"CREDITS",self.menu,"Echoes of Ember · Built with Python and Pygame",self._footer())
            lines=("Original game design and development","Procedural temporary art, effects, music and audio","No external commercial assets")
            for i,line in enumerate(lines):surface.blit(self.small.render(line,True,(210,215,228)),(430,245+i*42))
        else:draw_menu(surface,self.title_font,self.font,self.small,"ECHOES OF EMBER" if self.screen is FrontendScreen.MAIN else self.screen.value.replace("_"," ").upper(),self.menu,"Nova's journey through Verdant Reaches",self._footer())
        if self.dialog:draw_dialog(surface,self.title_font,self.font,self.dialog)
    def _footer(self)->str:
        i=self.host.input;return f"[{i.get_prompt(Action.CONFIRM)}] SELECT   [{i.get_prompt(Action.BACK)}] BACK"
    def _background(self,surface:pygame.Surface)->None:
        surface.fill((10,15,30));pygame.draw.circle(surface,(95,38,28),(640,500),240);pygame.draw.circle(surface,(231,98,48),(640,500),90)
        for i in range(24):
            x=(i*197)%1280;y=80+(i*83)%540+round(math.sin(self.age*1.1+i)*8);pygame.draw.circle(surface,(255,150,67),(x,y),2+(i%3))
        pygame.draw.polygon(surface,(19,30,36),[(0,560),(180,410),(330,560),(530,390),(730,560),(920,420),(1100,560),(1280,440),(1280,720),(0,720)])
def format_play_time(seconds:float)->str:
    total=max(0,int(seconds));return f"{total//3600:02}:{(total%3600)//60:02}:{total%60:02}"
