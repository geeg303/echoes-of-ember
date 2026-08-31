"""Phase 15 lifecycle, transition, save-isolation, and leak regressions."""
import os
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
from core.game import Game
from systems.effects_system import EffectQuality
from systems.save_data import CURRENT_SAVE_VERSION, SaveSession
from world.campaign import DEFAULT_WORLD_REGISTRY, WorldRegistry

DT=1/60

def test_level_runtime_configures_ambient_and_f7_reconstructs_effects():
    game=Game()
    try:
        assert any(key.startswith("ambient:") for key in game.effects.emitters)
        game.effects.spawn("enemy_defeat",game.player.rect.center)
        old=game.effects
        game.reset_level()
        assert game.effects is old and game.effects.particle_count==0
        assert any(key.startswith("ambient:") for key in game.effects.emitters)
    finally: game.shutdown()

def test_map_level_transitions_clear_owned_emitters_and_particles():
    game=Game(start_on_map=True)
    try:
        assert set(game.effects.emitters)=={"map:sanctum"}
        game.load_level("verdant_01")
        assert "map:sanctum" not in game.effects.emitters
        assert any(key.startswith("ambient:verdant_01") for key in game.effects.emitters)
        game.effects.spawn("enemy_hit",(10,10))
        game.return_to_world_map()
        assert game.effects.particle_count==0 and set(game.effects.emitters)=={"map:sanctum"}
    finally: game.shutdown()

def test_optional_effects_off_preserves_gameplay_and_critical_feedback():
    game=Game()
    try:
        health=game.player.health; position=game.player.position.copy()
        game.effects.set_quality(EffectQuality.OFF)
        assert game.effects.spawn("player_jump_dust",position)==0
        assert game.effects.spawn("player_damage",position)>0
        game.update(DT)
        assert game.player.health==health and game.player.position!=None
    finally: game.shutdown()

def test_continuous_emitters_remain_bounded_and_cleanup_after_long_run():
    game=Game()
    try:
        for _ in range(60*30): game.effects.update(DT,game.camera.view_rect)
        assert game.effects.particle_count<=game.effects.capacity
        assert game.effects.emitter_count<=3
        game.effects.clear()
        for _ in range(300): game.effects.update(DT,game.camera.view_rect)
        assert game.effects.particle_count==game.effects.emitter_count==0
    finally: game.shutdown()

def test_save_schema_remains_version_two_and_contains_no_effect_state():
    registry=WorldRegistry.load(DEFAULT_WORLD_REGISTRY); raw=SaveSession.fresh(1,registry).to_dict()
    assert CURRENT_SAVE_VERSION==2 and raw["schema_version"]==2
    text=str(raw).lower()
    assert "particle" not in text and "emitter" not in text and "effect_quality" not in text
