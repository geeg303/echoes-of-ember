"""Application entry point for Echoes of Ember."""

from __future__ import annotations

import argparse
import logging

from core.game import Game


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch Echoes of Ember")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="run a few frames and exit (useful for automated checks)",
    )
    return parser.parse_args()


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )


def main() -> int:
    configure_logging()
    args = parse_args()
    game = Game()
    game.run(frame_limit=5 if args.smoke_test else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

