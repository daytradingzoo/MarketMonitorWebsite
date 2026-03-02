"""Run all pending migration files in order.

Usage:
    python -m backend.migrate
"""

import logging
import os
import sys

from backend.db import run_migration

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")


def main() -> None:
    files = sorted(f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql"))
    if not files:
        logger.info("No migration files found.")
        return

    for filename in files:
        path = os.path.join(MIGRATIONS_DIR, filename)
        logger.info("Running migration: %s", filename)
        run_migration(path)

    logger.info("All migrations applied.")


if __name__ == "__main__":
    main()
