"""NPC catalog loading, validation, variant selection, and world management."""
from __future__ import annotations
import json,math,re
from pathlib import Path
from entities.npc import NPC,NPCVariant
from systems.dialogue_system import DialogueDataError,_conditions,condition_matches,load_dialogue
ID=re.compile(r"^[a-z][a-z0-9_]{1,63}$")
class NPCDataError(ValueError):
 """Authored NPC catalog data is unsafe or malformed."""
def load_npc_catalog(path:Path,level_id:str,known_dialogues:set[str],bounds:tuple[int,int]|None=None):
 try:raw=json.loads(path.read_text(encoding="utf-8"))
 except (OSError,json.JSONDecodeError) as exc:raise NPCDataError(str(exc)) from exc
 if not isinstance(raw,list):raise NPCDataError("NPC catalog must be a list")
 seen=set();result=[]
 for i,item in enumerate(raw):
  if not isinstance(item,dict):raise NPCDataError(f"NPC {i} must be an object")
  npc_id=item.get("id");position=item.get("position");variants=item.get("dialogues")
  if not isinstance(npc_id,str) or not ID.fullmatch(npc_id) or npc_id in seen:raise NPCDataError("NPC IDs must be unique and valid")
  seen.add(npc_id)
  if item.get("level_id")!=level_id:raise NPCDataError(f"NPC {npc_id} has wrong level")
  if not isinstance(position,list) or len(position)!=2 or not all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and x>=0 for x in position):raise NPCDataError(f"NPC {npc_id} position malformed")
  if bounds and (position[0] >= bounds[0] or position[1] >= bounds[1]):raise NPCDataError(f"NPC {npc_id} position outside level bounds")
  if not isinstance(variants,list) or not variants:raise NPCDataError(f"NPC {npc_id} dialogues missing")
  parsed=[]
  for variant in variants:
   if not isinstance(variant,dict) or variant.get("dialogue_id") not in known_dialogues or not isinstance(variant.get("priority",0),int):raise NPCDataError(f"NPC {npc_id} dialogue variant malformed")
   conditions=variant.get("conditions",[])
   try: parsed_conditions=_conditions(conditions,f"NPC {npc_id}")
   except DialogueDataError as exc: raise NPCDataError(str(exc)) from exc
   parsed.append(NPCVariant(variant["dialogue_id"],variant.get("priority",0),parsed_conditions))
  result.append(NPC(npc_id,str(item.get("display_name",npc_id)),position,float(item.get("interaction_radius",72)),str(item.get("style","default")),str(item.get("facing","right")),tuple(parsed)))
 return result
class NPCSystem:
 def __init__(self,npcs,progress):self.npcs=npcs;self.progress=progress;self.active_npc=None
 @classmethod
 def load(cls,root:Path,level_id:str,progress,bounds:tuple[int,int]|None=None):
  dialogue_paths=list((root/"dialogue").glob("*.json"));loaded=[load_dialogue(x) for x in dialogue_paths];definitions={d.dialogue_id:d for d in loaded};
  if len(definitions)!=len(loaded):raise NPCDataError("dialogue IDs must be globally unique")
  path=root/"npcs"/f"{level_id}.json";npcs=load_npc_catalog(path,level_id,set(definitions),bounds) if path.exists() else [];return cls(npcs,progress),definitions
 def update(self,dt,player_rect):
  for npc in self.npcs:npc.update(dt,player_rect)
 def nearest(self,player_rect):
  candidates=[n for n in self.npcs if n.in_range(player_rect)]
  return min(candidates,key=lambda n:abs(n.rect.centerx-player_rect.centerx)) if candidates else None
 def choose_dialogue(self,npc):
  matches=[v for v in npc.variants if all(condition_matches(c,self.progress) for c in v.conditions)]
  return max(matches,key=lambda v:(v.priority,v.dialogue_id)).dialogue_id if matches else None
 def begin(self,player_rect,dialogue):
  npc=self.nearest(player_rect)
  if npc is None:return False
  selected=self.choose_dialogue(npc)
  if selected is None:return False
  if dialogue.start(selected,npc.npc_id):self.active_npc=npc;npc.talking=True;npc.update(0,player_rect);return True
  return False
 def end(self):
  if self.active_npc:self.active_npc.talking=False
  self.active_npc=None
 def draw(self,surface,view,offset,player_rect,prompt,prompt_font):
  nearby=self.nearest(player_rect) if self.active_npc is None else None
  for npc in self.npcs:
   if view.inflate(160,120).colliderect(npc.rect):npc.draw(surface,offset,prompt if npc is nearby else None,prompt_font)
