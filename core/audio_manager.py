"""Central, optional, gameplay-independent audio presentation service."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, IntEnum
import json, logging
from pathlib import Path
from typing import Any
import pygame
from settings import ASSET_ROOT, PROJECT_ROOT
LOGGER=logging.getLogger(__name__)

class AudioBus(str,Enum):
    MASTER="master"; MUSIC="music"; SFX="sfx"; AMBIENCE="ambience"; UI="ui"; VOICE="voice"
class AudioPriority(IntEnum):
    AMBIENT=0; NORMAL=1; IMPORTANT=2; CRITICAL=3
@dataclass(slots=True)
class AudioSettings:
    master_volume:float=1.0; music_volume:float=.75; sfx_volume:float=.85; ambience_volume:float=.60; ui_volume:float=.80; voice_volume:float=.85; muted:bool=False
    def __post_init__(self)->None:
        for name in ("master_volume","music_volume","sfx_volume","ambience_volume","ui_volume","voice_volume"): setattr(self,name,_clamp(getattr(self,name)))
    def volume_for(self,bus:AudioBus)->float:
        if self.muted:return 0.0
        return self.master_volume*{AudioBus.MASTER:1.0,AudioBus.MUSIC:self.music_volume,AudioBus.SFX:self.sfx_volume,AudioBus.AMBIENCE:self.ambience_volume,AudioBus.UI:self.ui_volume,AudioBus.VOICE:self.voice_volume}[bus]
    def set_volume(self,bus:AudioBus,value:float)->None:
        value=_clamp(value)
        if bus is AudioBus.MASTER:self.master_volume=value
        else:setattr(self,f"{bus.value}_volume",value)
@dataclass(frozen=True,slots=True)
class SoundDefinition:
    sound_id:str; path:str; category:AudioBus; base_volume:float; priority:AudioPriority; max_instances:int; cooldown:float; loop:bool=False
@dataclass(frozen=True,slots=True)
class MusicDefinition:
    track_id:str; path:str; base_volume:float; loop:bool; fade_in:float; fade_out:float
@dataclass(frozen=True,slots=True)
class AudioEvent:
    kind:str; audio_id:str; played:bool
@dataclass(slots=True)
class SoundPlayback:
    channel:Any; definition:SoundDefinition; left_factor:float=1.0; right_factor:float=1.0
@dataclass(slots=True)
class AmbiencePlayback:
    owner_id:str; sound_id:str; channel:Any

def _clamp(value:float)->float:return max(0.0,min(1.0,float(value)))

def load_audio_catalog(path:Path)->tuple[dict[str,SoundDefinition],dict[str,MusicDefinition]]:
    raw=json.loads(path.read_text(encoding="utf-8")); sounds={}; music={}
    for item in raw.get("sounds",[]):
        try: bus=AudioBus(item["category"]); priority=AudioPriority(int(item["priority"])); sound_id=str(item["id"])
        except (KeyError,ValueError,TypeError) as exc: raise ValueError(f"invalid sound definition: {item}") from exc
        if sound_id in sounds or not sound_id: raise ValueError(f"duplicate/empty sound ID: {sound_id}")
        sounds[sound_id]=SoundDefinition(sound_id,str(item["path"]),bus,_clamp(item.get("base_volume",1)),priority,max(1,int(item.get("max_instances",1))),max(0,float(item.get("cooldown",0))),bool(item.get("loop",False)))
    for item in raw.get("music",[]):
        track_id=str(item.get("id",""))
        if not track_id or track_id in music: raise ValueError(f"duplicate/empty music ID: {track_id}")
        music[track_id]=MusicDefinition(track_id,str(item["path"]),_clamp(item.get("base_volume",1)),bool(item.get("loop",True)),max(0,float(item.get("fade_in",0))),max(0,float(item.get("fade_out",0))))
    return sounds,music

class AudioManager:
    """Owns mixer resources; all methods are safe no-ops when unavailable."""
    def __init__(self,*,asset_root:Path=ASSET_ROOT,catalog_path:Path|None=None,settings:AudioSettings|None=None,enabled:bool=True,channel_count:int=24)->None:
        self.asset_root=asset_root; self.settings=settings or AudioSettings(); self.enabled=enabled; self.available=False; self.disabled_reason=""
        self.sounds,self.music=load_audio_catalog(catalog_path or PROJECT_ROOT/"data"/"audio"/"audio.json")
        self._cache:dict[str,pygame.mixer.Sound|None]={}; self._failed:set[str]=set(); self._cooldowns:dict[str,float]={}; self._ambience:dict[str,AmbiencePlayback]={}; self._active_sfx:list[SoundPlayback]=[]
        self.current_music:str|None=None; self.pending_music:str|None=None; self._music_transition=0.0; self._clock=0.0; self.events:list[AudioEvent]=[]; self.peak_channels=0
        if not enabled:self.disabled_reason="disabled by runtime setting"; return
        try:
            if not pygame.mixer.get_init():pygame.mixer.init(frequency=22050,size=-16,channels=2,buffer=512)
            pygame.mixer.set_num_channels(channel_count); self.available=True; self._apply_volumes()
        except (pygame.error,ImportError,NotImplementedError,OSError) as exc:
            self.disabled_reason=str(exc); LOGGER.warning("Audio disabled: %s",exc)
    def update(self,dt:float)->None:
        self._clock+=max(0,dt)
        if self.available and pygame.mixer.get_init(): self._active_sfx=[item for item in self._active_sfx if item.channel.get_busy()]
        if self.pending_music:
            self._music_transition=max(0,self._music_transition-dt)
            if self._music_transition<=0:self._start_music(self.pending_music); self.pending_music=None
        if self.available:self.peak_channels=max(self.peak_channels,pygame.mixer.get_busy() and sum(pygame.mixer.Channel(i).get_busy() for i in range(pygame.mixer.get_num_channels())) or 0)
    def effective_volume(self,bus:AudioBus,base:float=1.0)->float:return _clamp(self.settings.volume_for(bus)*_clamp(base))
    def set_volume(self,bus:AudioBus,value:float)->None:self.settings.set_volume(bus,value); self._apply_volumes()
    def set_muted(self,muted:bool)->None:self.settings.muted=bool(muted); self._apply_volumes()
    def toggle_mute(self)->bool:self.set_muted(not self.settings.muted); return self.settings.muted
    def play_sound(self,sound_id:str,*,position:tuple[float,float]|None=None,listener_x:float|None=None,max_distance:float=1400)->bool:
        definition=self.sounds.get(sound_id)
        if definition is None:self._warn_once(sound_id,"unknown sound ID"); self._record("sound",sound_id,False); return False
        if not self.available or self._clock<self._cooldowns.get(sound_id,0):self._record("sound",sound_id,False); return False
        sound=self._load_sound(definition)
        if sound is None or sound.get_num_channels()>=definition.max_instances:self._record("sound",sound_id,False); return False
        channel=pygame.mixer.find_channel(force=definition.priority>=AudioPriority.IMPORTANT)
        if channel is None:self._record("sound",sound_id,False); return False
        left_factor=right_factor=1.0
        if position is not None and listener_x is not None:
            delta=max(-1.0,min(1.0,(position[0]-listener_x)/max(1,max_distance))); attenuation=max(.35,1-abs(position[0]-listener_x)/max_distance*.65); left_factor=attenuation*(1-max(0,delta)*.65); right_factor=attenuation*(1-max(0,-delta)*.65)
        volume=self.effective_volume(definition.category,definition.base_volume); channel.set_volume(volume*left_factor,volume*right_factor); channel.play(sound,loops=-1 if definition.loop else 0); self._active_sfx.append(SoundPlayback(channel,definition,left_factor,right_factor)); self._cooldowns[sound_id]=self._clock+definition.cooldown; self._record("sound",sound_id,True); return True
    def play_music(self,track_id:str,*,immediate:bool=False)->bool:
        if track_id not in self.music:self._warn_once(track_id,"unknown music ID"); self._record("music",track_id,False); return False
        if track_id==self.current_music or track_id==self.pending_music:return True
        if not self.available:self.current_music=track_id; self._record("music",track_id,False); return False
        if self.current_music and not immediate:
            fade=self.music[self.current_music].fade_out; pygame.mixer.music.fadeout(round(fade*1000)); self.pending_music=track_id; self._music_transition=fade; return True
        return self._start_music(track_id)
    def _start_music(self,track_id:str)->bool:
        d=self.music[track_id]; path=self.asset_root/d.path
        try: pygame.mixer.music.load(path); pygame.mixer.music.set_volume(self.effective_volume(AudioBus.MUSIC,d.base_volume)); pygame.mixer.music.play(-1 if d.loop else 0,fade_ms=round(d.fade_in*1000)); self.current_music=track_id; self._record("music",track_id,True); return True
        except (FileNotFoundError,pygame.error,OSError) as exc:self._warn_once(track_id,f"music unavailable: {exc}"); self.current_music=track_id; self._record("music",track_id,False); return False
    def stop_music(self,fade:float=0)->None:
        if self.available and pygame.mixer.get_init():
            if fade>0:pygame.mixer.music.fadeout(round(fade*1000))
            else:pygame.mixer.music.stop()
        self.current_music=None; self.pending_music=None; self._music_transition=0
    def start_ambience(self,owner_id:str,sound_id:str)->bool:
        existing=self._ambience.get(owner_id)
        if existing and existing.sound_id==sound_id:return True
        self.stop_ambience(owner_id); d=self.sounds.get(sound_id)
        if d is None or d.category is not AudioBus.AMBIENCE:self._warn_once(sound_id,"invalid ambience ID"); return False
        if not self.available:self._ambience[owner_id]=AmbiencePlayback(owner_id,sound_id,None); self._record("ambience",sound_id,False); return False
        sound=self._load_sound(d); channel=pygame.mixer.find_channel() if sound else None
        if channel is None:self._record("ambience",sound_id,False); return False
        channel.set_volume(self.effective_volume(AudioBus.AMBIENCE,d.base_volume)); channel.play(sound,loops=-1); self._ambience[owner_id]=AmbiencePlayback(owner_id,sound_id,channel); self._record("ambience",sound_id,True); return True
    def stop_ambience(self,owner_id:str)->None:
        playback=self._ambience.pop(owner_id,None)
        if playback and playback.channel and pygame.mixer.get_init(): playback.channel.stop()
    def stop_all_ambience(self)->None:
        for owner in tuple(self._ambience):self.stop_ambience(owner)
    def reset_context(self)->None:
        self.stop_all_ambience()
        if self.available and pygame.mixer.get_init():
            for index in range(pygame.mixer.get_num_channels()):pygame.mixer.Channel(index).stop()
        self._cooldowns.clear(); self._active_sfx.clear()
    def _load_sound(self,d:SoundDefinition):
        if d.sound_id not in self._cache:
            try:self._cache[d.sound_id]=pygame.mixer.Sound(self.asset_root/d.path)
            except (FileNotFoundError,pygame.error,OSError) as exc:self._cache[d.sound_id]=None; self._warn_once(d.sound_id,f"sound unavailable: {exc}")
        return self._cache[d.sound_id]
    def _apply_volumes(self)->None:
        if not self.available:return
        if self.current_music and self.current_music in self.music:pygame.mixer.music.set_volume(self.effective_volume(AudioBus.MUSIC,self.music[self.current_music].base_volume))
        for playback in self._active_sfx:
            volume=self.effective_volume(playback.definition.category,playback.definition.base_volume)
            if self.settings.muted: playback.channel.set_volume(0.0)
            else: playback.channel.set_volume(volume*playback.left_factor,volume*playback.right_factor)
        for playback in self._ambience.values():
            if playback.channel:
                d=self.sounds[playback.sound_id]; playback.channel.set_volume(self.effective_volume(AudioBus.AMBIENCE,d.base_volume))
    def _warn_once(self,key:str,message:str)->None:
        if key not in self._failed:self._failed.add(key); LOGGER.warning("Audio %s: %s",key,message)
    def _record(self,kind:str,audio_id:str,played:bool)->None:
        self.events.append(AudioEvent(kind,audio_id,played)); del self.events[:-256]
    @property
    def ambience_owners(self)->tuple[str,...]:return tuple(self._ambience)
    @property
    def active_channels(self)->int:
        if not self.available:return 0
        return sum(pygame.mixer.Channel(i).get_busy() for i in range(pygame.mixer.get_num_channels()))
    def shutdown(self)->None:
        self.reset_context(); self.stop_music()
        self.available=False
