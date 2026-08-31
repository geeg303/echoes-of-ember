import json,os
os.environ.setdefault("SDL_VIDEODRIVER","dummy");os.environ.setdefault("SDL_AUDIODRIVER","dummy")
import pygame
from core.game import Game
from core.input_manager import Action,FakeControllerBackend,InputDevice,InputManager
from core.save_manager import SaveManager
from core.settings_manager import SettingsManager
from states.frontend import FrontendScreen
from systems.level_completion import GameplayPhase
from systems.powerup_system import PowerUpType
from bosses.boss_base import BossState
from world.campaign import DEFAULT_WORLD_REGISTRY,WorldRegistry

def buttons(*pressed):
 out=[False]*8
 for i in pressed:out[i]=True
 return out

def frame(game,backend,*,buttons_down=(),axes=(0,0),hat=(0,0),dt=1/60,dispatch=True,update=False):
 backend.set_state(buttons=buttons(*buttons_down),axes=axes,hat=hat);game.input.begin_frame(dt)
 if dispatch:game._dispatch_input()
 if update:game.update(dt)

def release(game,backend):frame(game,backend)

def make_game(tmp_path,**kwargs):
 backend=FakeControllerBackend();backend.connect();manager=InputManager(backend);settings=SettingsManager(tmp_path/"settings.json")
 return Game(input_manager=manager,settings_manager=settings,**kwargs),backend

def test_controller_only_frontend_new_game_slot_and_settings(tmp_path):
 registry=WorldRegistry.load(DEFAULT_WORLD_REGISTRY);saves=SaveManager(registry,tmp_path/"saves");game,b=make_game(tmp_path,registry=registry,start_frontend=True,save_manager=saves)
 try:
  assert game.frontend.menu.focused.item_id=="new"
  frame(game,b,buttons_down=(0,));assert game.frontend.screen is FrontendScreen.SLOTS;release(game,b)
  frame(game,b,buttons_down=(0,));assert game.app_mode=="map" and game.save_session.slot_id==1;release(game,b)
  game.return_to_main_menu();release(game,b);game.frontend.menu.focus=next(i for i,x in enumerate(game.frontend.menu.items) if x.item_id=="settings")
  frame(game,b,buttons_down=(0,));assert game.app_mode=="settings";release(game,b)
  before=game.app_settings.audio.master_volume;frame(game,b,hat=(-1,0));assert game.app_settings.audio.master_volume<before;release(game,b)
  frame(game,b,buttons_down=(1,));assert game.app_mode=="frontend"
 finally:game.shutdown()

def test_controller_map_dpad_analog_confirm_and_back(tmp_path):
 game,b=make_game(tmp_path,start_on_map=True)
 try:
  start=game.world_map_runtime.current_node_id;frame(game,b,hat=(1,0));assert game.world_map_runtime.current_node_id!=start or game.world_map_runtime.travelling;release(game,b)
  for _ in range(120):game.update(1/60)
  frame(game,b,buttons_down=(0,));assert game.app_mode in {"map","gameplay"};release(game,b)
  if game.app_mode=="map":frame(game,b,buttons_down=(1,));assert game.app_mode=="frontend"
 finally:game.shutdown()

def test_gameplay_analog_jump_attack_interact_and_pause_edges(tmp_path):
 game,b=make_game(tmp_path)
 try:
  x=game.player.position.x;frame(game,b,axes=(1,0),update=True);assert game.player.velocity.x>0 and game.player.position.x>x;release(game,b)
  game.player.grounded=True;game.player.coyote_timer=.1;frame(game,b,buttons_down=(0,),update=True);assert game.player.velocity.y<0;release(game,b)
  game.powerups.activate(PowerUpType.EMBER_PULSE,20);frame(game,b,buttons_down=(2,),update=True);assert any(p.faction.value=="player" for p in game.projectiles.projectiles);release(game,b)
  switch=game.world_objects.switches[0];game.player.reposition(switch.rect.topleft);frame(game,b,buttons_down=(3,),update=True);assert switch.active;release(game,b)
  frame(game,b,buttons_down=(7,));assert game.app_mode=="pause";game.update(.5);assert game.app_mode=="pause"
  release(game,b);frame(game,b,buttons_down=(7,));assert game.app_mode=="gameplay"
 finally:game.shutdown()

