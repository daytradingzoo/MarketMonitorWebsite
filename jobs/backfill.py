"""Historical backfill: download Polygon flat files year by year and build full history.

Run once manually from the Cursor terminal — NOT scheduled on Render.

Usage:
    python -m jobs.backfill --start-year 2004 --end-year 2024
    python -m jobs.backfill --start-year 2004  # end defaults to last full year

Strategy:
    1. Download each year's day-aggregate flat file from Polygon S3
    2. Load into pandas, compute per-stock rolling metrics (calculate.py logic)
    3. Aggregate market_summary rows chronologically, carrying McClellan EMA state
    4. Write results to DB
    5. Purge daily_bars older than 252 days after all years are processed

The backfill intentionally loads all history in memory one year at a time to
manage memory usage. calculate.py and aggregate.py expose functions that are
called directly here with pandas DataFrames rather than going through the DB
query layer used in the daily pipeline.
"""

import argparse
import gzip
import io
import logging
import os
import sys
from datetime import date

import boto3
import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.db import get_connection
from jobs.calculate import compute_metrics_for_universe
from jobs.aggregate import aggregate_market_summary, get_last_mcclellan_state

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

S3_BUCKET = "flatfiles.polygon.io"
S3_PREFIX = "us_stocks_sip/day_aggs_v1"


# ---------------------------------------------------------------------------
# S3 flat file download
# ---------------------------------------------------------------------------

def list_flat_files(year: int) -> list[str]:
    """List all day-aggregate flat file keys for the given year."""
    s3 = boto3.client("s3")
    prefix = f"{S3_PREFIX}/{year}/"
    paginator = s3.get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".csv.gz"):
                keys.append(key)
    logger.info("Found %d flat files for year %d", len(keys), year)
    return sorted(keys)


