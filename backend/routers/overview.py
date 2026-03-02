"""Overview and breadth endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Query

from backend.db import get_connection

logger = logging.getLogger(__name__)
router = APIRouter(tags=["overview"])


def _fetchall_dict(conn, sql: str, params: tuple = ()) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


@router.get("/overview")
def get_overview(universe: str = "all") -> dict[str, Any]:
    """Return the latest market_summary row for the given universe."""
    conn = get_connection()
    try:
        rows = _fetchall_dict(
            conn,
            "SELECT * FROM market_summary WHERE universe = %s ORDER BY date DESC LIMIT 1",
            (universe,),
        )
        return rows[0] if rows else {}
    finally:
        conn.close()


@router.get("/overview/history")
def get_overview_history(
    days: int = Query(252, ge=1, le=1260),
    universe: str = "all",
) -> list[dict]:
    """Return market_summary time series for charting."""
    conn = get_connection()
    try:
        return _fetchall_dict(
            conn,
            """
            SELECT * FROM market_summary
            WHERE universe = %s
            ORDER BY date DESC
            LIMIT %s
            """,
            (universe, days),
        )
    finally:
        conn.close()


@router.get("/breadth/history")
def get_breadth_history(
    days: int = Query(60, ge=1, le=1260),
    universe: str = "all",
) -> list[dict]:
    """Return advance/decline + McClellan time series."""
    conn = get_connection()
    try:
        return _fetchall_dict(
            conn,
            """
            SELECT date, adv, dec, voladv, voldec, rat, rat5, rat10,
                   volrat, volrat5, volrat10, mcclellan, adv_ema19, adv_ema39,
                   newhi, newlo, newhi010ma, newlo010ma, universe
            FROM market_summary
            WHERE universe = %s
            ORDER BY date DESC
            LIMIT %s
            """,
            (universe, days),
        )
    finally:
        conn.close()


@router.get("/breadth/ratios")
def get_breadth_ratios(universe: str = "all") -> dict[str, Any]:
    """Return latest A/D and volume ratios."""
    conn = get_connection()
    try:
        rows = _fetchall_dict(
            conn,
            """
            SELECT date, rat, rat5, rat10, volrat, volrat5, volrat10
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


@router.get("/breakouts")
def get_breakouts(universe: str = "all") -> dict[str, Any]:
    """Return latest breakout quality ratios."""
    conn = get_connection()
    try:
        rows = _fetchall_dict(
            conn,
            """
            SELECT date,
                   bu021ok, bd021ok, bu021nok, bd021nok, ratbu021, ratbd021,
                   bu063ok, bd063ok, bu063nok, bd063nok, ratbu063, ratbd063,
                   bu252ok, bd252ok, bu252nok, bd252nok, ratbu252, ratbd252
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
