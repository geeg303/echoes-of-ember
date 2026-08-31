"""Versioned application preferences, separate from campaign save slots."""
from __future__ import annotations
from dataclasses import dataclass,field
import json,math,os
from pathlib import Path
from core.audio_manager import AudioSettings
from core.save_manager import default_save_root
SETTINGS_SCHEMA_VERSION=1
@dataclass(slots=True)
class ApplicationSettings:
    audio:AudioSettings=field(default_factory=AudioSettings)
    effects_quality:str="full"
    fullscreen:bool=False
    def to_dict(self)->dict[str,object]:
        return {"schema_version":SETTINGS_SCHEMA_VERSION,"audio":{"master_volume":self.audio.master_volume,"music_volume":self.audio.music_volume,"sfx_volume":self.audio.sfx_volume,"ambience_volume":self.audio.ambience_volume,"ui_volume":self.audio.ui_volume,"muted":self.audio.muted},"visual":{"effects_quality":self.effects_quality},"display":{"fullscreen":self.fullscreen}}
class SettingsManager:
    def __init__(self,path:Path|None=None)->None:self.path=path or default_save_root().parent/"settings.json";self.path.parent.mkdir(parents=True,exist_ok=True);self.last_warning=""
    def load(self)->ApplicationSettings:
        if not self.path.exists():return ApplicationSettings()
        try:
            raw=json.loads(self.path.read_text(encoding="utf-8"))
            if raw.get("schema_version")!=SETTINGS_SCHEMA_VERSION:raise ValueError("unsupported settings version")
            if not isinstance(raw,dict):raise TypeError("settings root must be an object")
            audio=raw.get("audio",{});visual=raw.get("visual",{});display=raw.get("display",{})
            if not all(isinstance(section,dict) for section in (audio,visual,display)):raise TypeError("settings sections must be objects")
            def volume(name:str,default:float)->float:
                value=audio.get(name,default)
                if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError(f"invalid {name}")
                return max(0.0,min(1.0,float(value)))
            muted=audio.get("muted",False);fullscreen=display.get("fullscreen",False)
            if not isinstance(muted,bool) or not isinstance(fullscreen,bool):raise TypeError("toggle settings must be booleans")
            quality=visual.get("effects_quality","full")
            if quality not in {"full","reduced","off"}:raise ValueError("invalid effects quality")
            return ApplicationSettings(AudioSettings(master_volume=volume("master_volume",1),music_volume=volume("music_volume",.75),sfx_volume=volume("sfx_volume",.85),ambience_volume=volume("ambience_volume",.60),ui_volume=volume("ui_volume",.80),muted=muted),quality,fullscreen)
        except (OSError,json.JSONDecodeError,TypeError,ValueError) as exc:self.last_warning=str(exc);return ApplicationSettings()
    def save(self,settings:ApplicationSettings)->None:
        temp=self.path.with_suffix(".json.tmp");payload=json.dumps(settings.to_dict(),indent=2,sort_keys=True)+"\n";temp.write_text(payload,encoding="utf-8");os.replace(temp,self.path)
    def reset(self)->ApplicationSettings:
        settings=ApplicationSettings();self.save(settings);return settings
