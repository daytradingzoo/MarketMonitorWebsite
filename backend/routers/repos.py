"""Generic repo data endpoints — power the block system.

These endpoints are the backbone of the dashboard block system.
All chart blocks fetch data through /api/repos/{repo_id}/data,
meaning adding a new chart requires zero new API code.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.db import get_connection

logger = logging.getLogger(__name__)
router = APIRouter(tags=["repos"])

# Allowlist of valid table names for repos to prevent SQL injection
ALLOWED_TABLES = {"market_summary"}


def _fetchall_dict(conn, sql: str, params: tuple = ()) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def _get_repo(conn, repo_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, label, description, table_name, dimension_cols FROM repos WHERE id = %s",
            (repo_id,),
        )
        cols = [d[0] for d in cur.description]
        row = cur.fetchone()
    return dict(zip(cols, row)) if row else None


def _validate_column_names(conn, repo_id: str, columns: list[str]) -> list[str]:
    """Return only column names that exist in repo_columns for the given repo."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM repo_columns WHERE repo_id = %s",
            (repo_id,),
        )
        allowed = {row[0] for row in cur.fetchall()}
    # Always allow date and dimension columns
    allowed.update({"date", "universe", "sector", "price_bucket"})
    return [c for c in columns if c in allowed]


@router.get("/repos")
def list_repos() -> list[dict]:
    """List all registered repos."""
    conn = get_connection()
    try:
        return _fetchall_dict(conn, "SELECT id, label, description, dimension_cols FROM repos ORDER BY label")
    finally:
        conn.close()


@router.get("/repos/{repo_id}/columns")
def get_repo_columns(repo_id: str) -> list[dict]:
    """Return the column catalog for a repo (drives dashboard builder UI)."""
    conn = get_connection()
    try:
        repo = _get_repo(conn, repo_id)
        if not repo:
            raise HTTPException(status_code=404, detail=f"Repo '{repo_id}' not found")
        return _fetchall_dict(
            conn,
            """
            SELECT column_name, label, description, category, chart_type
            FROM repo_columns
            WHERE repo_id = %s
            ORDER BY category, label
            """,
            (repo_id,),
        )
    finally:
        conn.close()


@router.get("/repos/{repo_id}/data")
def get_repo_data(
    repo_id: str,
    metrics: str = Query(..., description="Comma-separated column names"),
    days: int = Query(252, ge=1, le=1260),
    universe: str | None = Query(None, description="Universe filter: all, nyse, nasdaq"),
    group_by: str | None = Query(None, description="Dimension to group by (e.g. sector)"),
) -> list[dict[str, Any]]:
    """Generic time-series data endpoint for any registered repo.

    Supports:
    - Column selection (metrics param)
    - Universe filtering (universe param)
    - GroupBy for multi-series/heatmap (group_by param)
    - Days lookback (days param)

    All column names are validated against repo_columns to prevent injection.
    """
    conn = get_connection()
    try:
        repo = _get_repo(conn, repo_id)
        if not repo:
            raise HTTPException(status_code=404, detail=f"Repo '{repo_id}' not found")

        table = repo["table_name"]
        if table not in ALLOWED_TABLES:
            raise HTTPException(status_code=400, detail="Repo table not accessible")

        requested_cols = [c.strip() for c in metrics.split(",") if c.strip()]
        safe_cols = _validate_column_names(conn, repo_id, requested_cols)

        if not safe_cols:
            raise HTTPException(status_code=400, detail="No valid metric columns requested")

        # Build SELECT clause — always include date
        select_cols = ["date"] + safe_cols
        if group_by and group_by not in select_cols:
            select_cols.insert(1, group_by)

        select_clause = ", ".join(select_cols)

        # Build WHERE clause
        where_parts = []
        params: list[Any] = []

        # Universe filter (applies to market_summary which has universe column)
        if universe and "universe" in _get_table_columns(conn, table):
            where_parts.append("universe = %s")
            params.append(universe)

        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

        sql = f"""
            SELECT {select_clause}
            FROM {table}
            {where_clause}
            ORDER BY date DESC
            LIMIT %s
        """
        params.append(days)

        return _fetchall_dict(conn, sql, tuple(params))

    finally:
        conn.close()


def _get_table_columns(conn, table_name: str) -> set[str]:
    """Return actual column names for a table."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = %s AND table_schema = 'public'
            """,
            (table_name,),
        )
        return {row[0] for row in cur.fetchall()}
