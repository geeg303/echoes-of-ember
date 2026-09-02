"""Headless long-run stability check for Phase 23 performance work."""
from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
import tracemalloc
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def run(frames: int, draw_every: int) -> dict[str, int | float]:
    from core.game import Game

    game = Game(level_id="verdant_boss", debug_enabled=False, achievements_enabled=False, persistence=False)
    tracemalloc.start()
    started = time.perf_counter()
    first_window = 0
    try:
        trigger = game.boss_system.definition.trigger
        game.player.reposition((trigger.centerx, trigger.bottom - game.player.rect.height))
        game.camera.snap_to(game.player.rect)
        for frame in range(frames):
            if frame % 240 == 0:
                game.effects.spawn("enemy_defeat", game.player.rect.center, count_scale=1.5)
            game.update(1.0 / 60.0)
            if frame % draw_every == 0:
                game.draw()
            if frame == frames // 4:
                gc.collect()
                first_window = tracemalloc.get_traced_memory()[0]
        gc.collect()
        current, peak = tracemalloc.get_traced_memory()
        elapsed = time.perf_counter() - started
        result = {
            "frames": frames,
            "draw_every": draw_every,
            "elapsed_seconds": round(elapsed, 3),
            "current_bytes": current,
            "peak_bytes": peak,
            "growth_after_warmup_bytes": current - first_window,
            "particles_final": game.effects.particle_count,
            "projectiles_final": len(game.projectiles.projectiles),
            "debug_events": len(game.debug.events),
            "audio_events": len(game.audio.events),
            "achievement_toasts": len(game.achievement_toasts.items),
            "tile_chunks": game.level.tilemap.cached_chunk_count,
            "tile_chunk_limit": game.level.tilemap.maximum_chunk_count,
        }
        if result["tile_chunks"] > result["tile_chunk_limit"]:
            raise RuntimeError("tile chunk cache exceeded its natural bound")
        if result["debug_events"] > 50 or result["audio_events"] > 256:
            raise RuntimeError("diagnostic history exceeded its configured bound")
        return result
    finally:
        tracemalloc.stop()
        game.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", type=int, default=18_000)
    parser.add_argument("--draw-every", type=int, default=30)
    args = parser.parse_args()
    print(json.dumps(run(max(600, args.frames), max(1, args.draw_every)), indent=2))


if __name__ == "__main__":
    main()
