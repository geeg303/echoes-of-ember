"""Validated data-driven achievement definitions and event-driven evaluation."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import json,re
from pathlib import Path
ID_RE=re.compile(r"^[a-z][a-z0-9_]{1,63}$")
COUNTERS={"ember_shards_collected","rare_crystals_collected","secret_tokens_collected","enemies_defeated","secrets_discovered","npc_conversations_completed","levels_completed","bosses_defeated"}
SETS={"npc_ids_met","secret_ids_found","completed_level_ids","boss_ids_defeated"}
CATEGORIES={"progression","exploration","combat","secrets","collectibles","story","challenge"}
class AchievementDataError(ValueError):
    """Achievement definitions are malformed or unsafe."""
class Visibility(str,Enum):VISIBLE="visible";HIDDEN="hidden"
@dataclass(frozen=True,slots=True)
class AchievementDefinition:
 id:str;title:str;description:str;category:str;visibility:Visibility;condition:dict;sort_order:int;style:str="ember"
def _condition(raw,where):
 if not isinstance(raw,dict):raise AchievementDataError(f"{where} condition must be an object")
 kind=raw.get("type")
 if kind=="event":
  if not isinstance(raw.get("event"),str) or not raw["event"]:raise AchievementDataError(f"{where} event malformed")
  match=raw.get("match",{})
  if not isinstance(match,dict) or any(not isinstance(k,str) or not isinstance(v,(str,bool,int)) for k,v in match.items()):raise AchievementDataError(f"{where} event match malformed")
 elif kind=="flag":
  if not isinstance(raw.get("flag"),str) or not ID_RE.fullmatch(raw["flag"]):raise AchievementDataError(f"{where} flag malformed")
 elif kind=="counter_at_least":
  if raw.get("counter") not in COUNTERS or not isinstance(raw.get("value"),int) or isinstance(raw.get("value"),bool) or raw["value"]<0:raise AchievementDataError(f"{where} counter condition malformed")
 elif kind=="set_contains_all":
  values=raw.get("values")
  if raw.get("set") not in SETS or not isinstance(values,list) or not values or not all(isinstance(x,str) and x for x in values):raise AchievementDataError(f"{where} set condition malformed")
 elif kind in {"all_of","any_of"}:
  children=raw.get("conditions")
  if not isinstance(children,list) or not children:raise AchievementDataError(f"{where} nested condition empty")
  for i,child in enumerate(children):_condition(child,f"{where}.{i}")
 else:raise AchievementDataError(f"{where} unknown condition type: {kind}")
 return raw
def load_achievement_definitions(path:Path)->tuple[AchievementDefinition,...]:
 try:raw=json.loads(path.read_text(encoding="utf-8"))
 except (OSError,json.JSONDecodeError) as exc:raise AchievementDataError(str(exc)) from exc
 if not isinstance(raw,list) or not raw:raise AchievementDataError("achievement catalog must be a non-empty list")
 out=[];ids=set();orders=set()
 for i,item in enumerate(raw):
  if not isinstance(item,dict):raise AchievementDataError(f"achievement {i} must be an object")
  aid=item.get("id");title=item.get("title");desc=item.get("description");cat=item.get("category");order=item.get("sort_order")
  if not isinstance(aid,str) or not ID_RE.fullmatch(aid) or aid in ids:raise AchievementDataError("achievement IDs must be unique and valid")
  if not isinstance(title,str) or not title.strip() or not isinstance(desc,str) or not desc.strip():raise AchievementDataError(f"achievement {aid} text missing")
  if cat not in CATEGORIES:raise AchievementDataError(f"achievement {aid} category invalid")
  try:visibility=Visibility(item.get("visibility"))
  except ValueError as exc:raise AchievementDataError(f"achievement {aid} visibility invalid") from exc
  if not isinstance(order,int) or isinstance(order,bool) or order in orders:raise AchievementDataError("sort_order must be unique integers")
  style=item.get("style","ember")
  if style not in {"ember","crystal","secret","story","combat","challenge"}:raise AchievementDataError(f"achievement {aid} style invalid")
  out.append(AchievementDefinition(aid,title.strip(),desc.strip(),cat,visibility,_condition(item.get("condition"),aid),order,style));ids.add(aid);orders.add(order)
 return tuple(sorted(out,key=lambda x:(x.sort_order,x.title)))
def condition_matches(condition,profile,event,payload):
 kind=condition["type"]
 if kind=="event":return event==condition["event"] and all(payload.get(k)==v for k,v in condition.get("match",{}).items())
 if kind=="flag":return condition["flag"] in profile.flags
 if kind=="counter_at_least":return profile.counters.get(condition["counter"],0)>=condition["value"]
 if kind=="set_contains_all":return set(condition["values"])<=profile.sets.get(condition["set"],set())
 children=condition["conditions"]
 return (all if kind=="all_of" else any)(condition_matches(x,profile,event,payload) for x in children)