def download_flat_file(key: str) -> pd.DataFrame:
    """Download a single flat file from S3 and return as DataFrame."""
    s3 = boto3.client("s3")
    logger.info("Downloading: %s", key)
    obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
    body = obj["Body"].read()

    with gzip.open(io.BytesIO(body), "rt") as f:
        df = pd.read_csv(f)

    # Polygon flat file columns: ticker, volume, open, close, high, low,
    # window_start, transactions, vwap (column names may vary by version)
    # Normalise to standard names
    rename_map = {
        "ticker": "ticker",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume",
        "vwap": "vwap",
        "window_start": "window_start",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Parse date from window_start (nanosecond epoch) or date column
    if "window_start" in df.columns:
        df["date"] = pd.to_datetime(df["window_start"], unit="ns", utc=True).dt.date
    elif "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.date

    required = {"ticker", "date", "open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        logger.warning("Flat file missing columns: %s — skipping", missing)
        return pd.DataFrame()

    return df[list(required | {"vwap"}.intersection(df.columns))]


def load_year_from_s3(year: int) -> pd.DataFrame:
    """Download all flat files for a year and concatenate into one DataFrame."""
    keys = list_flat_files(year)
    if not keys:
        logger.warning("No flat files found for year %d", year)
        return pd.DataFrame()

    frames = []
    for key in keys:
        df = download_flat_file(key)
        if not df.empty:
            frames.append(df)

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(["ticker", "date"]).reset_index(drop=True)
    logger.info("Year %d: %d rows across %d tickers", year, len(combined), combined["ticker"].nunique())
    return combined


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def upsert_bars_to_db(conn, df: pd.DataFrame) -> None:
    """Upsert raw bars into daily_bars (used to keep rolling window current)."""
    import psycopg2.extras

    rows = [
        (
            row.ticker,
            row.date,
            row.open,
            row.high,
            row.low,
            row.close,
            int(row.volume),
            getattr(row, "vwap", None),
        )
        for row in df.itertuples(index=False)
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
        psycopg2.extras.execute_values(cur, sql, rows, page_size=2000)
    conn.commit()


def upsert_tickers(conn, tickers: list[str]) -> None:
    """Ensure all tickers exist in the stocks reference table."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO stocks (ticker) SELECT unnest(%s::text[]) ON CONFLICT DO NOTHING",
            (tickers,),
        )
    conn.commit()


def purge_old_bars(conn, cutoff_date: date) -> None:
    """Delete daily_bars and daily_metrics older than cutoff_date."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM daily_bars WHERE date < %s", (cutoff_date,))
        bar_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM daily_metrics WHERE date < %s", (cutoff_date,))
        metric_count = cur.fetchone()[0]

    logger.warning(
        "Purging %d daily_bars and %d daily_metrics rows older than %s",
        bar_count, metric_count, cutoff_date,
    )
    with conn.cursor() as cur:
        cur.execute("DELETE FROM daily_bars WHERE date < %s", (cutoff_date,))
        cur.execute("DELETE FROM daily_metrics WHERE date < %s", (cutoff_date,))
    conn.commit()
    logger.info("Purge complete.")


# ---------------------------------------------------------------------------
# Main backfill loop
# ---------------------------------------------------------------------------

def backfill(start_year: int, end_year: int) -> None:
    """Download and process all years from start_year to end_year inclusive."""
    conn = get_connection()

    # Carry McClellan EMA state across years
    mcclellan_state = get_last_mcclellan_state(conn)
    logger.info("Starting McClellan EMA state: %s", mcclellan_state)

    # Accumulate bars across year boundaries for rolling windows
    # We keep a trailing buffer so 252-day windows work at year boundaries
    trailing_buffer: pd.DataFrame = pd.DataFrame()

    for year in range(start_year, end_year + 1):
        logger.info("=== Processing year %d ===", year)
        year_df = load_year_from_s3(year)

        if year_df.empty:
            logger.warning("No data for year %d — skipping", year)
            continue

        # Combine with trailing buffer from prior year for lookback continuity
        if not trailing_buffer.empty:
            combined = pd.concat([trailing_buffer, year_df], ignore_index=True)
        else:
            combined = year_df

        combined = combined.sort_values(["ticker", "date"]).reset_index(drop=True)

        # Upsert raw bars to DB (needed for daily metrics view and purge boundary)
        upsert_tickers(conn, combined["ticker"].unique().tolist())
        upsert_bars_to_db(conn, year_df)  # only this year's new bars

        # Compute per-stock metrics on combined data (with lookback buffer)
        logger.info("Computing per-stock metrics for year %d", year)
        metrics_df = compute_metrics_for_universe(combined)

        # Filter metrics to only this year's dates for writing
        year_dates = set(year_df["date"].unique())
        metrics_this_year = metrics_df[metrics_df["date"].isin(year_dates)]

        # Aggregate market_summary for each date in this year, chronologically
        logger.info("Aggregating market_summary for year %d", year)
        mcclellan_state = aggregate_market_summary(
            conn=conn,
            metrics_df=metrics_this_year,
            index_conn=conn,
            mcclellan_state=mcclellan_state,
            mode="backfill",
        )

        # Keep last 252 days of combined as trailing buffer for next year
        max_date = combined["date"].max()
        cutoff = pd.Timestamp(max_date) - pd.DateOffset(days=365)
        trailing_buffer = combined[combined["date"] > cutoff.date()].copy()

        logger.info("Year %d complete. McClellan state: %s", year, mcclellan_state)

    # Purge daily_bars and daily_metrics older than 252 trading days
    from datetime import date as date_type
    today = date_type.today()
    # Approximate 252 trading days as 365 calendar days for the cutoff
    cutoff_date = pd.bdate_range(end=today, periods=253)[0].date()
    purge_old_bars(conn, cutoff_date)

    conn.close()
    logger.info("Backfill complete.")


def main() -> None:
    current_year = date.today().year
    parser = argparse.ArgumentParser(description="Historical backfill from Polygon flat files")
    parser.add_argument("--start-year", type=int, default=2004, help="First year to load")
    parser.add_argument("--end-year", type=int, default=current_year - 1, help="Last year to load")
    args = parser.parse_args()

    logger.info("Backfill: %d → %d", args.start_year, args.end_year)
    backfill(args.start_year, args.end_year)


if __name__ == "__main__":
    main()
