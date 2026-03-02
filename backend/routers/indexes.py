"""Index data endpoints: SPX, NDX, VIX with MAs and RSI."""

import logging
from typing import Any

from fastapi import APIRouter, Query

from backend.db import get_connection

logger = logging.getLogger(__name__)
router = APIRouter(tags=["indexes"])


def _fetchall_dict(conn, sql: str, params: tuple = ()) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


@router.get("/indexes")
def get_indexes(universe: str = "all") -> dict[str, Any]:
    """Return latest index values, MAs, RSI, and ROC from market_summary."""
    conn = get_connection()
    try:
        rows = _fetchall_dict(
            conn,
            """
            SELECT date,
                   spx, spxrsi, ndx, ndxrsi, vix,
                   spx005ma, spx010ma, spx020ma, spx050ma, spx200ma,
                   ndx005ma, ndx010ma, ndx020ma, ndx050ma, ndx200ma,
                   rocspx005, rocspx010, rocspx020,
                   rocndx005, rocndx010, rocndx020
            FROM market_summary
            WHERE universe = %s
            ORDER BY date DESC
            LIMIT 1
            """,
            (universe,),
        )
        return rows[0] if rows else {}
    finally:
        conn.close()


@router.get("/indexes/history")
def get_index_history(
    ticker: str = Query("$I:SPX", description="Index ticker: $I:SPX, $I:NDX, $I:VIX"),
    days: int = Query(252, ge=1, le=1260),
) -> list[dict]:
    """Return raw index bar history from index_bars table."""
    conn = get_connection()
    try:
        return _fetchall_dict(
            conn,
            """
            SELECT ticker, date, open, high, low, close, volume
            FROM index_bars
            WHERE ticker = %s
            ORDER BY date DESC
            LIMIT %s
            """,
            (ticker, days),
        )
    finally:
        conn.close()
