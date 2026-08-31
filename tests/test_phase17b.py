import json, os
from pathlib import Path
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame
from core.audio_manager import AudioBus, AudioManager
from core.game import Game
from core.settings_manager import ApplicationSettings, SettingsManager
from states.pause_menu import GameOverController, PauseController
from ui.menu import MenuAction

class Host:
    def __init__(self): self.calls=[]; self.fullscreen=False
    def resume_game(self): self.calls.append("resume")
    def open_settings(self,parent): self.calls.append(("settings",parent))
    def restart_from_menu(self): self.calls.append("restart")
    def abandon_to_map(self): self.calls.append("map")
    def return_to_main_menu(self): self.calls.append("main")
    def retry_after_game_over(self): self.calls.append("retry")
    def set_fullscreen(self,value): self.fullscreen=value; self.calls.append(("fullscreen",value))
    def close_settings(self): self.calls.append("close")

class SilentAudio:
    def __init__(self): self.settings=__import__("core.audio_manager",fromlist=["AudioSettings"]).AudioSettings(); self.updates=0
    def play_sound(self,*a,**k): pass
    def set_muted(self,v): self.settings.muted=v
    def set_volume(self,b,v): self.settings.set_volume(b,v)
    def _apply_volumes(self): pass
    def update(self,dt): self.updates+=1

def focus(controller,item): controller.menu.focus=next(i for i,x in enumerate(controller.menu.items) if x.item_id==item)

def confirm_dialog(controller): controller.handle(MenuAction.RIGHT); controller.handle(MenuAction.CONFIRM)

def test_settings_missing_corrupt_future_and_atomic_roundtrip(tmp_path):
    path=tmp_path/"settings.json"; manager=SettingsManager(path)
    assert manager.load()==ApplicationSettings()
    settings=ApplicationSettings(); settings.audio.master_volume=.42; settings.audio.music_volume=.33; settings.effects_quality="reduced"; settings.fullscreen=True
    manager.save(settings); loaded=manager.load()
    assert loaded.audio.master_volume==.42 and loaded.audio.music_volume==.33 and loaded.effects_quality=="reduced" and loaded.fullscreen
    assert not path.with_suffix(".json.tmp").exists()
    path.write_text("{broken"); assert manager.load()==ApplicationSettings() and manager.last_warning
    path.write_text(json.dumps({"schema_version":999})); assert manager.load()==ApplicationSettings()

def test_settings_clamp_and_campaign_file_is_untouched(tmp_path):
    settings_path=tmp_path/"settings.json"; campaign=tmp_path/"slot_1.json"; campaign.write_text("campaign")
    settings_path.write_text(json.dumps({"schema_version":1,"audio":{"master_volume":9,"music_volume":-2},"visual":{"effects_quality":"full"},"display":{}}))
    loaded=SettingsManager(settings_path).load()
    assert loaded.audio.master_volume==1 and loaded.audio.music_volume==0 and loaded.effects_quality=="full"
    SettingsManager(settings_path).save(loaded); assert campaign.read_text()=="campaign"

def test_pause_confirmation_defaults_to_cancel_and_routes():
    pygame.font.init(); host=Host(); audio=SilentAudio(); font=pygame.font.Font(None,20); controller=PauseController(host,font,font,font,audio)
    focus(controller,"restart"); controller.handle(MenuAction.CONFIRM); controller.handle(MenuAction.CONFIRM); assert host.calls==[]
    focus(controller,"restart"); controller.handle(MenuAction.CONFIRM); confirm_dialog(controller); assert host.calls==["restart"]
    focus(controller,"settings"); controller.handle(MenuAction.CONFIRM); assert host.calls[-1]==("settings","pause")
    controller.handle(MenuAction.BACK); assert host.calls[-1]=="resume"

def test_game_over_routes():
    pygame.font.init(); host=Host(); audio=SilentAudio(); font=pygame.font.Font(None,20); controller=GameOverController(host,font,font,font,audio)
    focus(controller,"retry");controller.handle(MenuAction.CONFIRM)
    focus(controller,"map");controller.handle(MenuAction.CONFIRM)
    focus(controller,"main");controller.handle(MenuAction.CONFIRM)
    assert host.calls==["retry","map","main"]

def test_pause_freezes_gameplay_simulation_and_settings_returns(tmp_path):
    game=Game(settings_manager=SettingsManager(tmp_path/"settings.json"))
    try:
        before=(game.player.position.copy(),game.elapsed_time,len(game.projectiles.projectiles),game.effects.particle_count,game.effects.emitter_count)
        game.open_pause(); assert game.app_mode=="pause"
        game.update(.5)
        after=(game.player.position.copy(),game.elapsed_time,len(game.projectiles.projectiles),game.effects.particle_count,game.effects.emitter_count)
        assert before==after
        game.open_settings("pause"); game.settings_controller.close(); assert game.app_mode=="pause"
        game.resume_game(); assert game.app_mode=="gameplay"
    finally: game.shutdown()

def test_retry_after_game_over_is_full_runtime_reset(tmp_path):
    game=Game(settings_manager=SettingsManager(tmp_path/"settings.json"))
    try:
        game.player.health=1; game.player.lives=0; game.deaths=4; game.progress.score=999; game.app_mode="game_over"
        game.retry_after_game_over()
        assert game.app_mode=="gameplay" and game.player.health==game.player.max_health and game.player.lives==3
        assert game.deaths==0 and game.progress.score==0 and game.elapsed_time==0 and not game.world_objects.activated_checkpoint_ids and game.world_objects.respawn_position==game.level.player_spawn
    finally: game.shutdown()


def advance_death(game):
    game.player.health=1; game.player.lives=1; game.player.apply_damage(1,__import__("entities.player",fromlist=["DamageSource"]).DamageSource.HAZARD)
    assert game.player.is_dead
    for _ in range(90):
        game.update(1/60)
        if game.app_mode=="game_over": break

def test_final_life_enters_game_over_once_without_result_or_progress(tmp_path):
    game=Game(settings_manager=SettingsManager(tmp_path/"settings.json"))
    try:
        progress_before=(dict(game.world_progress.results),game.world_progress.progression_flags)
        advance_death(game)
        assert game.app_mode=="game_over" and game.player.lives==0 and game.deaths==1
        assert game.level_result is None and (dict(game.world_progress.results),game.world_progress.progression_flags)==progress_before
        game.update(1.0); assert game.player.lives==0 and game.deaths==1
    finally: game.shutdown()

def test_boss_game_over_retry_restores_phase_one_and_clears_failed_progress(tmp_path):
    game=Game(level_id="verdant_boss",settings_manager=SettingsManager(tmp_path/"settings.json"))
    try:
        assert game.boss_system is not None
        progress_before=(dict(game.world_progress.results),game.world_progress.progression_flags); boss=game.boss_system.boss; boss.health=max(1,boss.max_health//3)
        advance_death(game)
        assert game.app_mode=="game_over" and "verdant_boss" not in game.world_progress.completed_levels_once and (dict(game.world_progress.results),game.world_progress.progression_flags)==progress_before
        assert not game.projectiles.projectiles
        game.retry_after_game_over(); boss=game.boss_system.boss
        assert game.app_mode=="gameplay" and boss.health==boss.max_health and boss.phase==1 and game.player.lives==3
    finally: game.shutdown()
