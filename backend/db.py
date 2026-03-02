"""Database connection and cursor helpers."""

import logging
import os

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def get_connection() -> psycopg2.extensions.connection:
    """Return a new psycopg2 connection from DATABASE_URL."""
    url = os.environ["DATABASE_URL"]
    return psycopg2.connect(url)


def run_migration(sql_path: str) -> None:
    """Execute a SQL migration file against the database."""
    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        logger.info("Migration applied: %s", sql_path)
    except Exception as e:
        conn.rollback()
        logger.error("Migration failed: %s — %s", sql_path, e)
        raise
    finally:
        conn.close()
