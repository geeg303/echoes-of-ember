from __future__ import annotations
import json
from pathlib import Path
import pygame,pytest
from core.game import Game
from core.save_manager import SaveManager
from core.settings_manager import SettingsManager
from systems.powerup_system import PowerUpType
from world.campaign import DEFAULT_WORLD_REGISTRY,WorldRegistry

@pytest.fixture(autouse=True)
def dummy(monkeypatch):
 monkeypatch.setenv("SDL_VIDEODRIVER","dummy");monkeypatch.setenv("SDL_AUDIODRIVER","dummy")

def make_game(tmp_path,level="verdant_01"):
 registry=WorldRegistry.load(DEFAULT_WORLD_REGISTRY);return Game(level_id=level,registry=registry,debug_enabled=True,persistence=False,achievements_enabled=False,settings_manager=SettingsManager(tmp_path/"settings.json"))

def test_high_value_player_commands(tmp_path):
 g=make_game(tmp_path);d=g.debug
 try:
  g.player.health=1;d.execute(g,"heal");assert g.player.health==g.player.max_health
  d.execute(g,"lives 7");assert g.player.lives==7
  d.execute(g,"powerup wind_boots");assert g.powerups.has(PowerUpType.WIND_BOOTS)
  d.execute(g,"clear_powerup");assert g.powerups.active is None
  d.execute(g,"teleport checkpoint");assert g.player.rect.topleft==tuple(round(x) for x in g.world_objects.respawn_position)
  assert d.tainted
 finally:g.shutdown()

def test_enemy_secret_save_and_achievement_commands(tmp_path):
 g=make_game(tmp_path);d=g.debug
 try:
  original=len(g.enemies.enemies);d.execute(g,"spawn_enemy crawler");assert len(g.enemies.enemies)==original+1
  d.execute(g,"clear_enemies");assert not g.enemies.enemies
  d.execute(g,"secret list");d.execute(g,"save status");d.execute(g,"achievement status")
  assert any("enabled=False" in x for x in d.command_output)
 finally:g.shutdown()

def test_visualizations_are_read_only(tmp_path):
 g=make_game(tmp_path);d=g.debug;surface=pygame.Surface((1280,720));before=(g.player.rect.copy(),len(g.enemies.enemies),tuple(g.level.tilemap.grid[0]))
 try:
  d.collision_visible=d.triggers_visible=d.platforms_visible=d.entities_visible=d.camera_visible=True;d.draw_world(surface,g)
  assert g.player.rect==before[0] and len(g.enemies.enemies)==before[1] and tuple(g.level.tilemap.grid[0])==before[2]
 finally:g.shutdown()

def test_boss_debug_commands_reset_invariants(tmp_path):
 g=make_game(tmp_path,"verdant_boss");d=g.debug
 try:
  d.execute(g,"boss status");d.execute(g,"boss damage 2");assert g.boss_system.boss.health==g.boss_system.boss.max_health-2
  d.execute(g,"boss reset");assert g.boss_system.boss.health==g.boss_system.boss.max_health and not g.boss_system.active
 finally:g.shutdown()

def test_debug_session_never_writes_slot_or_achievements(tmp_path):
 registry=WorldRegistry.load(DEFAULT_WORLD_REGISTRY);manager=SaveManager(registry,tmp_path/"saves");session=manager.new_game(1);slot=tmp_path/"saves"/"slot_1.json";before=slot.read_bytes()
 g=Game(registry=registry,debug_enabled=True,persistence=False,achievements_enabled=False,save_manager=manager,settings_manager=SettingsManager(tmp_path/"settings.json"))
 try:g.debug.execute(g,"god on");g.debug.execute(g,"teleport goal");g._autosave(force=True)
 finally:g.shutdown()
 assert slot.read_bytes()==before and not (tmp_path/"achievements.json").exists()