def test_controller_level_complete_and_game_over_flows(tmp_path):
 game,b=make_game(tmp_path)
 try:
  game.gameplay_phase=GameplayPhase.LEVEL_COMPLETE;frame(game,b,buttons_down=(0,));assert game.app_mode=="map";release(game,b)
  game.load_level("verdant_01");game.app_mode="game_over";release(game,b);frame(game,b,buttons_down=(0,));assert game.app_mode=="gameplay" and game.player.lives==3
  game.app_mode="game_over";release(game,b);game.game_over_controller.menu.move(1);frame(game,b,buttons_down=(0,));assert game.app_mode=="map"
 finally:game.shutdown()

def test_device_prompts_switch_without_analog_noise(tmp_path):
 game,b=make_game(tmp_path,start_frontend=True)
 try:
  assert game.input.get_prompt(Action.CONFIRM)=="ENTER"
  frame(game,b,axes=(.1,.1),dispatch=False);assert game.input.active_device is InputDevice.KEYBOARD
  frame(game,b,buttons_down=(2,),dispatch=False);assert game.input.active_device is InputDevice.CONTROLLER and game.input.get_prompt(Action.ATTACK)=="X"
  game.input.process_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e));assert game.input.active_device is InputDevice.KEYBOARD
 finally:game.shutdown()

def test_v1_settings_migrate_vibration_and_preference_suppresses_rumble(tmp_path):
 path=tmp_path/"settings.json";path.write_text(json.dumps({"schema_version":1,"audio":{},"visual":{"effects_quality":"full"},"display":{"fullscreen":False}}))
 game,b=make_game(tmp_path)
 try:
  assert game.app_settings.vibration_enabled
  assert game._rumble(.2,.4,100) and b.rumbles
  game.app_settings.vibration_enabled=False;count=len(b.rumbles);assert not game._rumble(.2,.4,100) and len(b.rumbles)==count
  game.settings_manager.save(game.app_settings);assert json.loads(path.read_text())["schema_version"]==2
 finally:game.shutdown()

def test_disconnect_during_gameplay_stops_actor_and_keyboard_remains(tmp_path):
 game,b=make_game(tmp_path)
 try:
  frame(game,b,axes=(1,0),update=True);assert game.player.velocity.x>0
  b.disconnect();game.input.begin_frame(1/60);game._dispatch_input();assert game.input.axis(Action.MOVE_X)==0
  game.input.process_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_a));game.update(1/60);assert game.input.axis(Action.MOVE_X)==-1
  b.connect();frame(game,b,axes=(1,0),dispatch=False);assert game.input.active_device is InputDevice.CONTROLLER
 finally:game.shutdown()


def test_controller_only_boss_three_phases_defeat_and_world_complete(tmp_path):
 game,b=make_game(tmp_path,level_id="verdant_boss")
 try:
  trigger=game.level.boss_encounter.trigger;game.player.reposition((trigger.centerx-game.player.rect.width/2,trigger.bottom-game.player.rect.height));game.update(0)
  assert game.boss_system.active
  frame(game,b,buttons_down=(0,));release(game,b);assert game.boss_system.boss.state is not BossState.INTRO
  boss=game.boss_system.boss
  def controller_hit(health):
   boss.health=health;boss.invulnerability_timer=0;boss.set_state(BossState.RECOVER,2,True);game.player.facing=1
   game.player.reposition((boss.rect.centerx-game.player.rect.width-13,boss.rect.centery+5-game.player.rect.height/2))
   game.player_combat.cooldown_timer=0;frame(game,b,buttons_down=(2,),update=True);release(game,b)
  controller_hit(13);assert boss.phase==2
  controller_hit(7);assert boss.phase==3
  controller_hit(1);assert boss.defeat_claimed
  game.update(boss.config.defeat_duration+.1);assert game.gameplay_phase is GameplayPhase.COMPLETION_SEQUENCE and game.world_progress.world_completed_once
  game.update(2);assert game.gameplay_phase is GameplayPhase.LEVEL_COMPLETE
  frame(game,b,buttons_down=(0,));assert game.app_mode=="map"
 finally:game.shutdown()


def test_controller_rumble_damage_guard_and_boss_events(tmp_path):
 from types import SimpleNamespace
 game,b=make_game(tmp_path)
 try:
  game.player.reposition((12*64+10,16*64+8));game.update(1/60);assert b.rumbles
  b.rumbles.clear();game.powerups.activate(PowerUpType.STONE_GUARD);game.player.reposition((12*64+10,16*64+8));game.update(1/60);assert b.rumbles
 finally:game.shutdown()
 boss_game,b=make_game(tmp_path,level_id="verdant_boss")
 try:
  boss_game._emit_boss_audio(SimpleNamespace(triggered=False,audio_events=("ground_slam","phase","defeat")))
  assert len(b.rumbles)==3 and b.rumbles[-1][3]==320
 finally:boss_game.shutdown()
