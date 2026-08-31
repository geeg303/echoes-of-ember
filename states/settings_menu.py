"""Reusable immediate-apply application settings menu."""
from __future__ import annotations
from core.audio_manager import AudioBus
from core.settings_manager import ApplicationSettings,SettingsManager
from systems.effects_system import EffectQuality
from ui.menu import ConfirmationDialog,Menu,MenuAction,MenuItem,draw_dialog,draw_menu
class SettingsController:
    def __init__(self,host,manager:SettingsManager,settings:ApplicationSettings,audio,effects,title,font,small)->None:
        self.host=host;self.manager=manager;self.settings=settings;self.audio=audio;self.effects=effects;self.title=title;self.font=font;self.small=small;self.menu=Menu();self.dialog=None;self._rebuild()
    def _rebuild(self,preferred=None)->None:
        a=self.settings.audio;self.menu.set_items([MenuItem("MASTER VOLUME","master",detail=f"{a.master_volume:.0%}"),MenuItem("MUSIC VOLUME","music",detail=f"{a.music_volume:.0%}"),MenuItem("SFX VOLUME","sfx",detail=f"{a.sfx_volume:.0%}"),MenuItem("AMBIENCE VOLUME","ambience",detail=f"{a.ambience_volume:.0%}"),MenuItem("UI VOLUME","ui",detail=f"{a.ui_volume:.0%}"),MenuItem("MUTE","mute",detail="ON" if a.muted else "OFF"),MenuItem("EFFECTS QUALITY","effects",detail=self.settings.effects_quality.upper()),MenuItem("FULLSCREEN","fullscreen",detail="ON" if self.settings.fullscreen else "OFF"),MenuItem("RESET TO DEFAULTS","reset"),MenuItem("BACK","back")],preferred)
    def handle(self,action:MenuAction)->None:
        if self.dialog:
            keep=self.dialog.handle(action)
            if not keep:self.dialog=None
            return
        if action in {MenuAction.UP,MenuAction.DOWN}:self.menu.move(-1 if action is MenuAction.UP else 1);self.audio.play_sound("ui_move");return
        if action is MenuAction.BACK:self.close();return
        item=self.menu.focused
        if not item:return
        if action in {MenuAction.LEFT,MenuAction.RIGHT} and item.item_id in {"master","music","sfx","ambience","ui","effects"}:
            direction=-1 if action is MenuAction.LEFT else 1;self._adjust(item.item_id,direction);return
        if action is MenuAction.CONFIRM:
            if item.item_id=="mute":self.audio.set_muted(not self.audio.settings.muted);self.settings.audio.muted=self.audio.settings.muted
            elif item.item_id=="effects":self._adjust("effects",1)
            elif item.item_id=="fullscreen":self.settings.fullscreen=not self.settings.fullscreen;self.host.set_fullscreen(self.settings.fullscreen)
            elif item.item_id=="reset":self.dialog=ConfirmationDialog("RESET SETTINGS?","Campaign saves are not affected.","RESET",self._reset)
            elif item.item_id=="back":self.close();return
            self.audio.play_sound("ui_confirm");self._rebuild(item.item_id)
    def _adjust(self,item_id:str,direction:int)->None:
        if item_id=="effects":
            values=("full","reduced","off");self.settings.effects_quality=values[(values.index(self.settings.effects_quality)+direction)%3];self.effects.set_quality(EffectQuality(self.settings.effects_quality))
        else:
            bus={"master":AudioBus.MASTER,"music":AudioBus.MUSIC,"sfx":AudioBus.SFX,"ambience":AudioBus.AMBIENCE,"ui":AudioBus.UI}[item_id];current={"master":self.audio.settings.master_volume,"music":self.audio.settings.music_volume,"sfx":self.audio.settings.sfx_volume,"ambience":self.audio.settings.ambience_volume,"ui":self.audio.settings.ui_volume}[item_id];self.audio.set_volume(bus,current+direction*.05)
        self.audio.play_sound("ui_move");self._rebuild(item_id)
    def _reset(self)->None:
        defaults=self.manager.reset();self.settings.audio=defaults.audio;self.settings.effects_quality=defaults.effects_quality;self.settings.fullscreen=defaults.fullscreen;self.audio.settings=defaults.audio;self.audio._apply_volumes();self.effects.set_quality(EffectQuality.FULL);self.host.set_fullscreen(False);self._rebuild("reset")
    def close(self)->None:self.manager.save(self.settings);self.audio.play_sound("ui_cancel");self.host.close_settings()
    def draw(self,surface)->None:
        surface.fill((12,18,34));draw_menu(surface,self.title,self.font,self.small,"SETTINGS",self.menu,"Immediate application · Saved on exit")
        if self.dialog:draw_dialog(surface,self.title,self.font,self.dialog)
