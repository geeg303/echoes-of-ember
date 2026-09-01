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
    parser.add_argument("--level", help="launch a registered World 1 level ID without save persistence")
    parser.add_argument("--editor", action="store_true", help="launch the developer-only level editor")
    parser.add_argument("--debug", action="store_true", help="enable nonpersistent developer diagnostics")
    parser.add_argument("--slot", type=int, choices=(1, 2, 3), default=None, help="directly load campaign save slot")
    parser.add_argument("--new-game", action="store_true", help="explicitly reset the selected slot")
    return parser.parse_args()


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )


def main() -> int:
    configure_logging()
    args = parse_args()
    if args.editor:
        from tools.level_editor import run_editor
        run_editor(args.level or "verdant_01", frames=5 if args.smoke_test else None, debug=args.debug)
        return 0
    if args.level and args.new_game:
        logging.error("--new-game cannot be combined with direct --level launch")
        return 2
    if args.debug and args.new_game:
        logging.error("--debug cannot be combined with --new-game; debug sessions never overwrite saves")
        return 2
    try:
        registry = WorldRegistry.load(DEFAULT_WORLD_REGISTRY)
        level_id = args.level or registry.level_ids[0]
        if level_id not in registry.level_paths:
            raise WorldRegistryError(f"unknown level id: {level_id}")
    except WorldRegistryError as exc:
        logging.error("Cannot launch: %s", exc)
        return 2
    direct_campaign = args.slot is not None or args.new_game
    slot_id = args.slot or 1
    game = Game(level_id=level_id, registry=registry, start_frontend=args.level is None and not direct_campaign, start_on_map=args.level is None and direct_campaign, slot_id=slot_id, new_game=args.new_game, persistence=direct_campaign, achievements_enabled=args.level is None and not args.debug, debug_enabled=args.debug)
    game.run(frame_limit=5 if args.smoke_test else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
