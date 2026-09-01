"""Central developer hotkeys, read-only snapshots, commands, and debug exports."""
from __future__ import annotations
from collections import deque
import json,time
from pathlib import Path
from typing import Any
import pygame
from debug.commands import DebugCommand,DebugCommandError,DebugCommandRegistry,parse_float,parse_int,require_args
from debug.overlay import DebugOverlay,PAGES,COLORS
from debug.profiler import DebugProfiler
from debug.snapshot import DebugSnapshot,build_snapshot
from settings import PROJECT_ROOT
from systems.combat import DamageSource
from systems.powerup_system import PowerUpType
from world.level import EnemySpawn
from systems.enemy_config import EnemyType
from enemies import create_enemy
from world.tile import TileKind

class DebugManager:
 def __init__(self,enabled:bool,font:pygame.font.Font,small:pygame.font.Font|None=None,export_root:Path|None=None):
  self.enabled=bool(enabled);self.overlay_visible=False;self.page_index=0;self.collision_visible=False;self.triggers_visible=False;self.platforms_visible=False;self.entities_visible=False;self.camera_visible=False;self.palette_open=False;self.command_text="";self.command_output=deque(maxlen=7);self.command_history=deque(maxlen=50);self.history_index=0;self.profiler=DebugProfiler(120);self.events=deque(maxlen=50);self.snapshot:DebugSnapshot|None=None;self.overlay=DebugOverlay(font,small);self.god_mode=False;self.tainted=False;self.simulation_paused=False;self.step_requested=False;self.time_scale=1.0;self.free_camera=False;self.free_camera_position=pygame.Vector2();self.selected:dict[str,Any]|None=None;self.export_root=export_root or PROJECT_ROOT/"debug_output";self.registry=DebugCommandRegistry();self._register_commands()
 @property
 def page(self):return PAGES[self.page_index]
 def cycle_page(self,reverse=False):self.page_index=(self.page_index+(-1 if reverse else 1))%len(PAGES)
 def record_event(self,category:str,event:str,**payload):
  self.events.append({"time":round(time.monotonic(),3),"category":category,"event":event,"payload":{k:str(v) for k,v in payload.items()}})
 def handle_event(self,event:pygame.event.Event,game:object)->bool:
  if not self.enabled:return False
  if self.palette_open:
   if event.type==pygame.KEYDOWN:
    if event.key==pygame.K_ESCAPE:self.palette_open=False;self.command_text=""
    elif event.key==pygame.K_RETURN:self.execute(game,self.command_text);self.command_text=""
    elif event.key==pygame.K_BACKSPACE:self.command_text=self.command_text[:-1]
    elif event.key==pygame.K_UP:self._history(-1)
    elif event.key==pygame.K_DOWN:self._history(1)
    elif event.unicode and event.unicode.isprintable() and len(self.command_text)<120:self.command_text+=event.unicode
   return event.type in {pygame.KEYDOWN,pygame.KEYUP,getattr(pygame,'TEXTINPUT',-1)}
  if event.type==pygame.KEYDOWN:
   if event.key in (pygame.K_BACKQUOTE,pygame.K_QUOTE):self.palette_open=True;getattr(game,"input").clear_all();return True
   if event.key==pygame.K_F1:self.overlay_visible=not self.overlay_visible;return True
   if event.key==pygame.K_F2:self.cycle_page(bool(event.mod&pygame.KMOD_SHIFT));self.overlay_visible=True;return True
   if event.key==pygame.K_F3:self.collision_visible=not self.collision_visible;return True
   if event.key==pygame.K_F4:self.triggers_visible=not self.triggers_visible;return True
   if event.key==pygame.K_F6 and hasattr(game,"effects"):
    quality=game.effects.toggle_optional();self.command_output.append(f"Optional effects: {quality.value}");return True
   if event.key==pygame.K_F7 and getattr(game,"app_mode","")=="gameplay":game.reset_level();self.record_event("DEBUG","level_reset");return True
   if event.key==pygame.K_F8:self.simulation_paused=not self.simulation_paused;return True
   if event.key==pygame.K_F9 and self.simulation_paused:self.step_requested=True;return True
   if event.key==pygame.K_F10:self.toggle_free_camera(game);return True
   if self.free_camera and event.key in {pygame.K_w,pygame.K_a,pygame.K_s,pygame.K_d,pygame.K_UP,pygame.K_DOWN,pygame.K_LEFT,pygame.K_RIGHT}:return True
  if self.free_camera and event.type==pygame.KEYUP and event.key in {pygame.K_w,pygame.K_a,pygame.K_s,pygame.K_d,pygame.K_UP,pygame.K_DOWN,pygame.K_LEFT,pygame.K_RIGHT}:return True
  if event.type==pygame.MOUSEBUTTONDOWN and event.button==1 and (self.overlay_visible or self.collision_visible or self.triggers_visible):self.select_at(game,event.pos);return False
  return False
 def _history(self,direction):
  if not self.command_history:return
  self.history_index=max(0,min(len(self.command_history)-1,self.history_index+direction));self.command_text=list(self.command_history)[self.history_index]
 def execute(self,game,text):
  text=text.strip()
  if not text:return
  self.command_history.append(text);self.history_index=len(self.command_history)
  try:result,mutates=self.registry.dispatch(game,text)
  except DebugCommandError as exc:result=f"ERROR: {exc}";mutates=False
  if mutates:self.tainted=True;self.record_event("DEBUG","command",command=text)
  self.command_output.append("> "+text);self.command_output.extend(str(result).splitlines()[:4])
 def simulation_dt(self,dt):
  if not self.enabled:return dt
  if self.simulation_paused:
   if self.step_requested:self.step_requested=False;return min(dt if dt>0 else 1/60,1/60)
   return 0.0
  return dt*self.time_scale
 def toggle_free_camera(self,game):
  if getattr(game,"app_mode","")!="gameplay":return
  self.free_camera=not self.free_camera
  if self.free_camera:self.free_camera_position.update(getattr(game,"camera").position);getattr(game,"input").clear_all()
 def update_free_camera(self,game,dt):
  if not self.enabled or not self.free_camera:return
  keys=pygame.key.get_pressed();axis=pygame.Vector2(float(keys[pygame.K_d] or keys[pygame.K_RIGHT])-float(keys[pygame.K_a] or keys[pygame.K_LEFT]),float(keys[pygame.K_s] or keys[pygame.K_DOWN])-float(keys[pygame.K_w] or keys[pygame.K_UP]))
  if axis.length_squared():axis.normalize_ip();self.free_camera_position+=axis*700*max(dt,1/60)
  level=getattr(game,"level",None);camera=getattr(game,"camera",None)
  if level and camera:
   self.free_camera_position.x=max(0,min(self.free_camera_position.x,level.tilemap.pixel_width-camera.viewport_width));self.free_camera_position.y=max(0,min(self.free_camera_position.y,level.tilemap.pixel_height-camera.viewport_height))
 def render_offset(self,game):return (-round(self.free_camera_position.x),-round(self.free_camera_position.y)) if self.enabled and self.free_camera else getattr(game,"camera").render_offset
 def view_rect(self,game):
  if self.enabled and self.free_camera:return pygame.Rect(round(self.free_camera_position.x),round(self.free_camera_position.y),*getattr(game,"canvas").get_size())
  return getattr(game,"camera").view_rect
 def capture(self,game,performance):self.snapshot=build_snapshot(game,self.profiler.frame,performance);return self.snapshot
 def draw(self,surface,game):
  if not self.enabled:return
  if self.collision_visible or self.triggers_visible or self.platforms_visible or self.entities_visible or self.camera_visible:self.draw_world(surface,game)
  if self.overlay_visible and self.snapshot:self.overlay.draw(surface,self.snapshot,self.page,self);self.overlay.draw_inspector(surface,self.selected)
  if self.palette_open:self.overlay.draw_palette(surface,self)
 def draw_world(self,surface,game):
  if getattr(game,"app_mode","") not in {"gameplay","dialogue","pause","game_over"} or not hasattr(game,"level"):return
  offset=self.render_offset(game);view=self.view_rect(game)
  def rect(r,c,w=2):pygame.draw.rect(surface,c,r.move(offset),w)
  if self.collision_visible:
   for tile in game.level.tilemap.tiles_in_rect(view.inflate(128,128)):
    color=(248,71,78) if tile.definition.kind is TileKind.HAZARD else COLORS["terrain"];rect(tile.rect,color,2)
   rect(game.player.rect,COLORS["player"],3)
   for enemy in game.enemies.enemies:rect(enemy.rect,COLORS["enemy"],2)
   for shot in game.projectiles.projectiles:rect(shot.rect,COLORS["projectile"],2)
   for door in game.world_objects.doors:rect(door.rect,(238,135,70),2)
  if self.triggers_visible:
   for cp in game.world_objects.checkpoints:rect(cp.rect.inflate(24,12),COLORS["trigger"],2)
   for switch in game.world_objects.switches:rect(switch.rect.inflate(32,18),COLORS["trigger"],2)
   for area in game.secrets.areas.values():rect(area.rect,COLORS["trigger"],2);self._label(surface,area.definition.secret_id,area.rect.move(offset).topleft)
   for npc in game.npcs.npcs:rect(npc.rect.inflate(npc.interaction_radius*2,npc.interaction_radius),COLORS["trigger"],1);self._label(surface,npc.npc_id,npc.rect.move(offset).topleft)
   if game.boss_system:rect(game.boss_system.definition.trigger,(255,104,64),3);rect(game.boss_system.definition.bounds,(255,174,62),3)
   else:rect(game.goal.rect.inflate(40,20),COLORS["trigger"],2)
  if self.platforms_visible or self.triggers_visible:
   for platform in game.world_objects.platforms:
    rect(platform.rect,COLORS["platform"],2);origin=pygame.Vector2(platform.origin)+pygame.Vector2(offset);end=origin+pygame.Vector2(platform.distance if platform.movement=="horizontal" else 0,platform.distance if platform.movement=="vertical" else 0);pygame.draw.line(surface,COLORS["platform"],origin,end,2);self._label(surface,f"{platform.object_id} {getattr(getattr(platform,'state',None),'value','move')}",platform.rect.move(offset).topleft)
  if self.entities_visible:
   for enemy in game.enemies.enemies:self._label(surface,f"{enemy.enemy_id} {enemy.health}/{enemy.max_health}",enemy.rect.move(offset).topleft)
   for shot in game.projectiles.projectiles:self._label(surface,f"{shot.faction.value} {shot.lifetime:.2f}s",shot.rect.move(offset).topleft)
  if self.camera_visible or self.triggers_visible:pygame.draw.rect(surface,COLORS["camera"],pygame.Rect(0,0,*surface.get_size()),2)
 def _label(self,surface,text,pos):surface.blit(self.overlay.small.render(str(text),True,(255,255,255)),pos)
 def select_at(self,game,screen_pos):
  if not hasattr(game,"camera"):return
  offset=self.render_offset(game);world=(screen_pos[0]-offset[0],screen_pos[1]-offset[1]);candidates=[]
  for rank,kind,items in ((0,"boss",[game.boss_system.boss] if game.boss_system else []),(1,"enemy",game.enemies.enemies),(2,"npc",game.npcs.npcs),(3,"projectile",game.projectiles.projectiles),(4,"platform",game.world_objects.platforms),(5,"door",game.world_objects.doors),(6,"switch",game.world_objects.switches),(7,"checkpoint",game.world_objects.checkpoints),(8,"player",[game.player])):
   for item in items:
    if item.rect.collidepoint(world):candidates.append((rank,item.rect.centerx,item.rect.centery,kind,item))
  if not candidates:self.selected=None;return
  _,_,_,kind,item=min(candidates);self.selected={"type":kind,"id":getattr(item,"enemy_id",getattr(item,"npc_id",getattr(item,"projectile_id",getattr(item,"object_id","nova")))),"bounds":tuple(item.rect),"health":getattr(item,"health",None),"state":getattr(getattr(item,"state",None),"value",getattr(item,"state",None)),"velocity":tuple(round(x,2) for x in getattr(item,"velocity",()))}
 def export_repro(self,game):
  if self.snapshot is None:self.capture(game,{})
  self.export_root.mkdir(parents=True,exist_ok=True);path=self.export_root/f"repro_{time.strftime('%Y%m%d_%H%M%S')}_{time.time_ns()%1_000_000:06d}.json";payload={"snapshot":self.snapshot.to_dict(),"events":list(self.events),"debug":{"page":self.page,"collision":self.collision_visible,"triggers":self.triggers_visible,"tainted":self.tainted,"time_scale":self.time_scale}};path.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8");return path
 def _register_commands(self):
  R=self.registry.register;game=frozenset({"gameplay"});global_=frozenset({"global"})
  R(DebugCommand("status","status","Show current debug session state.",global_,lambda g,a:f"debug=on tainted={self.tainted} paused={self.simulation_paused} scale={self.time_scale:g}"))
  R(DebugCommand("god","god [on|off]","Toggle damage immunity.",game,self._god,True));R(DebugCommand("heal","heal","Restore Nova's health.",game,self._heal,True));R(DebugCommand("damage","damage [amount]","Apply normal debug damage.",game,self._damage,True));R(DebugCommand("lives","lives <0..99>","Set lives safely.",game,self._lives,True));R(DebugCommand("powerup","powerup <type>","Activate an authoritative power-up.",game,self._powerup,True));R(DebugCommand("clear_powerup","clear_powerup","Clear active power-up.",game,self._clear_powerup,True));R(DebugCommand("teleport","teleport <x> <y>|checkpoint|goal|boss","Move Nova to a validated world position.",game,self._teleport,True));R(DebugCommand("checkpoint","checkpoint list|<id>","List or activate a checkpoint.",game,self._checkpoint,True));R(DebugCommand("spawn_enemy","spawn_enemy <type> [x y]","Spawn a configured enemy.",game,self._spawn_enemy,True));R(DebugCommand("clear_enemies","clear_enemies","Remove enemies without rewards.",game,self._clear_enemies,True));R(DebugCommand("boss","boss status|damage <n>|reset","Inspect or safely alter the boss.",game,self._boss,True));R(DebugCommand("secret","secret list|reveal <id>","Inspect or transiently reveal a secret.",game,self._secret,True));R(DebugCommand("save","save status","Show non-mutating save diagnostics.",global_,self._save));R(DebugCommand("achievement","achievement status","Show profile diagnostics.",global_,self._achievement));R(DebugCommand("dialogue","dialogue status|close","Inspect or close dialogue.",global_,self._dialogue));R(DebugCommand("audio","audio status|mute","Inspect or transiently mute audio.",global_,self._audio));R(DebugCommand("effects","effects status|full|reduced|off|stress","Inspect/override effects transiently.",global_,self._effects,True));R(DebugCommand("pause","pause","Toggle debug simulation pause.",global_,self._pause));R(DebugCommand("step","step","Advance one update while paused.",game,self._step));R(DebugCommand("timescale","timescale <0.25|0.5|1|2>","Set transient simulation time scale.",game,self._timescale));R(DebugCommand("repro","repro","Export a safe diagnostic JSON snapshot.",global_,lambda g,a:f"Exported {self.export_repro(g)}"));R(DebugCommand("perf","perf export","Export bounded rolling metrics.",global_,self._perf));R(DebugCommand("screenshot","screenshot","Save the current internal frame.",global_,self._screenshot))
 def _god(self,g,a):
  if len(a)>1:raise DebugCommandError("Usage: god [on|off]")
  self.god_mode=(not self.god_mode) if not a else {"on":True,"off":False}.get(a[0],self.god_mode)
  if a and a[0] not in {"on","off"}:raise DebugCommandError("Expected on or off")
  return f"God mode {'ON' if self.god_mode else 'OFF'}"
 def _heal(self,g,a):require_args(a,0,"heal");g.player.heal(g.player.max_health);return f"Health {g.player.health}/{g.player.max_health}"
 def _damage(self,g,a):
  if len(a)>1:raise DebugCommandError("Usage: damage [amount]")
  amount=parse_int(a[0],1,99) if a else 1
  if self.god_mode:return "God mode blocked damage"
  result=g.player.apply_damage(amount,DamageSource.ENEMY);return f"Damage applied={result.applied} absorbed={result.absorbed} health={g.player.health}"
 def _lives(self,g,a):require_args(a,1,"lives <0..99>");g.player.lives=parse_int(a[0],0,99);return f"Lives {g.player.lives}"
 def _powerup(self,g,a):require_args(a,1,"powerup <type>");kind=PowerUpType(a[0]);g.powerups.activate(kind);return f"Power-up {kind.value}"
 def _clear_powerup(self,g,a):require_args(a,0,"clear_powerup");g.powerups.clear("debug");return "Power-up cleared"
 def _teleport(self,g,a):
  if len(a)==1:
   if a[0]=="checkpoint":pos=tuple(g.world_objects.respawn_position)
   elif a[0]=="goal":pos=(g.goal.rect.x,g.goal.rect.y-g.player.rect.height)
   elif a[0]=="boss" and g.boss_system:pos=(g.boss_system.definition.trigger.centerx,g.boss_system.definition.trigger.bottom-g.player.rect.height)
   else:raise DebugCommandError("Usage: teleport <x> <y>|checkpoint|goal|boss")
  elif len(a)==2:pos=(parse_float(a[0],0,g.level.tilemap.pixel_width-g.player.rect.width),parse_float(a[1],0,g.level.tilemap.pixel_height-g.player.rect.height))
  else:raise DebugCommandError("Usage: teleport <x> <y>|checkpoint|goal|boss")
  g.player.reposition(pos);g.camera.snap_to(g.player.rect);return f"Teleported to ({round(pos[0])}, {round(pos[1])})"
 def _checkpoint(self,g,a):
  require_args(a,1,"checkpoint list|<id>")
  if a[0]=="list":return "Checkpoints: "+", ".join(x.object_id for x in g.world_objects.checkpoints)
  cp=next((x for x in g.world_objects.checkpoints if x.object_id==a[0]),None)
  if cp is None:raise DebugCommandError(f"Unknown checkpoint: {a[0]}")
  for x in g.world_objects.checkpoints:x.active=False
  cp.active=True;g.world_objects.activated_checkpoint_ids.add(cp.object_id);g.world_objects.respawn_position.update(cp.respawn_position);return f"Activated {cp.object_id}"
 def _spawn_enemy(self,g,a):
  if len(a) not in {1,3}:raise DebugCommandError("Usage: spawn_enemy <type> [x y]")
  kind=EnemyType(a[0]);pos=(g.player.rect.centerx+100,g.player.rect.y) if len(a)==1 else (parse_float(a[1],0,g.level.tilemap.pixel_width),parse_float(a[2],0,g.level.tilemap.pixel_height));eid=f"debug_{kind.value}_{len(g.enemies.enemies)+1}";enemy=create_enemy(EnemySpawn(eid,kind,pos,{}));g.enemies.enemies.append(enemy);return f"Spawned {eid}"
 def _clear_enemies(self,g,a):require_args(a,0,"clear_enemies");count=len(g.enemies.enemies);g.enemies.enemies.clear();return f"Cleared {count} enemies (no rewards)"
 def _boss(self,g,a):
  if not g.boss_system:raise DebugCommandError("No boss in this level")
  if a==("status",):b=g.boss_system.boss;return f"{b.display_name} {b.health}/{b.max_health} phase={b.phase} state={b.state.value}"
  if a==("reset",):g.boss_system.reset_encounter(g.powerups);return "Boss reset"
  if len(a)==2 and a[0]=="damage":
   amount=parse_int(a[1],1,99);g.boss_system.debug_damage(amount);return f"Boss health {g.boss_system.boss.health}/{g.boss_system.boss.max_health}"
  raise DebugCommandError("Usage: boss status|damage <n>|reset")
 def _secret(self,g,a):
  if a==("list",):return "Secrets: "+", ".join(f"{k}:{v.state.value}" for k,v in g.secrets.areas.items())
  if len(a)==2 and a[0]=="reveal":
   area=g.secrets.areas.get(a[1]);
   if area is None:raise DebugCommandError(f"Unknown secret: {a[1]}")
   from world.secret_area import SecretState
   if area.state is SecretState.UNDISCOVERED:area.state=SecretState.DISCOVERED
   return f"Revealed {a[1]} (transient)"
  raise DebugCommandError("Usage: secret list|reveal <id>")
 def _save(self,g,a):
  require_args(a,1,"save status")
  if a[0]!="status":raise DebugCommandError("Usage: save status")
  session=g.save_session
  return "No active slot; debug is nonpersistent" if session is None else f"slot={session.slot_id} schema=3 dirty={session.dirty} completed={g.world_progress.levels_completed} writes=disabled"
 def _achievement(self,g,a):
  require_args(a,1,"achievement status");return f"enabled={g.achievements.enabled} schema=1 unlocked={g.achievements.unlocked_count}/{len(g.achievements.definitions)} dirty={g.achievements.profile.dirty}"
 def _dialogue(self,g,a):
  require_args(a,1,"dialogue status|close")
  if a[0]=="status":return f"active={getattr(g.dialogue,'active',False)} id={getattr(g.dialogue,'dialogue_id',None)}"
  if a[0]=="close":g._close_dialogue();return "Dialogue closed"
  raise DebugCommandError("Usage: dialogue status|close")
 def _audio(self,g,a):
  require_args(a,1,"audio status|mute")
  if a[0]=="status":return f"available={g.audio.available} muted={g.audio.settings.muted} channels={g.audio.active_channels}"
  if a[0]=="mute":return f"Muted={g.audio.toggle_mute()}"
  raise DebugCommandError("Usage: audio status|mute")
 def _effects(self,g,a):
  require_args(a,1,"effects status|full|reduced|off|stress")
  if a[0]=="status":return f"quality={g.effects.quality.value} particles={g.effects.particle_count}/{g.effects.capacity}"
  if a[0]=="stress":
   for _ in range(20):g.effects.spawn("enemy_defeat",g.player.rect.center)
   return f"Stress effect bounded at {g.effects.particle_count}/{g.effects.capacity}"
  from systems.effects_system import EffectQuality
  g.effects.set_quality(EffectQuality(a[0]));return f"Effects {a[0]} (transient)"
 def _pause(self,g,a):require_args(a,0,"pause");self.simulation_paused=not self.simulation_paused;return f"Debug paused={self.simulation_paused}"
 def _step(self,g,a):require_args(a,0,"step");self.simulation_paused=True;self.step_requested=True;return "Stepping one simulation update"
 def _timescale(self,g,a):require_args(a,1,"timescale <0.25|0.5|1|2>");value=parse_float(a[0],.25,2);self.time_scale=min((.25,.5,1.,2.),key=lambda x:abs(x-value));return f"Time scale {self.time_scale:g}x"
 def _perf(self,g,a):require_args(a,1,"perf export");return f"Exported {self.profiler.export(self.export_root)}"
 def _screenshot(self,g,a):require_args(a,0,"screenshot");root=self.export_root/"screenshots";root.mkdir(parents=True,exist_ok=True);path=root/f"screen_{time.strftime('%Y%m%d_%H%M%S')}_{time.time_ns()%1_000_000:06d}.png";pygame.image.save(g.canvas,path);return f"Saved {path}"
