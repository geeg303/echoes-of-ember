"""Application entry point for Echoes of Ember."""

from __future__ import annotations

import argparse
import logging

from core.game import Game
from world.campaign import DEFAULT_WORLD_REGISTRY, WorldRegistry, WorldRegistryError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch Echoes of Ember")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="run a few frames and exit (useful for automated checks)",
    )
    parser.add_argument("--level", help="launch a registered World 1 level ID")
    return parser.parse_args()


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )


def main() -> int:
    configure_logging()
    args = parse_args()
    try:
        registry = WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
        level_id = args.level or registry.level_ids[0]
        if level_id not in registry.level_paths:
            raise WorldRegistryError(f"unknown level id: {level_id}")
    except WorldRegistryError as exc:
        logging.error("Cannot launch: %s", exc)
        return 2
    game = Game(level_id=level_id, registry=registry, start_on_map=args.level is None)
    game.run(frame_limit=5 if args.smoke_test else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

