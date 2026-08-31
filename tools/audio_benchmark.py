"""Repeatable 600-frame Phase 16 audio request benchmarks."""
from __future__ import annotations
import os,statistics,sys,time
from pathlib import Path
os.environ.setdefault("SDL_AUDIODRIVER","dummy"); os.environ.setdefault("SDL_VIDEODRIVER","dummy")
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.audio_manager import AudioManager
DT=1/60; FRAMES=600

def run(scenario:str):
    audio=AudioManager(); audio.play_music("music_verdant",immediate=True); audio.start_ambience("level","ambience_verdant"); samples=[]
    try:
        for frame in range(FRAMES):
            start=time.perf_counter()
            if scenario=="normal" and frame%60==0:audio.play_sound("player_jump")
            elif scenario=="shards":
                for _ in range(8):audio.play_sound("ember_shard")
            elif scenario=="combat":
                for cue in ("ember_pulse_fire","ember_pulse_hit","enemy_hit","enemy_defeat"):audio.play_sound(cue)
            elif scenario=="phase3":
                for cue in ("warden_ground_slam","warden_bolt","warden_core_burst","warden_hurt"):audio.play_sound(cue)
            audio.update(DT); samples.append((time.perf_counter()-start)*1000)
        ordered=sorted(samples); print(f"{scenario} mean_ms={statistics.mean(samples):.4f} p95_ms={ordered[569]:.4f} max_ms={max(samples):.4f} peak_channels={audio.peak_channels}")
    finally:audio.shutdown()
if __name__=="__main__":run(sys.argv[1])
