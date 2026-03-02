"""Individual stock detail endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.db import get_connection

logger = logging.getLogger(__name__)
router = APIRouter(tags=["stocks"])


def _fetchall_dict(conn, sql: str, params: tuple = ()) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


@router.get("/stock/{ticker}")
def get_stock(ticker: str) -> dict[str, Any]:
    """Return latest metrics for a single ticker."""
    ticker = ticker.upper()
    conn = get_connection()
    try:
        rows = _fetchall_dict(
            conn,
            """
            SELECT dm.*, s.name, s.sector, s.industry, s.exchange, s.market_cap
            FROM daily_metrics dm
            LEFT JOIN stocks s ON s.ticker = dm.ticker
            WHERE dm.ticker = %s
            ORDER BY dm.date DESC
            LIMIT 1
            """,
            (ticker,),
        )
        if not rows:
            raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found")
        return rows[0]
    finally:
        conn.close()


@router.get("/stock/{ticker}/bars")
def get_stock_bars(
    ticker: str,
    days: int = Query(252, ge=1, le=1260),
) -> list[dict]:
    """Return OHLCV history for a single ticker (for price charts)."""
    ticker = ticker.upper()
    conn = get_connection()
    try:
        rows = _fetchall_dict(
            conn,
            """
            SELECT ticker, date, open, high, low, close, volume, vwap
            FROM daily_bars
            WHERE ticker = %s
            ORDER BY date DESC
            LIMIT %s
            """,
            (ticker, days),
        )
        if not rows:
            raise HTTPException(status_code=404, detail=f"No bar data for {ticker}")
        return rows
    finally:
        conn.close()
