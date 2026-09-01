"""Developer-only Pygame level editor using the authoritative level format."""
from __future__ import annotations
import json,tempfile,time
from dataclasses import replace
from pathlib import Path
import pygame
from editor.commands import CommandHistory
from editor.document import LevelDocument,EditorDocumentError
from editor.palette import OBJECT_TYPES,SECRET_TYPES,object_template,secret_template,npc_template
from editor.viewport import EditorViewport
from settings import DISPLAY,PROJECT_ROOT
from world.tile import TILE_DEFINITIONS,draw_tile
class LevelEditor:
 def __init__(self,level_id="verdant_01",debug=False):
  pygame.init();pygame.display.set_caption("Echoes of Ember — Level Editor");self.screen=pygame.display.set_mode(DISPLAY.window_size,pygame.RESIZABLE);self.clock=pygame.time.Clock();path=PROJECT_ROOT/"data"/"levels"/f"{level_id}.json";self.document=LevelDocument.load(path) if path.exists() else LevelDocument.new(level_id);self.history=CommandHistory();self.view=EditorViewport();self.running=True;self.grid=True;self.tile_id=1;self.tool="paint";self.object_index=0;self.message="READY";self.dragging=False;self.pan_anchor=None;self.font=pygame.font.Font(None,20);self.heading=pygame.font.Font(None,28);self.layers={x:True for x in ("terrain","objects","secrets","npcs","triggers")};self.pending_quit=False;self.clipboard=None;self.rect_start=None;self.debug_playtest=bool(debug)
 def run(self,frames=None):
  count=0
  while self.running and (frames is None or count<frames):
   dt=self.clock.tick(60)/1000;self.handle_events();self.draw();count+=1
  pygame.quit()
 def handle_events(self):
  for event in pygame.event.get():
   if event.type==pygame.QUIT:self.request_quit()
   elif event.type==pygame.MOUSEWHEEL:self.view.step_zoom(1 if event.y>0 else -1,pygame.mouse.get_pos())
   elif event.type==pygame.MOUSEBUTTONDOWN:
    if event.button==2:self.pan_anchor=event.pos
    elif event.button in (1,3):self._mouse_action(event.pos,erase=event.button==3)
   elif event.type==pygame.MOUSEBUTTONUP and event.button==2:self.pan_anchor=None
   elif event.type==pygame.MOUSEMOTION and self.pan_anchor:
    dx=self.pan_anchor[0]-event.pos[0];dy=self.pan_anchor[1]-event.pos[1];self.view.pan(dx,dy);self.pan_anchor=event.pos
   elif event.type==pygame.KEYDOWN:self._key(event)
 def _key(self,e):
  mod=pygame.key.get_mods();ctrl=bool(mod&pygame.KMOD_CTRL);shift=bool(mod&pygame.KMOD_SHIFT)
  if self.pending_quit:
   if e.key==pygame.K_d:self.running=False
   elif e.key==pygame.K_s:
    try:self.document.save();self.running=False
    except Exception as exc:self.message=str(exc)
   elif e.key in (pygame.K_ESCAPE,pygame.K_c):self.pending_quit=False;self.clipboard=None;self.rect_start=None
   return
  if ctrl and e.key==pygame.K_s:
   try:self.document.save();self.message="SAVED + VALID"
   except Exception as exc:self.message=str(exc)
  elif ctrl and e.key==pygame.K_z:self.history.redo(self.document) if shift else self.history.undo(self.document)
  elif ctrl and e.key==pygame.K_y:self.history.redo(self.document)
  elif ctrl and e.key==pygame.K_c:self.clipboard=json.loads(json.dumps(self.document.selected())) if self.document.selected() else None
  elif ctrl and e.key==pygame.K_v and self.clipboard:
   def paste():
    item=json.loads(json.dumps(self.clipboard));item["id"]="";self.document.add_object(item,self.document.selection[0] if self.document.selection else "objects")
   self.history.execute(self.document,"paste",paste)
  elif ctrl and e.key==pygame.K_d:self.history.execute(self.document,"duplicate",self.document.duplicate_selected)
  elif e.key==pygame.K_DELETE:self.history.execute(self.document,"delete",self.document.remove_selected)
  elif e.key==pygame.K_g:self.grid=not self.grid
  elif e.key==pygame.K_r:self.tool="rectangle";self.rect_start=None
  elif pygame.K_1<=e.key<=pygame.K_5:
   key=("terrain","objects","secrets","npcs","triggers")[e.key-pygame.K_1];self.layers[key]=not self.layers[key]
  elif e.key in (pygame.K_LEFT,pygame.K_RIGHT,pygame.K_UP,pygame.K_DOWN) and self.document.selected():
   dx=(-8 if e.key==pygame.K_LEFT else 8 if e.key==pygame.K_RIGHT else 0);dy=(-8 if e.key==pygame.K_UP else 8 if e.key==pygame.K_DOWN else 0)
   def move():
    item=self.document.selected()
    if "x" in item:item["x"]+=dx;item["y"]+=dy
    elif "position" in item:item["position"][0]+=dx;item["position"][1]+=dy
    self.document.dirty=True
   self.history.execute(self.document,"move object",move)
  elif e.key==pygame.K_v:self.message="VALID" if not self.document.validate() else " | ".join(self.document.validation_errors[:3])
  elif e.key==pygame.K_TAB:self.tool={"paint":"object","object":"select","select":"paint"}[self.tool]
  elif e.key==pygame.K_LEFTBRACKET:self.tile_id=(self.tile_id-1)%8
  elif e.key==pygame.K_RIGHTBRACKET:self.tile_id=(self.tile_id+1)%8
  elif e.key==pygame.K_COMMA:self.object_index=(self.object_index-1)%len(OBJECT_TYPES)
  elif e.key==pygame.K_PERIOD:self.object_index=(self.object_index+1)%len(OBJECT_TYPES)
  elif e.key==pygame.K_F5:self.playtest(debug=self.debug_playtest or shift)
  elif e.key==pygame.K_ESCAPE:self.document.selection=None
 def request_quit(self):
  if self.document.dirty:self.pending_quit=True;self.message="UNSAVED: [S]AVE [D]ISCARD [C]ANCEL"
  else:self.running=False
 def _mouse_action(self,pos,erase=False):
  if not (190<=pos[0]<1010 and 20<=pos[1]<670):return
  world=self.view.screen_to_world(pos);tile=self.view.screen_to_tile(pos,self.document.data["tile_size"])
  if self.tool=="rectangle" and not erase:
   if self.rect_start is None:self.rect_start=tile;self.message="RECTANGLE: choose opposite corner"
   else:self.history.execute(self.document,"rectangle",lambda:self.document.rectangle(self.rect_start,tile,self.tile_id));self.rect_start=None;self.message="RECTANGLE PLACED"
   return
  if erase or self.tool=="paint":self.history.execute(self.document,"tile",lambda:self.document.set_tiles({tile:0 if erase else self.tile_id}));return
  if self.tool=="object":
   kind=OBJECT_TYPES[self.object_index];x,y=round(world[0]),round(world[1])
   if kind=="spawn":self.history.execute(self.document,"move spawn",lambda:self.document.data.__setitem__("player_spawn",[x,y]));self.document.dirty=True
   elif kind=="goal":
    def goal():self.document.data["goal"].update(x=x,y=y);self.document.dirty=True
    self.history.execute(self.document,"move goal",goal)
   elif kind=="npc":self.history.execute(self.document,"add NPC",lambda:self.document.add_object(npc_template(self.document.data["id"],x,y),"npcs"))
   elif kind in SECRET_TYPES:self.history.execute(self.document,"add secret",lambda:self.document.add_object(secret_template(kind,x,y),"secrets"))
   else:self.history.execute(self.document,"add object",lambda:self.document.add_object(object_template(kind,x,y)))
   return
  candidates=[x for x in self.document.data.get("objects",[]) if abs(x.get("x",-999)-world[0])<36 and abs(x.get("y",-999)-world[1])<36]
  if candidates:self.document.selection=("objects",candidates[0]["id"])
 def draw(self):
  self.screen.fill((12,17,29));viewport=pygame.Rect(190,20,820,650);pygame.draw.rect(self.screen,(22,31,43),viewport);self.screen.set_clip(viewport);ts=self.document.data["tile_size"]
  if self.layers["terrain"]:
   for y,row in enumerate(self.document.tile_grid()):
    for x,tile in enumerate(row):
     sx,sy=self.view.world_to_screen((x*ts,y*ts));rect=pygame.Rect(round(sx),round(sy),round(ts*self.view.zoom),round(ts*self.view.zoom))
     if viewport.colliderect(rect) and tile:draw_tile(self.screen,TILE_DEFINITIONS[tile],rect,rect.width)
     if self.grid and viewport.colliderect(rect):pygame.draw.rect(self.screen,(60,76,87),rect,1)
  if self.layers["objects"]:
   for item in self.document.data.get("objects",[]):
    sx,sy=self.view.world_to_screen((item.get("x",0),item.get("y",0)));r=pygame.Rect(round(sx-8),round(sy-8),16,16)
    if viewport.colliderect(r):pygame.draw.circle(self.screen,(245,166,72),r.center,7);self.screen.blit(self.font.render(item.get("type","?"),True,(230,230,210)),(r.x+10,r.y-4))
  if self.layers["secrets"]:
   for item in self.document.data.get("secrets",[]):
    x,y,w,h=item["properties"]["bounds"];a=self.view.world_to_screen((x,y));r=pygame.Rect(round(a[0]),round(a[1]),round(w*self.view.zoom),round(h*self.view.zoom));pygame.draw.rect(self.screen,(190,105,236),r,3)
  selected=self.document.selected()
  if selected and "x" in selected:
   p=self.view.world_to_screen((selected["x"],selected["y"]));pygame.draw.circle(self.screen,(255,255,255),(round(p[0]),round(p[1])),14,3)
  self.screen.set_clip(None);self._panels(selected);pygame.display.flip()
 def _panels(self,selected):
  pygame.draw.rect(self.screen,(19,25,42),(0,0,190,720));pygame.draw.rect(self.screen,(19,25,42),(1010,0,270,720));pygame.draw.rect(self.screen,(15,20,34),(190,670,820,50));self.screen.blit(self.heading.render("LEVEL EDITOR",True,(255,195,103)),(18,20))
  lines=[f"Tool: {self.tool}",f"Tile: {self.tile_id} {TILE_DEFINITIONS[self.tile_id].name}",f"Object: {OBJECT_TYPES[self.object_index]}","TAB tool  [ ] tile","< > object  RMB erase","MMB pan  wheel zoom","Ctrl+S save","Ctrl+Z/Y undo/redo","Ctrl+D duplicate  Del","V validate  F5 playtest","G grid  R rectangle","1-5 layer visibility"]
  for i,line in enumerate(lines):self.screen.blit(self.font.render(line,True,(205,214,229)),(15,65+i*27))
  self.screen.blit(self.heading.render("INSPECTOR",True,(255,195,103)),(1030,20));payload=json.dumps(selected,indent=1) if selected else "No selection"
  for i,line in enumerate(payload.splitlines()[:24]):self.screen.blit(self.font.render(line[:33],True,(201,211,224)),(1025,60+i*24))
  c=self.document.counts();status=f"{self.document.data['id']} | {self.view.zoom*100:.0f}% | {'DIRTY' if self.document.dirty else 'SAVED'} | "+" ".join(f"{k}:{v}" for k,v in c.items());self.screen.blit(self.font.render(status,True,(238,205,128)),(205,680));self.screen.blit(self.font.render(self.message[:100],True,(238,135,118)),(205,701))
 def playtest(self,debug=False):
  # Serialize to an isolated temporary level, then run the normal Game runtime briefly.
  dirty=self.document.dirty;source=self.document.source_path
  try:
   with tempfile.TemporaryDirectory() as folder:
    path=Path(folder)/f"{self.document.data['id']}.json";path.write_text(json.dumps(self.document.data,indent=2)+"\n")
    from tools.validation import load_and_validate_level;load_and_validate_level(path)
    from world.campaign import DEFAULT_WORLD_REGISTRY,WorldRegistry
    registry=WorldRegistry.load(DEFAULT_WORLD_REGISTRY);paths=dict(registry.level_paths);paths[self.document.data["id"]]=path;ids=registry.level_ids if self.document.data["id"] in registry.level_ids else registry.level_ids+(self.document.data["id"],);registry=replace(registry,level_ids=ids,level_paths=paths)
    from core.game import Game
    game=Game(level_id=self.document.data["id"],registry=registry,achievements_enabled=False,persistence=False,debug_enabled=debug);game.run(frame_limit=120)
    pygame.init();pygame.display.set_caption("Echoes of Ember — Level Editor");self.screen=pygame.display.set_mode(DISPLAY.window_size,pygame.RESIZABLE);self.font=pygame.font.Font(None,20);self.heading=pygame.font.Font(None,28);self.message="PLAYTEST RETURNED — campaign/profile isolated"
  except Exception as exc:self.message=f"PLAYTEST FAILED: {exc}"
  finally:self.document.dirty=dirty;self.document.source_path=source

def run_editor(level_id="verdant_01",frames=None,debug=False):LevelEditor(level_id,debug=debug).run(frames)
