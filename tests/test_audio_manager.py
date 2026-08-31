import json, os
from pathlib import Path
os.environ.setdefault("SDL_AUDIODRIVER","dummy"); os.environ.setdefault("SDL_VIDEODRIVER","dummy")
import pygame, pytest
from core.audio_manager import AudioBus, AudioManager, AudioPriority, AudioSettings, load_audio_catalog
from settings import ASSET_ROOT

@pytest.fixture
def audio():
    pygame.mixer.quit(); manager=AudioManager(); yield manager; manager.shutdown()

def test_initializes_dummy_mixer_and_disabled_mode(audio):
    assert audio.available
    disabled=AudioManager(enabled=False); assert not disabled.available and disabled.disabled_reason

def test_mixer_failure_is_silent(monkeypatch):
    pygame.mixer.quit(); monkeypatch.setattr(pygame.mixer,"init",lambda **kwargs: (_ for _ in ()).throw(pygame.error("no device")))
    manager=AudioManager(); assert not manager.available and "no device" in manager.disabled_reason

def test_catalog_definitions_and_invalid_category(tmp_path):
    sounds,music=load_audio_catalog(Path("data/audio/audio.json")); assert "player_jump" in sounds and "music_boss" in music
    path=tmp_path/"bad.json"; path.write_text(json.dumps({"sounds":[{"id":"x","path":"x","category":"bad","priority":1}],"music":[]}))
    with pytest.raises(ValueError):load_audio_catalog(path)

def test_volume_clamp_effective_and_mute(audio):
    audio.set_volume(AudioBus.MASTER,2); audio.set_volume(AudioBus.SFX,-1); assert audio.settings.master_volume==1 and audio.settings.sfx_volume==0
    audio.set_volume(AudioBus.SFX,.5); assert audio.effective_volume(AudioBus.SFX,.5)==pytest.approx(.25)
    audio.set_muted(True); assert audio.effective_volume(AudioBus.SFX)==0
    audio.set_muted(False); assert audio.effective_volume(AudioBus.SFX)==pytest.approx(.5)

def test_mute_updates_already_playing_sfx(audio):
    assert audio.play_sound("player_death")
    channel=audio._active_sfx[-1].channel
    audio.set_muted(True); assert channel.get_volume()==0
    audio.set_muted(False); assert channel.get_volume()>0

def test_sound_play_cooldown_unknown_and_disabled(audio):
    assert audio.play_sound("player_jump"); assert not audio.play_sound("player_jump")
    audio.update(.07); assert audio.play_sound("player_jump")
    assert not audio.play_sound("unknown"); assert len(audio._failed)==1
    disabled=AudioManager(enabled=False); assert not disabled.play_sound("player_jump")

def test_instance_cap_and_critical_priority(audio):
    for _ in range(10):audio._clock+=1; audio.play_sound("world_complete")
    assert audio.sounds["world_complete"].priority is AudioPriority.CRITICAL
    assert audio.active_channels<=pygame.mixer.get_num_channels()

def test_missing_asset_cached_once(tmp_path):
    raw={"sounds":[{"id":"missing","path":"none.wav","category":"sfx","base_volume":1,"priority":1,"max_instances":1,"cooldown":0}],"music":[]}
    path=tmp_path/"catalog.json"; path.write_text(json.dumps(raw)); pygame.mixer.quit(); manager=AudioManager(catalog_path=path)
    assert not manager.play_sound("missing"); assert not manager.play_sound("missing"); assert manager._failed=={"missing"}; manager.shutdown()

def test_music_start_same_track_transition_stop(audio):
    assert audio.play_music("music_world_map",immediate=True); count=len(audio.events); assert audio.current_music=="music_world_map"
    assert audio.play_music("music_world_map"); assert len(audio.events)==count
    assert audio.play_music("music_verdant"); assert audio.pending_music=="music_verdant"
    audio.update(2); assert audio.current_music=="music_verdant" and audio.pending_music is None
    audio.stop_music(); assert audio.current_music is None

def test_ambience_owner_no_duplicate_and_reset(audio):
    assert audio.start_ambience("level","ambience_verdant"); first=audio._ambience["level"]
    assert audio.start_ambience("level","ambience_verdant"); assert audio._ambience["level"] is first
    audio.start_ambience("level","ambience_ruins"); assert audio._ambience["level"].sound_id=="ambience_ruins"
    audio.reset_context(); assert audio.ambience_owners==() and audio.active_channels==0

def test_positional_sound_and_history_bound(audio):
    assert audio.play_sound("ember_pulse_hit",position=(1000,0),listener_x=0,max_distance=1000)
    for _ in range(300):audio._record("sound","x",False)
    assert len(audio.events)==256

def test_settings_defaults():
    settings=AudioSettings(); assert settings.master_volume==1 and settings.music_volume==.75 and settings.sfx_volume==.85 and settings.ambience_volume==.60 and settings.ui_volume==.80
