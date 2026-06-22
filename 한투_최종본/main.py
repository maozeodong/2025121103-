"""Application entry point."""

from __future__ import annotations

import sys

from config import Settings
from logger import configure_logging
from trader import Trader


def main() -> int:
    try:
        settings = Settings.from_env()
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    logger = configure_logging(settings.log_dir)
    try:
        Trader(settings, logger).run()
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

