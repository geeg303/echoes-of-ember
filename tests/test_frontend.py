import json,os
from pathlib import Path
os.environ.setdefault("SDL_AUDIODRIVER","dummy");os.environ.setdefault("SDL_VIDEODRIVER","dummy")
import pygame
from core.game import Game
from core.save_manager import SaveManager,SlotState
from states.frontend import FrontendScreen,format_play_time
from ui.menu import ConfirmationDialog,Menu,MenuAction,MenuItem,Slider,Selector,action_for_key
from world.campaign import DEFAULT_WORLD_REGISTRY,WorldRegistry

def make_game(tmp_path):
 registry=WorldRegistry.load(DEFAULT_WORLD_REGISTRY);manager=SaveManager(registry,tmp_path);return Game(registry=registry,start_frontend=True,save_manager=manager),manager

def choose(controller,item_id):
 controller.menu.focus=next(i for i,x in enumerate(controller.menu.items) if x.item_id==item_id);controller.handle(MenuAction.CONFIRM)

def test_menu_focus_skips_disabled_and_logical_keys():
 menu=Menu([MenuItem("A","a",False),MenuItem("B","b"),MenuItem("C","c")]);assert menu.focused.item_id=="b";menu.move(1);assert menu.focused.item_id=="c"
 assert action_for_key(pygame.K_w) is MenuAction.UP and action_for_key(pygame.K_RETURN) is MenuAction.CONFIRM
 assert Slider("x",.98).adjust(1)==1 and Selector("x",("a","b")).adjust(1)=="b"

def test_startup_frontend_continue_disabled_and_routes(tmp_path):
 game,manager=make_game(tmp_path)
 try:
  assert game.app_mode=="frontend" and game.frontend.screen is FrontendScreen.MAIN
  assert not next(x for x in game.frontend.menu.items if x.item_id=="continue").enabled
  choose(game.frontend,"settings");assert game.app_mode=="settings" and game.settings_parent=="frontend"
  game.settings_controller.handle(MenuAction.BACK);assert game.app_mode=="frontend"
  choose(game.frontend,"credits");assert game.frontend.screen is FrontendScreen.CREDITS
 finally:game.shutdown()

def test_three_empty_slots_and_formatting(tmp_path):
 game,_=make_game(tmp_path)
 try:
  game.frontend.open_slots("load");assert len(game.frontend.summaries)==3;assert all(x.state is SlotState.EMPTY for x in game.frontend.summaries);assert format_play_time(3723)=="01:02:03"
 finally:game.shutdown()

def test_empty_slot_new_game_enters_map(tmp_path):
 game,manager=make_game(tmp_path)
 try:
  game.frontend.open_slots("new");choose(game.frontend,"slot:2");assert game.app_mode=="map";assert game.save_session.slot_id==2;assert manager.inspect_slot(2).state is SlotState.VALID
 finally:game.shutdown()

def test_occupied_new_game_requires_confirmation_cancel_preserves(tmp_path):
 game,manager=make_game(tmp_path);session=manager.new_game(1);session.play_time_seconds=99;manager.save(session)
 try:
  game.frontend.open_slots("new");choose(game.frontend,"slot:1");assert game.frontend.dialog is not None
  game.frontend.handle(MenuAction.CONFIRM);assert game.app_mode=="frontend" and manager.load(1).session.play_time_seconds==99
 finally:game.shutdown()

def test_overwrite_confirm_resets_only_selected_slot(tmp_path):
 game,manager=make_game(tmp_path);a=manager.new_game(1);a.play_time_seconds=50;manager.save(a);b=manager.new_game(2);b.play_time_seconds=80;manager.save(b)
 try:
  game.frontend.refresh_slots();game.frontend.open_slots("new");choose(game.frontend,"slot:1");game.frontend.handle(MenuAction.LEFT);game.frontend.handle(MenuAction.CONFIRM)
  assert game.app_mode=="map" and game.save_session.slot_id==1 and game.save_session.play_time_seconds==0;assert manager.load(2).session.play_time_seconds==80
 finally:game.shutdown()

def test_valid_slot_play_and_delete_cancel_confirm(tmp_path):
 game,manager=make_game(tmp_path);manager.new_game(1)
 try:
  game.frontend.refresh_slots();game.frontend.open_slots("load");choose(game.frontend,"slot:1");assert game.frontend.screen is FrontendScreen.SLOT_ACTION
  choose(game.frontend,"delete");game.frontend.handle(MenuAction.CONFIRM);assert manager.inspect_slot(1).state is SlotState.VALID
  choose(game.frontend,"delete");game.frontend.handle(MenuAction.LEFT);game.frontend.handle(MenuAction.CONFIRM);assert manager.inspect_slot(1).state is SlotState.EMPTY
 finally:game.shutdown()

def test_continue_selects_most_recent_valid(tmp_path):
 game,manager=make_game(tmp_path);manager.new_game(1);manager.new_game(2)
 game.frontend.summaries=tuple([game.frontend.summaries[0].__class__(1,SlotState.VALID,updated_at="2026-01-01T00:00:00Z"),game.frontend.summaries[1].__class__(2,SlotState.VALID,updated_at="2026-02-01T00:00:00Z"),game.frontend.summaries[2]])
 try:assert game.frontend.continue_slot==2
 finally:game.shutdown()

def test_recovered_corrupt_and_unsupported_presentation(tmp_path):
 game,manager=make_game(tmp_path);session=manager.new_game(1);manager.save(session);manager._primary(1).write_text("broken")
 manager._primary(2).write_text("broken");manager._primary(3).write_text(json.dumps({"schema_version":999}))
 try:
  game.frontend.refresh_slots();states=[x.state for x in game.frontend.summaries];assert states==[SlotState.RECOVERED,SlotState.CORRUPT,SlotState.UNSUPPORTED_VERSION]
  game.frontend.open_slots("load");unsupported=next(x for x in game.frontend.menu.items if x.item_id=="slot:3");assert not unsupported.enabled and "UNSUPPORTED" in unsupported.detail
 finally:game.shutdown()

def test_return_main_refreshes_slot_metadata(tmp_path):
 game,manager=make_game(tmp_path)
 try:
  game.start_campaign(1,True);game.return_to_main_menu();assert game.app_mode=="frontend" and game.frontend.continue_slot==1
 finally:game.shutdown()
