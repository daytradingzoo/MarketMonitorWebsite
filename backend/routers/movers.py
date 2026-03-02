"""Top movers, extreme candles, volume leaders, momentum screener endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Query

from backend.db import get_connection

logger = logging.getLogger(__name__)
router = APIRouter(tags=["movers"])

VALID_MOMENTUM_TYPES = {
    "up4", "dn4", "up25q", "dn25q", "up25m", "dn25m",
    "up50m", "dn50m", "up1334", "dn1334",
}


def _fetchall_dict(conn, sql: str, params: tuple = ()) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


@router.get("/movers")
def get_movers(n: int = Query(20, ge=1, le=100)) -> dict[str, Any]:
    """Return top N gainers and losers from the latest day in daily_bars."""
    conn = get_connection()
    try:
        sql = """
            WITH latest AS (
                SELECT MAX(date) AS d FROM daily_bars
            ),
            prior AS (
                SELECT ticker, close AS prior_close
                FROM daily_bars, latest
                WHERE date = (
                    SELECT MAX(date) FROM daily_bars WHERE date < latest.d
                )
            ),
            today AS (
                SELECT b.ticker, b.date, b.close, b.volume, s.name, s.sector
                FROM daily_bars b, latest
                LEFT JOIN stocks s ON s.ticker = b.ticker
                WHERE b.date = latest.d
            ),
            ranked AS (
                SELECT
                    t.ticker, t.date, t.close, t.volume, t.name, t.sector,
                    p.prior_close,
                    ROUND(((t.close - p.prior_close) / NULLIF(p.prior_close, 0) * 100)::numeric, 2) AS pct_change
                FROM today t
                LEFT JOIN prior p ON p.ticker = t.ticker
                WHERE p.prior_close IS NOT NULL
            )
            SELECT ticker, date, close, volume, name, sector, prior_close, pct_change
            FROM ranked
            ORDER BY pct_change DESC
        """
        rows = _fetchall_dict(conn, sql)
        gainers = rows[:n]
        losers = list(reversed(rows))[:n]
        return {"gainers": gainers, "losers": losers}
    finally:
        conn.close()


@router.get("/movers/extreme")
def get_extreme_movers(universe: str = "all") -> dict[str, Any]:
    """Return today's extremeup and extremedn counts from market_summary."""
    conn = get_connection()
    try:
        rows = _fetchall_dict(
            conn,
            "SELECT date, extremeup, extremedn FROM market_summary WHERE universe = %s ORDER BY date DESC LIMIT 1",
            (universe,),
        )
        return rows[0] if rows else {}
    finally:
        conn.close()


@router.get("/movers/volume")
def get_volume_leaders(n: int = Query(20, ge=1, le=100)) -> list[dict]:
    """Return stocks with highest RVOL from the latest daily_metrics."""
    conn = get_connection()
    try:
        return _fetchall_dict(
            conn,
            """
            SELECT dm.ticker, dm.date, dm.rvol, dm.rsi14, dm.atr21,
                   s.name, s.sector
            FROM daily_metrics dm
            LEFT JOIN stocks s ON s.ticker = dm.ticker
            WHERE dm.date = (SELECT MAX(date) FROM daily_metrics)
              AND dm.rvol IS NOT NULL
            ORDER BY dm.rvol DESC
            LIMIT %s
            """,
            (n,),
        )
    finally:
        conn.close()


@router.get("/movers/momentum")
def get_momentum_movers(
    metric_type: str = Query("up25m", description="One of: up4, dn4, up25q, dn25q, up25m, dn25m, up50m, dn50m, up1334, dn1334"),
    universe: str = "all",
) -> dict[str, Any]:
    """Return count of momentum movers of the given type from market_summary."""
    if metric_type not in VALID_MOMENTUM_TYPES:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid metric_type. Must be one of: {sorted(VALID_MOMENTUM_TYPES)}")

    conn = get_connection()
    try:
        rows = _fetchall_dict(
            conn,
            f"SELECT date, {metric_type} AS count FROM market_summary WHERE universe = %s ORDER BY date DESC LIMIT 1",
            (universe,),
        )
        return rows[0] if rows else {}
    finally:
        conn.close()
