from __future__ import annotations
import json,os
from pathlib import Path
os.environ.setdefault("SDL_VIDEODRIVER","dummy");os.environ.setdefault("SDL_AUDIODRIVER","dummy")
import pygame
from core.achievement_manager import AchievementManager
from core.game import Game
from core.input_manager import Action,FakeControllerBackend,InputManager
from core.save_manager import SaveManager
from core.settings_manager import SETTINGS_SCHEMA_VERSION,SettingsManager
from systems.level_completion import ExitType
from systems.progression import CollectibleType
from systems.save_data import CURRENT_SAVE_VERSION
from ui.achievement_toast import AchievementToastQueue
from world.campaign import DEFAULT_WORLD_REGISTRY,WorldRegistry
CATALOG=Path("data/achievements/achievements.json")
def make_manager(tmp_path,enabled=True):return AchievementManager.create(CATALOG,tmp_path/"achievements.json",enabled=enabled)
def test_first_shard_game_e2e_toast_persistence_and_f7(tmp_path):
 manager=make_manager(tmp_path);game=Game(achievement_manager=manager,achievements_enabled=True,settings_manager=SettingsManager(tmp_path/"settings.json"))
 try:
  shard=next(x for x in game.collectibles.collectibles if x.kind is CollectibleType.EMBER_SHARD);game.player.reposition((shard.pickup_rect.centerx-game.player.rect.width/2,shard.pickup_rect.centery-game.player.rect.height/2));game.update(0)
  assert "spark_in_the_dark" in manager.profile.unlocked and len(game.achievement_toasts.items)==1
  stamp=manager.profile.unlocked["spark_in_the_dark"];game.reset_level();assert not game.achievement_toasts.items and manager.profile.unlocked["spark_in_the_dark"]==stamp
  shard=next(x for x in game.collectibles.collectibles if x.kind is CollectibleType.EMBER_SHARD);game.player.reposition(shard.pickup_rect.topleft);game.update(0);assert manager.profile.unlocked["spark_in_the_dark"]==stamp
 finally:game.shutdown()
 assert "spark_in_the_dark" in make_manager(tmp_path).profile.unlocked

def test_level_secret_npc_boss_world_and_challenge_events(tmp_path):
 m=make_manager(tmp_path)
 m.emit("secret_discovered",secret_id="v01_breakable_cache");assert "off_the_path" in m.profile.unlocked
 m.emit("secret_exit_discovered",exit_id="v04_secret_exit");assert "veil_piercer" in m.profile.unlocked
 for i in range(12):m.emit("secret_discovered",secret_id=f"secret_{i}")
 assert "verdant_cartographer" in m.profile.unlocked
 for npc in ("mira","orin","talen","vesper","mira"):m.emit("npc_conversation_completed",npc_id=npc)
 assert {"friendly_voice","four_voices"}<=m.profile.unlocked.keys() and m.profile.counters["npc_conversations_completed"]==4
 new=m.emit("boss_defeated",boss_id="ashen_warden");assert {x.id for x in new}=={"warden_fallen"}
 m.emit("world_completed",world_id="verdant_reaches");assert "verdant_restored" in m.profile.unlocked
 m.emit("level_completed",level_id="verdant_01",no_damage=True,normal=True,shard_sweep=True);assert {"first_light","untouched","shard_sweep"}<=m.profile.unlocked.keys()

def test_frontend_keyboard_and_controller_achievement_screen(tmp_path):
 registry=WorldRegistry.load(DEFAULT_WORLD_REGISTRY);saves=SaveManager(registry,tmp_path/"saves");backend=FakeControllerBackend();backend.connect();inputs=InputManager(backend);game=Game(registry=registry,start_frontend=True,save_manager=saves,input_manager=inputs,settings_manager=SettingsManager(tmp_path/"settings.json"))
 try:
  game.frontend.menu.focus=next(i for i,x in enumerate(game.frontend.menu.items) if x.item_id=="achievements");game.frontend.handle(__import__('ui.menu',fromlist=['MenuAction']).MenuAction.CONFIRM);assert game.app_mode=="achievements"
  before=game.achievement_screen.category;game.achievement_screen.handle(Action.MENU_RIGHT);assert game.achievement_screen.category!=before
  assert game.achievement_screen.handle(Action.BACK)=="back"
  game.app_mode="achievements";backend.set_state(buttons=(False,True,False,False,False,False,False,False));inputs.begin_frame(1/60);game._dispatch_input();assert game.app_mode=="frontend"
 finally:game.shutdown()

def test_slot_operations_never_reset_profile(tmp_path):
 registry=WorldRegistry.load(DEFAULT_WORLD_REGISTRY);saves=SaveManager(registry,tmp_path/"saves");m=make_manager(tmp_path);m.emit("ember_shard_collected");stamp=m.profile.unlocked["spark_in_the_dark"]
 saves.new_game(1);saves.new_game(2);saves.delete(1);saves.new_game(1)
 loaded=make_manager(tmp_path);assert loaded.profile.unlocked["spark_in_the_dark"]==stamp

def test_direct_level_disabled_and_schema_isolation(tmp_path):
 m=make_manager(tmp_path,enabled=False);game=Game(achievement_manager=m,achievements_enabled=False,settings_manager=SettingsManager(tmp_path/"settings.json"))
 try:game._emit_achievement("ember_shard_collected");assert not m.profile.unlocked and not (tmp_path/"achievements.json").exists()
 finally:game.shutdown()
 assert CURRENT_SAVE_VERSION==3 and SETTINGS_SCHEMA_VERSION==2

def test_toast_queue_is_bounded_serial_and_pause_safe(tmp_path):
 pygame.font.init();m=make_manager(tmp_path);q=AchievementToastQueue(pygame.font.Font(None,24),pygame.font.Font(None,18))
 for d in m.definitions:q.push(d)
 assert len(q.items)==12;remaining=q.items[0].remaining;q.update(0);assert q.items[0].remaining==remaining;q.update(4);assert len(q.items)==11
