"""System status endpoints: data freshness, pipeline health."""

import logging
from typing import Any

from fastapi import APIRouter

from backend.db import get_connection

logger = logging.getLogger(__name__)
router = APIRouter(tags=["system"])


def _fetchone_dict(conn, sql: str, params: tuple = ()) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        row = cur.fetchone()
        return dict(zip(cols, row)) if row else None


@router.get("/status")
def get_status() -> dict[str, Any]:
    """Return last successful pipeline run and latest data date."""
    conn = get_connection()
    try:
        last_run = _fetchone_dict(
            conn,
            """
            SELECT run_date, status, rows_ingested, duration_seconds, created_at
            FROM job_runs
            WHERE status = 'success'
            ORDER BY run_date DESC
            LIMIT 1
            """,
        )
        latest_date = _fetchone_dict(
            conn,
            "SELECT MAX(date) AS latest_date FROM market_summary",
        )
        return {
            "last_successful_run": last_run,
            "latest_data_date": latest_date.get("latest_date") if latest_date else None,
        }
    finally:
        conn.close()
