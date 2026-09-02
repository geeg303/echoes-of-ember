"""Lossless editable level document with safe authoritative serialization."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
import json,os,re,shutil
from pathlib import Path
from tools.validation import validate_level_data,load_and_validate_level
ID=re.compile(r"^[a-z][a-z0-9_]{1,63}$")
class EditorDocumentError(ValueError):
 """An editor operation would create or save unsafe level data."""
@dataclass(slots=True)
class DocumentSnapshot:data:dict;npcs:list
class LevelDocument:
 def __init__(self,data:dict,source_path:Path|None=None,npcs:list|None=None):self.data=deepcopy(data);self.source_path=source_path;self.npcs=deepcopy(npcs or []);self.dirty=False;self.selection=None;self.validation_errors=[];self._grid_cache=None;self._grid_builds=0
 @classmethod
 def load(cls,path:Path):
  data=load_and_validate_level(path);npc_path=path.parents[1]/"npcs"/f"{data['id']}.json";npcs=json.loads(npc_path.read_text()) if npc_path.exists() else [];return cls(data,path,npcs)
 @classmethod
 def new(cls,level_id="new_level",width=20,height=12,tile_size=64):
  if not ID.fullmatch(level_id):raise EditorDocumentError("invalid level ID")
  data={"id":level_id,"name":"New Level","world_id":"development","level_number":1,"display_name":"New Level","description":"Unregistered editor-authored level.","theme":"verdant","time_target":180,"shard_total":0,"rare_crystal_total":0,"secret_token_total":0,"completion_requirements":{"reach_goal":True,"minimum_ember_shards":0},"rating_thresholds":{"silver_score":1000,"gold_score":2500,"gold_shard_ratio":0.8,"gold_time":150},"goal":{"type":"ember_gate","x":(width-3)*tile_size,"y":(height-4)*tile_size,"properties":{"requires_interact":True}},"width":width,"height":height,"tile_size":tile_size,"player_spawn":[tile_size*2,(height-4)*tile_size],"tiles":[{"id":1,"position":[0,height-2],"size":[width,2]}],"objects":[],"secrets":[]};return cls(data)
 def snapshot(self):return DocumentSnapshot(deepcopy(self.data),deepcopy(self.npcs))
 def restore(self,s):self.data=deepcopy(s.data);self.npcs=deepcopy(s.npcs);self.dirty=True;self._grid_cache=None
 @property
 def pixel_size(self):return self.data["width"]*self.data["tile_size"],self.data["height"]*self.data["tile_size"]
 def tile_grid(self):
  if self._grid_cache is not None:return self._grid_cache
  grid=[[0]*self.data["width"] for _ in range(self.data["height"])]
  for item in self.data["tiles"]:
   x,y=item["position"];w,h=item.get("size",[1,1])
   for row in range(y,min(y+h,len(grid))):
    for col in range(x,min(x+w,len(grid[row]))):grid[row][col]=item["id"]
  self._grid_cache=grid;self._grid_builds+=1;return grid
 def set_tiles(self,cells:dict[tuple[int,int],int]):
  grid=[row[:] for row in self.tile_grid()]
  for (x,y),value in cells.items():
   if 0<=x<self.data["width"] and 0<=y<self.data["height"]:grid[y][x]=value
  self.data["tiles"]=[{"id":value,"position":[x,y],"size":[1,1]} for y,row in enumerate(grid) for x,value in enumerate(row) if value];self._grid_cache=grid;self.dirty=True
 def rectangle(self,a,b,tile_id):
  x1,x2=sorted((a[0],b[0]));y1,y2=sorted((a[1],b[1]));self.set_tiles({(x,y):tile_id for y in range(y1,y2+1) for x in range(x1,x2+1)})
 def unique_id(self,prefix):
  used={x.get("id") for x in self.data.get("objects",[])+self.data.get("secrets",[])+self.npcs};i=1
  while f"{prefix}_{i:02}" in used:i+=1
  return f"{prefix}_{i:02}"
 def add_object(self,item,collection="objects"):
  target=self.npcs if collection=="npcs" else self.data.setdefault(collection,[]);copy=deepcopy(item)
  if not copy.get("id"):copy["id"]=self.unique_id(copy.get("type",copy.get("secret_type","object")))
  if copy["id"] in {x.get("id") for x in self.data.get("objects",[])+self.data.get("secrets",[])+self.npcs}:raise EditorDocumentError("duplicate object ID")
  target.append(copy);self.selection=(collection,copy["id"]);self._sync_totals();self.dirty=True;return copy
 def remove_selected(self):
  if not self.selection:return False
  collection,oid=self.selection;target=self.npcs if collection=="npcs" else self.data.get(collection,[]);before=len(target);target[:]=[x for x in target if x.get("id")!=oid];self.selection=None;self._sync_totals();self.dirty|=len(target)!=before;return len(target)!=before
 def selected(self):
  if not self.selection:return None
  collection,oid=self.selection;target=self.npcs if collection=="npcs" else self.data.get(collection,[]);return next((x for x in target if x.get("id")==oid),None)
 def duplicate_selected(self,offset=16):
  item=self.selected()
  if not item:return None
  copy=deepcopy(item);copy["id"]=self.unique_id(copy.get("type",copy.get("secret_type","object")))
  if "x" in copy:copy["x"]+=offset;copy["y"]+=offset
  elif "position" in copy:copy["position"]=[copy["position"][0]+offset,copy["position"][1]+offset]
  return self.add_object(copy,self.selection[0])
 def resize(self,width,height):
  if not 8<=width<=512 or not 8<=height<=128:raise EditorDocumentError("dimensions outside safe range")
  pw,ph=width*self.data["tile_size"],height*self.data["tile_size"]
  outside=[x.get("id","object") for x in self.data.get("objects",[]) if x.get("x",0)>=pw or x.get("y",0)>=ph]
  if outside:raise EditorDocumentError(f"objects outside resized bounds: {outside}")
  grid=self.tile_grid();self.data["width"]=width;self.data["height"]=height;cells={(x,y):grid[y][x] for y in range(min(height,len(grid))) for x in range(min(width,len(grid[y]))) if grid[y][x]};self.data["tiles"]=[];self.set_tiles(cells)
 def validate(self):self._sync_totals();self.validation_errors=validate_level_data(self.data);return self.validation_errors
 def _sync_totals(self):
  types=[x.get("type") for x in self.data.get("objects",[])];self.data["shard_total"]=types.count("ember_shard");self.data["rare_crystal_total"]=types.count("rare_crystal");self.data["secret_token_total"]=types.count("secret_token")
 def save(self,path:Path|None=None,level_id=None):
  target=path or self.source_path
  if target is None:raise EditorDocumentError("Save As path required")
  if target.suffix!=".json" or not ID.fullmatch(level_id or self.data["id"]) or target.name!=(level_id or self.data["id"])+".json":raise EditorDocumentError("safe level filename must match level ID")
  if level_id:self.data["id"]=level_id
  errors=self.validate()
  if errors:raise EditorDocumentError("invalid level: "+"; ".join(errors))
  target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_suffix(".json.tmp");backup=target.with_suffix(".json.bak")
  if target.exists():shutil.copy2(target,backup)
  payload=json.dumps(self.data,indent=2,sort_keys=False)+"\n"
  try:
   with temp.open("w") as f:f.write(payload);f.flush();os.fsync(f.fileno())
   os.replace(temp,target);load_and_validate_level(target)
  except Exception:
   if backup.exists():shutil.copy2(backup,target)
   raise
  if self.npcs:
   for npc in self.npcs:npc["level_id"]=self.data["id"]
   npc_dir=target.parents[1]/"npcs";npc_dir.mkdir(parents=True,exist_ok=True);npc_target=npc_dir/f"{self.data['id']}.json";npc_temp=npc_target.with_suffix(".json.tmp")
   with npc_temp.open("w") as f:f.write(json.dumps(self.npcs,indent=2)+"\n");f.flush();os.fsync(f.fileno())
   os.replace(npc_temp,npc_target)
  self.source_path=target;self.dirty=False;return target
 def counts(self):
  types=[x.get("type") for x in self.data.get("objects",[])];return {"shards":types.count("ember_shard"),"rare":types.count("rare_crystal"),"tokens":types.count("secret_token"),"enemies":types.count("enemy"),"platforms":sum(x in {"moving_platform","falling_platform","disappearing_platform"} for x in types),"checkpoints":types.count("checkpoint"),"secrets":len(self.data.get("secrets",[])),"npcs":len(self.npcs)}
