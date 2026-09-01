from __future__ import annotations
import json, os
os.environ.setdefault("SDL_VIDEODRIVER","dummy");os.environ.setdefault("SDL_AUDIODRIVER","dummy")
import pygame
from core.game import Game
from core.input_manager import FakeControllerBackend, InputManager
from core.save_manager import SaveManager
from core.settings_manager import SettingsManager
from world.campaign import DEFAULT_WORLD_REGISTRY, WorldRegistry

DT=1/60

def interact_keyboard(game):
 game.input.begin_frame(DT);game.input.process_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e));game._dispatch_input();game.update(DT);game.input.process_event(pygame.event.Event(pygame.KEYUP,key=pygame.K_e))

def test_dialogue_interaction_freezes_gameplay_timer_and_simulation(tmp_path):
 game=Game(settings_manager=SettingsManager(tmp_path/"settings.json"))
 try:
  npc=game.npcs.npcs[0];game.player.reposition(npc.rect.topleft);interact_keyboard(game)
  assert game.app_mode=="dialogue" and game.dialogue.active and npc.talking
  elapsed=game.elapsed_time;player=game.player.position.copy();enemy_positions=[e.position.copy() for e in game.enemies.enemies];platform_positions=[p.rect.topleft for p in game.world_objects.platforms]
  game.update(.5)
  assert game.elapsed_time==elapsed and game.player.position==player
  assert [e.position for e in game.enemies.enemies]==enemy_positions
  assert [p.rect.topleft for p in game.world_objects.platforms]==platform_positions
  game.open_pause();assert game.app_mode=="dialogue"
 finally:game.shutdown()

def test_f7_style_reset_closes_dialogue_but_preserves_campaign_flags(tmp_path):
 game=Game(settings_manager=SettingsManager(tmp_path/"settings.json"))
 try:
  game.world_progress.dialogue_flags.add("met_mira");npc=game.npcs.npcs[0];game.player.reposition(npc.rect.topleft);interact_keyboard(game);assert game.dialogue.active
  game.reset_level();game.app_mode="gameplay"
  assert not game.dialogue.active and game.world_progress.dialogue_flags=={"met_mira"}
  assert game.npcs.choose_dialogue(game.npcs.npcs[0])=="mira_repeat"
 finally:game.shutdown()

def test_controller_opens_advances_and_closes_dialogue(tmp_path):
 backend=FakeControllerBackend();backend.connect();manager=InputManager(backend);game=Game(input_manager=manager,settings_manager=SettingsManager(tmp_path/"settings.json"))
 try:
  npc=game.npcs.npcs[0];game.player.reposition(npc.rect.topleft)
  backend.set_state(buttons=(False,False,False,True,False,False,False,False));manager.begin_frame(DT);game._dispatch_input();game.update(DT)
  assert game.app_mode=="dialogue"
  backend.set_state(buttons=(False,)*8);manager.begin_frame(DT)
  backend.set_state(buttons=(False,True,False,False,False,False,False,False));manager.begin_frame(DT);game._dispatch_input()
  assert game.app_mode=="gameplay" and not game.dialogue.active
 finally:game.shutdown()

def test_dialogue_flag_callback_autosaves_immediately(tmp_path):
 registry=WorldRegistry.load(DEFAULT_WORLD_REGISTRY);saves=SaveManager(registry,tmp_path/"saves");game=Game(registry=registry,save_manager=saves,persistence=True,new_game=True,settings_manager=SettingsManager(tmp_path/"settings.json"))
 try:
  game.world_progress.dialogue_flags.add("met_mira");game._commit_dialogue_flag("met_mira")
  raw=json.loads((tmp_path/"saves"/"slot_1.json").read_text())
  assert raw["schema_version"]==3 and raw["campaign"]["progression"]["dialogue_flags"]==["met_mira"]
 finally:game.shutdown()
