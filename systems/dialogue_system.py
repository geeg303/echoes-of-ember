"""Validated, safe, data-driven dialogue graphs and runtime state."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import json,re
from pathlib import Path
from core.input_manager import Action
FLAG_RE=re.compile(r"^[a-z][a-z0-9_]{1,63}$")
CONDITIONS={"flag","flag_missing","level_completed","boss_defeated","secret_exit_found","secret_found","secret_token","world_completed"}
EFFECTS={"set_flag"}
class NodeType(str,Enum):LINE="line";CHOICE="choice";END="end";SYSTEM="system"
@dataclass(frozen=True,slots=True)
class Choice:label:str;target:str;conditions:tuple[dict,...]=();effects:tuple[dict,...]=()
@dataclass(frozen=True,slots=True)
class DialogueNode:node_id:str;kind:NodeType;speaker:str;text:str;next_id:str|None=None;choices:tuple[Choice,...]=();effects:tuple[dict,...]=()
@dataclass(frozen=True,slots=True)
class DialogueDefinition:dialogue_id:str;start:str;nodes:dict[str,DialogueNode]
class DialogueDataError(ValueError):
 """Authored dialogue data is unsafe or malformed."""
def _conditions(raw,where):
 if not isinstance(raw,list):raise DialogueDataError(f"{where} conditions must be a list")
 out=[]
 for item in raw:
  if not isinstance(item,dict) or item.get("type") not in CONDITIONS:
   raise DialogueDataError(f"{where} has unknown/malformed condition")
  kind=item["type"];value=item.get("value",True)
  string_kinds={"flag","flag_missing","level_completed","boss_defeated","secret_exit_found"}
  if (kind in string_kinds and (not isinstance(value,str) or not value)) or (kind not in string_kinds and not isinstance(value,bool)):
   raise DialogueDataError(f"{where} has unknown/malformed condition")
  if kind in {"flag","flag_missing"} and not FLAG_RE.fullmatch(value):
   raise DialogueDataError(f"{where} has invalid flag condition")
  out.append(item)
 return tuple(out)
def _effects(raw,where):
 if not isinstance(raw,list):raise DialogueDataError(f"{where} effects must be a list")
 out=[]
 for item in raw:
  if not isinstance(item,dict) or item.get("type") not in EFFECTS or not isinstance(item.get("value"),str) or not FLAG_RE.fullmatch(item["value"]):raise DialogueDataError(f"{where} has unknown/malformed effect")
  out.append(item)
 return tuple(out)
def load_dialogue(path:Path)->DialogueDefinition:
 try:raw=json.loads(path.read_text(encoding="utf-8"))
 except (OSError,json.JSONDecodeError) as exc:raise DialogueDataError(str(exc)) from exc
 if not isinstance(raw,dict) or not isinstance(raw.get("id"),str) or not raw["id"]:raise DialogueDataError("dialogue id must be non-empty")
 if not isinstance(raw.get("nodes"),list) or not raw["nodes"]:raise DialogueDataError("nodes must be a non-empty list")
 nodes={}
 for i,item in enumerate(raw["nodes"]):
  if not isinstance(item,dict):raise DialogueDataError(f"nodes[{i}] must be an object")
  node_id=item.get("id");kind_raw=item.get("type")
  if not isinstance(node_id,str) or not node_id or node_id in nodes:raise DialogueDataError("node IDs must be unique and non-empty")
  try:kind=NodeType(kind_raw)
  except ValueError as exc:raise DialogueDataError(f"unknown node type: {kind_raw}") from exc
  text=item.get("text","");speaker=item.get("speaker","")
  if not isinstance(text,str) or not isinstance(speaker,str) or len(text)>900:raise DialogueDataError(f"node {node_id} text/speaker malformed")
  choices=[]
  for c in item.get("responses",[]):
   if not isinstance(c,dict) or not isinstance(c.get("label"),str) or not c["label"] or not isinstance(c.get("target"),str):raise DialogueDataError(f"node {node_id} has malformed response")
   choices.append(Choice(c["label"],c["target"],_conditions(c.get("conditions",[]),node_id),_effects(c.get("effects",[]),node_id)))
  if kind is NodeType.CHOICE and not choices:raise DialogueDataError(f"choice node {node_id} has no responses")
  nodes[node_id]=DialogueNode(node_id,kind,speaker,text,item.get("next"),tuple(choices),_effects(item.get("effects",[]),node_id))
 start=raw.get("start")
 if start not in nodes:raise DialogueDataError("start node does not exist")
 for node in nodes.values():
  if node.next_id is not None and node.next_id not in nodes:raise DialogueDataError(f"node {node.node_id} next target missing")
  for choice in node.choices:
   if choice.target not in nodes:raise DialogueDataError(f"node {node.node_id} response target missing")
 reachable=set();stack=[start]
 while stack:
  item=stack.pop()
  if item in reachable:continue
  reachable.add(item);node=nodes[item]
  if node.next_id:stack.append(node.next_id)
  stack.extend(c.target for c in node.choices)
 if set(nodes)-reachable:raise DialogueDataError(f"unreachable nodes: {sorted(set(nodes)-reachable)}")
 return DialogueDefinition(raw["id"],start,nodes)

def condition_matches(condition:dict,progress)->bool:
 kind=condition["type"];value=condition.get("value",True)
 if kind=="flag":return value in progress.dialogue_flags
 if kind=="flag_missing":return value not in progress.dialogue_flags
 if kind=="level_completed":return value in progress.completed_levels_once
 if kind=="boss_defeated":return value in progress.defeated_bosses
 if kind=="secret_exit_found":return any(exit_id==value for _,exit_id in progress.discovered_secret_exits)
 if kind=="secret_found":return any(r.secrets_discovered>0 for r in progress.results.values()) is bool(value)
 if kind=="secret_token":return any(r.secret_tokens_collected>0 for r in progress.results.values()) is bool(value)
 if kind=="world_completed":return progress.world_completed_once is bool(value)
 return False
class DialogueSystem:
 def __init__(self,definitions:dict[str,DialogueDefinition],progress,on_flag=None,text_rate:float=52)->None:self.definitions=definitions;self.progress=progress;self.on_flag=on_flag;self.text_rate=text_rate;self.active=False;self.definition=None;self.current_id="";self.visible_chars=0.0;self.choice_index=0;self.npc_id="";self.completed_dialogue=""
 @property
 def node(self):return self.definition.nodes[self.current_id] if self.active and self.definition else None
 @property
 def text_complete(self)->bool:return self.node is not None and self.visible_chars>=len(self.node.text)
 @property
 def visible_text(self)->str:return self.node.text[:int(self.visible_chars)] if self.node else ""
 @property
 def available_choices(self)->tuple[Choice,...]:return tuple(c for c in self.node.choices if all(condition_matches(x,self.progress) for x in c.conditions)) if self.node else ()
 def start(self,dialogue_id:str,npc_id:str)->bool:
  definition=self.definitions.get(dialogue_id)
  if definition is None or self.active:return False
  self.active=True;self.definition=definition;self.current_id=definition.start;self.visible_chars=0;self.choice_index=0;self.npc_id=npc_id;self.completed_dialogue="";return True
 def update(self,dt:float)->None:
  if self.active and self.node:self.visible_chars=min(len(self.node.text),self.visible_chars+max(0,dt)*self.text_rate)
 def handle(self,action:Action)->str:
  if not self.active:return "none"
  if action is Action.BACK:self.close();return "close"
  if action in {Action.MENU_UP,Action.MENU_DOWN} and self.text_complete and self.available_choices:
   self.choice_index=(self.choice_index+(-1 if action is Action.MENU_UP else 1))%len(self.available_choices);return "move"
  if action is not Action.CONFIRM:return "none"
  if not self.text_complete:self.visible_chars=len(self.node.text);return "reveal"
  if self.node.kind is NodeType.CHOICE:
   choices=self.available_choices
   if not choices:return "none"
   chosen=choices[self.choice_index%len(choices)];self._apply(chosen.effects);self._goto(chosen.target);return "choice"
  self._apply(self.node.effects)
  if self.node.kind is NodeType.END or not self.node.next_id:self.close(completed=True);return "close"
  self._goto(self.node.next_id);return "advance"
 def _goto(self,node_id):self.current_id=node_id;self.visible_chars=0;self.choice_index=0
 def _apply(self,effects):
  for effect in effects:
   if effect["type"]=="set_flag" and effect["value"] not in self.progress.dialogue_flags:
    self.progress.dialogue_flags.add(effect["value"])
    if self.on_flag:self.on_flag(effect["value"])
 def close(self,completed=False):
  if completed and self.definition:self.completed_dialogue=self.definition.dialogue_id
  self.active=False;self.definition=None;self.current_id="";self.visible_chars=0;self.choice_index=0;self.npc_id=""
