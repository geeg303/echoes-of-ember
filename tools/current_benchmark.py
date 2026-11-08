"""Headless 600-frame benchmark scenarios for the Ember Current prototype."""

from __future__ import annotations
import argparse, os, statistics, time
from dataclasses import replace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from core.game import Game
from entities.projectile import EmberPulseProjectile, Faction
from settings import PROJECT_ROOT
from world.campaign import DEFAULT_WORLD_REGISTRY, WorldRegistry
from world.ember_current import EmberCurrentDefinition, EmberCurrentRuntime

SCENARIOS = ("normal", "visible", "projectiles", "effects", "combination", "stress")


def create_game() -> Game:
    registry = WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
    paths = dict(registry.level_paths)
    level_id = "prototype_glassreach_currents"
    paths[level_id] = PROJECT_ROOT / "data" / "levels" / f"{level_id}.json"
    return Game(
        level_id=level_id,
        registry=replace(registry, level_ids=registry.level_ids + (level_id,), level_paths=paths),
        achievements_enabled=False,
        persistence=False,
    )


def run(name: str, frames: int = 600) -> dict[str, float | int]:
    game = create_game()
    try:
        positions = {
            "normal": (700, 700),
            "visible": (4900, 650),
            "projectiles": (2700, 700),
            "effects": (4900, 650),
            "combination": (4050, 650),
            "stress": (4900, 650),
        }
        game.player.reposition(positions[name])
        game.camera.snap_to(game.player.rect)
        if name == "stress":
            originals = tuple(game.ember_currents.currents.values())
            for index in range(8):
                source = originals[index % len(originals)].definition
                copied = EmberCurrentDefinition(
                    f"stress_{index}",
                    pygame.Rect(
                        game.player.rect.x - 500 + (index % 4) * 240,
                        game.player.rect.y - 300 + (index // 4) * 280,
                        500,
                        500,
                    ),
                    source.direction,
                    source.strength,
                    source.affects,
                    True,
                    source.style,
                )
                game.ember_currents.currents[copied.current_id] = EmberCurrentRuntime(copied, True)
        samples = []
        for frame in range(frames):
            if name in {"projectiles", "combination", "stress"} and frame % 20 == 0:
                shot = EmberPulseProjectile(
                    game.projectiles.new_id("bench"),
                    game.player.rect.center,
                    pygame.Vector2(720, 0),
                    1,
                    Faction.PLAYER,
                    0.85,
                    owner_id="nova",
                )
                game.projectiles.spawn(shot)
            if name in {"effects", "stress"} and frame % 15 == 0:
                game.effects.spawn("ember_pulse_impact", game.player.rect.center)
            started = time.perf_counter()
            game.update(1 / 60)
            game.draw()
            samples.append((time.perf_counter() - started) * 1000)
        ordered = sorted(samples)
        return {
            "frames": frames,
            "mean_ms": statistics.mean(samples),
            "p95_ms": ordered[max(0, int(len(ordered) * 0.95) - 1)],
            "max_ms": max(samples),
            "spikes_16_67": sum(value > 16.67 for value in samples),
        }
    finally:
        game.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=SCENARIOS + ("all",))
    parser.add_argument("--frames", type=int, default=600)
    args = parser.parse_args()
    names = SCENARIOS if args.scenario == "all" else (args.scenario,)
    for name in names:
        result = run(name, max(30, args.frames))
        print(
            f"{name:12} frames={result['frames']} mean={result['mean_ms']:.3f} p95={result['p95_ms']:.3f} max={result['max_ms']:.3f} spikes={result['spikes_16_67']}"
        )


if __name__ == "__main__":
    main()
