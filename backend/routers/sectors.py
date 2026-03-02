"""Sector performance endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Query

from backend.db import get_connection

logger = logging.getLogger(__name__)
router = APIRouter(tags=["sectors"])


def _fetchall_dict(conn, sql: str, params: tuple = ()) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


@router.get("/sectors")
def get_sectors(days: int = Query(1, ge=1, le=30)) -> list[dict]:
    """Return sector performance for the latest day from daily_metrics + stocks."""
    conn = get_connection()
    try:
        return _fetchall_dict(
            conn,
            """
            WITH latest AS (SELECT MAX(date) AS d FROM daily_bars),
            today_bars AS (
                SELECT b.ticker, b.close, b.volume
                FROM daily_bars b, latest WHERE b.date = latest.d
            ),
            prior_bars AS (
                SELECT b.ticker, b.close AS prior_close
                FROM daily_bars b, latest
                WHERE b.date = (SELECT MAX(date) FROM daily_bars WHERE date < latest.d)
            )
            SELECT
                s.sector,
                COUNT(*) AS stock_count,
                ROUND(AVG(((tb.close - pb.prior_close) / NULLIF(pb.prior_close,0) * 100))::numeric, 2) AS avg_pct_change,
                SUM(CASE WHEN tb.close > pb.prior_close THEN 1 ELSE 0 END) AS advancing,
                SUM(CASE WHEN tb.close < pb.prior_close THEN 1 ELSE 0 END) AS declining,
                ROUND(AVG(dm.rvol)::numeric, 2) AS avg_rvol
            FROM today_bars tb
            JOIN prior_bars pb ON pb.ticker = tb.ticker
            JOIN stocks s ON s.ticker = tb.ticker
            LEFT JOIN daily_metrics dm ON dm.ticker = tb.ticker
                AND dm.date = (SELECT d FROM latest)
            WHERE s.sector IS NOT NULL
            GROUP BY s.sector
            ORDER BY avg_pct_change DESC
            """,
        )
    finally:
        conn.close()


@router.get("/sectors/{sector_name}")
def get_sector_stocks(
    sector_name: str,
    n: int = Query(50, ge=1, le=200),
) -> list[dict]:
    """Return constituent stocks for a sector, sorted by day performance."""
    conn = get_connection()
    try:
        return _fetchall_dict(
            conn,
            """
            WITH latest AS (SELECT MAX(date) AS d FROM daily_bars),
            today_bars AS (
                SELECT b.ticker, b.close, b.volume
                FROM daily_bars b, latest WHERE b.date = latest.d
            ),
            prior_bars AS (
                SELECT b.ticker, b.close AS prior_close
                FROM daily_bars b, latest
                WHERE b.date = (SELECT MAX(date) FROM daily_bars WHERE date < latest.d)
            )
            SELECT
                s.ticker, s.name, s.sector, s.industry,
                tb.close, tb.volume, pb.prior_close,
                ROUND(((tb.close - pb.prior_close) / NULLIF(pb.prior_close,0) * 100)::numeric, 2) AS pct_change,
                dm.rvol, dm.rsi14, dm.atr21, dm.is_52wk_high, dm.is_52wk_low
            FROM stocks s
            JOIN today_bars tb ON tb.ticker = s.ticker
            JOIN prior_bars pb ON pb.ticker = s.ticker
            LEFT JOIN daily_metrics dm ON dm.ticker = s.ticker
                AND dm.date = (SELECT d FROM latest)
            WHERE LOWER(s.sector) = LOWER(%s)
            ORDER BY pct_change DESC
            LIMIT %s
            """,
            (sector_name, n),
        )
    finally:
        conn.close()
