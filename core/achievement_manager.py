"""Profile-wide achievement persistence and semantic event observation."""
from __future__ import annotations
from dataclasses import dataclass,field
import json,logging,math,os
from pathlib import Path
from core.save_manager import default_save_root
from systems.save_data import utc_now
from systems.achievement_system import AchievementDefinition,COUNTERS,SETS,condition_matches,load_achievement_definitions
LOGGER=logging.getLogger(__name__);PROFILE_SCHEMA_VERSION=1;MAX_COUNTER=1_000_000_000
@dataclass(slots=True)
class AchievementProfile:
 unlocked:dict[str,str]=field(default_factory=dict);counters:dict[str,int]=field(default_factory=dict);sets:dict[str,set[str]]=field(default_factory=dict);flags:set[str]=field(default_factory=set);dirty:bool=False
 def to_dict(self):return {"schema_version":1,"unlocked":{k:{"unlocked_at":v} for k,v in sorted(self.unlocked.items())},"progress":{"counters":dict(sorted(self.counters.items())),"sets":{k:sorted(v) for k,v in sorted(self.sets.items())},"flags":sorted(self.flags)}}
class AchievementProfileError(ValueError):pass
class AchievementStore:
 def __init__(self,path:Path|None=None):self.path=path or default_save_root().parent/"achievements.json";self.path.parent.mkdir(parents=True,exist_ok=True);self.status="empty";self.writable=True
 def load(self,known_ids:set[str])->AchievementProfile:
  if not self.path.exists():return AchievementProfile()
  try:
   raw=json.loads(self.path.read_text());version=raw.get("schema_version") if isinstance(raw,dict) else None
   if version!=1:
    self.status="unsupported" if isinstance(version,int) and version>1 else "corrupt";self.writable=False;raise AchievementProfileError("unsupported profile schema" if self.status=="unsupported" else "invalid profile schema")
   unlocked=raw.get("unlocked");progress=raw.get("progress")
   if not isinstance(unlocked,dict) or not isinstance(progress,dict):raise AchievementProfileError("profile sections malformed")
   parsed={}
   for aid,value in unlocked.items():
    if aid not in known_ids or not isinstance(value,dict) or not isinstance(value.get("unlocked_at"),str):raise AchievementProfileError("profile unlock malformed")
    parsed[aid]=value["unlocked_at"]
   counters=progress.get("counters",{});sets=progress.get("sets",{});flags=progress.get("flags",[])
   if not isinstance(counters,dict) or any(k not in COUNTERS or not isinstance(v,int) or isinstance(v,bool) or not 0<=v<=MAX_COUNTER for k,v in counters.items()):raise AchievementProfileError("profile counters malformed")
   if not isinstance(sets,dict) or any(k not in SETS or not isinstance(v,list) or len(v)!=len(set(v)) or not all(isinstance(x,str) and x for x in v) for k,v in sets.items()):raise AchievementProfileError("profile sets malformed")
   if not isinstance(flags,list) or len(flags)!=len(set(flags)) or not all(isinstance(x,str) for x in flags):raise AchievementProfileError("profile flags malformed")
   self.status="valid";return AchievementProfile(parsed,dict(counters),{k:set(v) for k,v in sets.items()},set(flags))
  except (OSError,json.JSONDecodeError,AchievementProfileError) as exc:
   LOGGER.warning("Achievement profile unavailable: %s",exc);self.status=self.status if self.status in {"unsupported","corrupt"} else "corrupt";self.writable=False;return AchievementProfile()
 def save(self,profile:AchievementProfile):
  if not self.writable:return False
  temp=self.path.with_suffix(".json.tmp");payload=json.dumps(profile.to_dict(),indent=2,sort_keys=True)+"\n"
  with temp.open("w",encoding="utf-8") as handle:handle.write(payload);handle.flush();os.fsync(handle.fileno())
  os.replace(temp,self.path);profile.dirty=False;self.status="valid";return True
 def reset_profile(self):
  self.writable=True;self.status="empty";profile=AchievementProfile();self.save(profile);return profile
class AchievementManager:
 def __init__(self,definitions:tuple[AchievementDefinition,...],store:AchievementStore,enabled=True):
  self.definitions=definitions;self.by_id={x.id:x for x in definitions};self.store=store;self.enabled=enabled;self.profile=store.load(set(self.by_id)) if enabled else AchievementProfile();self.notifications=[];self.last_event=""
 @classmethod
 def create(cls,catalog:Path,profile_path:Path|None=None,enabled=True):return cls(load_achievement_definitions(catalog),AchievementStore(profile_path),enabled)
 @property
 def unlocked_count(self):return len(self.profile.unlocked)
 def emit(self,event:str,**payload):
  if not self.enabled:return ()
  self.last_event=event;self._observe(event,payload);new=[]
  for definition in self.definitions:
   if definition.id not in self.profile.unlocked and condition_matches(definition.condition,self.profile,event,payload):
    self.profile.unlocked[definition.id]=utc_now();new.append(definition);self.notifications.append(definition)
  if new:self.store.save(self.profile)
  return tuple(new)
 def _observe(self,event,p):
  counters={"ember_shard_collected":"ember_shards_collected","rare_crystal_collected":"rare_crystals_collected","secret_token_collected":"secret_tokens_collected","enemy_defeated":"enemies_defeated"}
  if event in counters:self.increment(counters[event])
  if event=="secret_discovered":self.add_unique("secret_ids_found",str(p.get("secret_id","")),"secrets_discovered")
  if event=="npc_conversation_completed":self.add_unique("npc_ids_met",str(p.get("npc_id","")),"npc_conversations_completed")
  if event=="level_completed":self.add_unique("completed_level_ids",str(p.get("level_id","")),"levels_completed")
  if event=="boss_defeated":self.add_unique("boss_ids_defeated",str(p.get("boss_id","")),"bosses_defeated")
  for flag in p.get("flags",()):self.profile.flags.add(flag);self.profile.dirty=True
 def increment(self,name,amount=1):self.profile.counters[name]=min(MAX_COUNTER,self.profile.counters.get(name,0)+max(0,amount));self.profile.dirty=True
 def add_unique(self,name,item,counter=None):
  if not item:return False
  values=self.profile.sets.setdefault(name,set())
  if item in values:return False
  values.add(item);self.profile.dirty=True
  if counter:self.increment(counter)
  return True
 def flush(self):
  if self.enabled and self.profile.dirty:self.store.save(self.profile)
 def reset_profile(self):self.profile=self.store.reset_profile();self.notifications.clear()
