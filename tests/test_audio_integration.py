"""Authoritative gameplay outcomes emit presentation-only audio requests."""
import os
os.environ.setdefault("SDL_AUDIODRIVER","dummy"); os.environ.setdefault("SDL_VIDEODRIVER","dummy")
import pygame
from bosses.boss_base import BossState
from core.audio_manager import AudioManager
from core.game import Game
from entities.projectile import Faction,Projectile
from systems.powerup_system import PowerUpType
from systems.progression import CollectibleType
from systems.save_data import CURRENT_SAVE_VERSION,SaveSession
from world.campaign import DEFAULT_WORLD_REGISTRY,WorldRegistry
DT=1/60

def ids(game):return [event.audio_id for event in game.audio.events]
def trigger_boss(game):
    trigger=game.level.boss_encounter.trigger; game.player.reposition((trigger.centerx-game.player.rect.width/2,trigger.bottom-game.player.rect.height)); game.update(0)

def test_map_music_ambience_and_ui_requests():
    game=Game(start_on_map=True)
    try:
        assert game.audio.current_music=="music_world_map" and game.audio.ambience_owners==("map",)
        game.audio.events.clear(); game._handle_map_key(pygame.K_RIGHT); assert any(x in ids(game) for x in ("ui_move","ui_locked"))
        game.load_level("verdant_01"); assert game.audio.current_music in {"music_world_map","music_verdant"} and game.audio.ambience_owners==("level",)
        game.audio.update(2); assert game.audio.current_music=="music_verdant"
    finally:game.shutdown()

def test_player_jump_damage_and_death_requests():
    game=Game()
    try:
        for _ in range(120):
            game.update(DT)
            if game.player.grounded: break
        assert game.player.grounded
        game.audio.events.clear(); game._jump_pressed=True; game.update(DT); assert "player_jump" in ids(game)
        game.player.invulnerability_timer=0; game.player.health=2; game.player.apply_damage(1,__import__('systems.combat',fromlist=['DamageSource']).DamageSource.ENEMY); game.audio.play_sound("player_damage"); assert "player_damage" in ids(game)
        game.audio.play_sound("player_death"); assert "player_death" in ids(game)
    finally:game.shutdown()

def test_collectible_powerup_and_pulse_requests():
    game=Game()
    try:
        shard=next(x for x in game.collectibles.collectibles if x.kind is CollectibleType.EMBER_SHARD); game.player.reposition((shard.pickup_rect.x,shard.pickup_rect.y)); game.update(0); assert "ember_shard" in ids(game)
        pickup=next(x for x in game.powerup_pickups.pickups if x.kind is PowerUpType.EMBER_PULSE); game.player.reposition((pickup.pickup_rect.x,pickup.pickup_rect.y)); game.update(0); assert "powerup_ember" in ids(game)
        game._attack_pressed=True; game.update(DT); assert "ember_pulse_fire" in ids(game)
    finally:game.shutdown()

def test_world_secret_and_combat_catalog_requests_are_bounded():
    game=Game()
    try:
        for audio_id in ("checkpoint_activate","switch_activate","door_open","breakable_destroy","platform_warning","secret_discovered","challenge_complete","secret_exit","enemy_hit","enemy_defeat","armored_block"):
            game.audio.play_sound(audio_id)
        assert set(("checkpoint_activate","switch_activate","door_open","breakable_destroy","secret_discovered","enemy_defeat"))<=set(ids(game))
        assert game.audio.active_channels<=24
    finally:game.shutdown()

def test_boss_intro_phase_hurt_defeat_and_music_requests():
    game=Game(level_id="verdant_boss")
    try:
        game.audio.events.clear(); trigger_boss(game); assert "warden_awaken" in ids(game); game.audio.update(2); assert game.audio.current_music=="music_boss"
        boss=game.boss_system.boss; game._emit_boss_audio(type("R",(),{"triggered":False,"audio_events":("ground_slam","bolt","ember_rain","leap","charge","core_burst","phase","hurt","defeat")})())
        expected={"warden_ground_slam","warden_bolt","warden_ember_rain","warden_leap","warden_charge","warden_core_burst","warden_phase_transition","warden_hurt","warden_defeat"}; assert expected<=set(ids(game))
    finally:game.shutdown()

def test_f7_and_map_level_cycles_do_not_duplicate_ambience():
    game=Game()
    try:
        for _ in range(3):game.reset_level(); assert game.audio.ambience_owners==("level",)
        game.return_to_world_map(); assert game.audio.ambience_owners==("map",)
        game.load_level("verdant_02"); assert game.audio.ambience_owners==("level",)
        assert len(game.audio.ambience_owners)==1
    finally:game.shutdown()

def test_disabled_audio_preserves_gameplay_and_progression():
    audio=AudioManager(enabled=False); game=Game(audio_manager=audio)
    try:
        start=game.player.position.copy(); game.update(DT); game.audio.play_sound("player_jump"); game.audio.play_music("music_verdant")
        assert not game.audio.available and game.player.position is not None and game.progress.score==0
    finally:game.shutdown()

def test_campaign_save_schema_has_no_audio_runtime_state():
    raw=SaveSession.fresh(1,WorldRegistry.load(DEFAULT_WORLD_REGISTRY)).to_dict(); text=str(raw).lower()
    assert CURRENT_SAVE_VERSION==3 and raw["schema_version"]==3
    assert all(word not in text for word in ("audio","music","ambience","channel","mute"))


def test_actual_checkpoint_switch_and_secret_outcomes_emit_audio():
    game=Game()
    try:
        checkpoint=game.world_objects.checkpoints[0]; game.player.reposition((checkpoint.rect.x,checkpoint.rect.y)); game.update(0); assert "checkpoint_activate" in ids(game)
        switch=game.world_objects.switches[0]; game.player.reposition((switch.rect.x,switch.rect.y)); game._interact_pressed=True; game.update(0); assert "switch_activate" in ids(game) and "door_open" in ids(game)
        area=next(iter(game.secrets.areas.values())); game.player.reposition((area.rect.x,area.rect.y)); game.update(0); assert "secret_discovered" in ids(game)
    finally:game.shutdown()

def test_actual_boss_phase_and_defeat_outcomes_emit_audio_once():
    game=Game(level_id="verdant_boss")
    try:
        trigger_boss(game); boss=game.boss_system.boss; game.audio.events.clear()
        boss.health=13; boss.set_state(BossState.RECOVER,2,True); game.projectiles.spawn(Projectile("phase_hit",boss.rect.center,pygame.Vector2(),1,Faction.PLAYER,2,owner_id="player",terrain_collision=False)); game.update(0)
        assert "warden_phase_transition" in ids(game) and "warden_hurt" in ids(game)
        boss.invulnerability_timer=0; boss.health=1; boss.set_state(BossState.RECOVER,2,True); game.projectiles.spawn(Projectile("final_hit",boss.rect.center,pygame.Vector2(),1,Faction.PLAYER,2,owner_id="player",terrain_collision=False)); game.update(0)
        assert "warden_defeat" in ids(game)
    finally:game.shutdown()
