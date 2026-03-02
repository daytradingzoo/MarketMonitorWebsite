"""Daily ingest: pull Polygon grouped daily bars and index bars, upsert into DB.

Usage:
    python -m jobs.ingest --date 2025-01-15
    python -m jobs.ingest  # defaults to previous trading day
"""

import argparse
import logging
import os
import sys
from datetime import date, timedelta
from typing import Any

import httpx
import psycopg2.extras
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.db import get_connection

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

POLYGON_BASE = "https://api.polygon.io"
INDEX_TICKERS = ["$I:SPX", "$I:NDX", "$I:VIX"]


def _api_key() -> str:
    return os.environ["POLYGON_API_KEY"]


def _previous_trading_day() -> date:
    """Return yesterday's date (caller verifies it was a trading day via empty response)."""
    return date.today() - timedelta(days=1)


# ---------------------------------------------------------------------------
# Stock bars
# ---------------------------------------------------------------------------

def fetch_grouped_daily(target_date: date) -> list[dict[str, Any]]:
    """Fetch all US stock adjusted daily bars for a given date from Polygon."""
    url = (
        f"{POLYGON_BASE}/v2/aggs/grouped/locale/us/market/stocks"
        f"/{target_date.isoformat()}"
    )
    params = {
        "adjusted": "true",
        "apiKey": _api_key(),
    }
    logger.info("Fetching grouped daily bars for %s", target_date)
    response = httpx.get(url, params=params, timeout=60.0)
    response.raise_for_status()

    data = response.json()
    results = data.get("results") or []
    logger.info("Received %d stock bars for %s", len(results), target_date)
    return results


def upsert_stock_bars(conn: Any, target_date: date, results: list[dict]) -> int:
    """Upsert stock OHLCV rows into daily_bars. Returns row count inserted/updated."""
    if not results:
        logger.info("No stock bars to upsert for %s (market holiday or empty response)", target_date)
        return 0

    rows = [
        (
            r["T"],                          # ticker
            target_date,
            r.get("o"),                      # open
            r.get("h"),                      # high
            r.get("l"),                      # low
            r.get("c"),                      # close
            r.get("v"),                      # volume
            r.get("vw"),                     # vwap
        )
        for r in results
        if r.get("T") and r.get("c") is not None
    ]

    sql = """
        INSERT INTO daily_bars (ticker, date, open, high, low, close, volume, vwap)
        VALUES %s
        ON CONFLICT (ticker, date) DO UPDATE SET
            open   = EXCLUDED.open,
            high   = EXCLUDED.high,
            low    = EXCLUDED.low,
            close  = EXCLUDED.close,
            volume = EXCLUDED.volume,
            vwap   = EXCLUDED.vwap
    """
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, rows, page_size=1000)

    conn.commit()
    logger.info("Upserted %d stock bars for %s", len(rows), target_date)
    return len(rows)


def upsert_stocks_reference(conn: Any, results: list[dict]) -> None:
    """Ensure all tickers from today's bars exist in the stocks reference table."""
    tickers = list({r["T"] for r in results if r.get("T")})
    if not tickers:
        return

    sql = """
        INSERT INTO stocks (ticker)
        SELECT unnest(%s::text[])
        ON CONFLICT (ticker) DO NOTHING
    """
    with conn.cursor() as cur:
        cur.execute(sql, (tickers,))
    conn.commit()
    logger.info("Ensured %d tickers in stocks table", len(tickers))


# ---------------------------------------------------------------------------
# Index bars
# ---------------------------------------------------------------------------

def fetch_index_bar(ticker: str, target_date: date) -> dict[str, Any] | None:
    """Fetch a single day's bar for an index ticker (e.g. $I:SPX)."""
    date_str = target_date.isoformat()
    url = (
        f"{POLYGON_BASE}/v2/aggs/ticker/{ticker}/range/1/day"
        f"/{date_str}/{date_str}"
    )
    params = {"apiKey": _api_key()}
    logger.info("Fetching index bar: %s for %s", ticker, date_str)

    response = httpx.get(url, params=params, timeout=30.0)
    response.raise_for_status()

    data = response.json()
    results = data.get("results") or []
    if not results:
        logger.info("No data for index %s on %s", ticker, date_str)
        return None
    return results[0]


def upsert_index_bars(conn: Any, target_date: date) -> None:
    """Fetch and upsert all index bars for the given date."""
    rows = []
    for ticker in INDEX_TICKERS:
        bar = fetch_index_bar(ticker, target_date)
        if bar is None:
            continue
        rows.append((
            ticker,
            target_date,
            bar.get("o"),
            bar.get("h"),
            bar.get("l"),
            bar.get("c"),
            bar.get("v"),
        ))

    if not rows:
        logger.info("No index bars to upsert for %s", target_date)
        return

    sql = """
        INSERT INTO index_bars (ticker, date, open, high, low, close, volume)
        VALUES %s
        ON CONFLICT (ticker, date) DO UPDATE SET
            open   = EXCLUDED.open,
            high   = EXCLUDED.high,
            low    = EXCLUDED.low,
            close  = EXCLUDED.close,
            volume = EXCLUDED.volume
    """
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, rows)
    conn.commit()
    logger.info("Upserted %d index bars for %s", len(rows), target_date)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def ingest(target_date: date) -> int:
    """Run the full ingest for a single date. Returns stock row count."""
    conn = get_connection()
    try:
        results = fetch_grouped_daily(target_date)
        if not results:
            logger.info("Empty Polygon response for %s — likely market holiday. Skipping.", target_date)
            return 0

        upsert_stocks_reference(conn, results)
        count = upsert_stock_bars(conn, target_date, results)
        upsert_index_bars(conn, target_date)
        return count
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest daily Polygon bars")
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=_previous_trading_day(),
        help="Date to ingest (YYYY-MM-DD). Defaults to yesterday.",
    )
    args = parser.parse_args()

    logger.info("Starting ingest for date: %s", args.date)
    count = ingest(args.date)
    logger.info("Ingest complete. Rows: %d", count)


if __name__ == "__main__":
    main()
