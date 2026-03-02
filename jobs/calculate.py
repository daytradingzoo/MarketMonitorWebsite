"""Per-stock metric calculation: vectorized rolling indicators via pandas/pandas_ta.

Two modes:
    daily   — load last 252 days from DB for each ticker, compute today's row
    backfill — accepts a pre-loaded DataFrame (called from backfill.py)

Usage (daily mode):
    python -m jobs.calculate --date 2025-01-15
    python -m jobs.calculate  # defaults to yesterday
"""

import argparse
import logging
import os
import sys
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd
import pandas_ta as ta
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

LOOKBACK_DAYS = 252    # maximum rolling window needed
LIQFILTER_MIN = 250_000.0
PRICEFILTER_MIN = 5.0
PRICE_LOOKBACK = 20    # close[20] >= 5 for pricefilter


# ---------------------------------------------------------------------------
# Core computation — operates on a DataFrame with columns:
#   ticker, date, open, high, low, close, volume
# Returns DataFrame with all metric columns added.
# ---------------------------------------------------------------------------

def _compute_ticker_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all rolling indicators for a single ticker's time series.

    Input df must be sorted by date ascending.
    Returns df with metric columns added (NaN for insufficient history).
    """
    c = df["close"]
    h = df["high"]
    lo = df["low"]
    v = df["volume"]

    # Moving averages
    df["sma20"]  = c.rolling(20).mean()
    df["sma40"]  = c.rolling(40).mean()
    df["sma50"]  = c.rolling(50).mean()
    df["sma200"] = c.rolling(200).mean()

    # Dollar volume MA (liquidity filter)
    dollar_vol = c * v
    df["ema_dollar_vol_20"] = dollar_vol.rolling(20).mean()
    df["liqfilter"]  = df["ema_dollar_vol_20"] >= LIQFILTER_MIN

    # Price filter: close 20 days ago >= $5
    df["pricefilter"] = c.shift(PRICE_LOOKBACK) >= PRICEFILTER_MIN

    # Volume rolling average for RVOL
    vol_ma20 = v.rolling(20).mean()
    df["rvol"] = v / vol_ma20

    # IBS — Internal Bar Strength
    bar_range = h - lo
    df["ibs"] = (c - lo) / bar_range.replace(0, np.nan)

    # RSI(14)
    df["rsi14"] = ta.rsi(c, length=14)

    # ATR
    df["atr14"] = ta.atr(h, lo, c, length=14)
    df["atr21"] = ta.atr(h, lo, c, length=21)

    # High/low lookbacks (rolling max/min of close)
    df["hhv007"] = c.rolling(7).max()
    df["hhv021"] = c.rolling(21).max()
    df["hhv063"] = c.rolling(63).max()
    df["hhv252"] = c.rolling(252).max()
    df["llv007"] = c.rolling(7).min()
    df["llv021"] = c.rolling(21).min()
    df["llv063"] = c.rolling(63).min()
    df["llv252"] = c.rolling(252).min()

    # 52-week high/low flags
    df["is_52wk_high"] = c == df["hhv252"]
    df["is_52wk_low"]  = c == df["llv252"]

    return df


def compute_metrics_for_universe(bars_df: pd.DataFrame) -> pd.DataFrame:
    """Compute metrics for all tickers in bars_df.

    Args:
        bars_df: DataFrame with columns ticker, date, open, high, low, close, volume.
                 Should include enough history for rolling windows (252+ days per ticker).

    Returns:
        DataFrame with ticker, date, and all metric columns. One row per (ticker, date).
    """
    bars_df = bars_df.copy()
    bars_df["date"] = pd.to_datetime(bars_df["date"])
    bars_df = bars_df.sort_values(["ticker", "date"]).reset_index(drop=True)

    result_frames = []
    tickers = bars_df["ticker"].unique()
    logger.info("Computing metrics for %d tickers", len(tickers))

    for ticker in tickers:
        tdf = bars_df[bars_df["ticker"] == ticker].copy().reset_index(drop=True)
        if len(tdf) < 1:
            continue
        try:
            tdf = _compute_ticker_metrics(tdf)
            result_frames.append(tdf)
        except Exception as e:
            logger.warning("Failed metrics for %s: %s", ticker, e)

    if not result_frames:
        return pd.DataFrame()

    out = pd.concat(result_frames, ignore_index=True)
    out["date"] = out["date"].dt.date
    return out


# ---------------------------------------------------------------------------
# DB I/O — daily mode
# ---------------------------------------------------------------------------

def load_bars_for_date(conn: Any, target_date: date) -> pd.DataFrame:
    """Load last 252 days of daily_bars up to and including target_date."""
    cutoff = target_date - timedelta(days=365)  # generous buffer for trading days
    sql = """
        SELECT ticker, date, open, high, low, close, volume
        FROM daily_bars
        WHERE date BETWEEN %s AND %s
        ORDER BY ticker, date
    """
    with conn.cursor() as cur:
        cur.execute(sql, (cutoff, target_date))
        rows = cur.fetchall()
        cols = ["ticker", "date", "open", "high", "low", "close", "volume"]
    return pd.DataFrame(rows, columns=cols)


def upsert_daily_metrics(conn: Any, metrics_df: pd.DataFrame, target_date: date) -> int:
    """Upsert daily_metrics rows for target_date only."""
    if metrics_df.empty or "date" not in metrics_df.columns:
        logger.info("No metrics computed for %s", target_date)
        return 0
    today_metrics = metrics_df[metrics_df["date"] == target_date].copy()
    if today_metrics.empty:
        logger.info("No metrics to upsert for %s", target_date)
        return 0

    metric_cols = [
        "sma20", "sma40", "sma50", "sma200",
        "ema_dollar_vol_20", "liqfilter", "pricefilter",
        "rsi14", "atr14", "atr21", "ibs", "rvol",
        "hhv007", "hhv021", "hhv063", "hhv252",
        "llv007", "llv021", "llv063", "llv252",
        "is_52wk_high", "is_52wk_low",
    ]

    def _none_if_nan(v: Any) -> Any:
        if v is None:
            return None
        try:
            return None if np.isnan(float(v)) else v
        except (TypeError, ValueError):
            return v

    rows = []
    for row in today_metrics.itertuples(index=False):
        r = [row.ticker, row.date]
        for col in metric_cols:
            r.append(_none_if_nan(getattr(row, col, None)))
        rows.append(tuple(r))

    placeholders = ", ".join(["%s"] * (2 + len(metric_cols)))
    col_names = "ticker, date, " + ", ".join(metric_cols)
    update_set = ", ".join(f"{c} = EXCLUDED.{c}" for c in metric_cols)

    sql = f"""
        INSERT INTO daily_metrics ({col_names})
        VALUES %s
        ON CONFLICT (ticker, date) DO UPDATE SET {update_set}
    """
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, rows, page_size=1000)
    conn.commit()

    logger.info("Upserted %d metric rows for %s", len(rows), target_date)
    return len(rows)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def calculate_daily(target_date: date) -> int:
    """Daily mode: load bars from DB, compute metrics, write back. Returns row count."""
    conn = get_connection()
    try:
        logger.info("Loading bars for metrics calculation up to %s", target_date)
        bars_df = load_bars_for_date(conn, target_date)
        if bars_df.empty:
            logger.info("No bars found for %s — skipping metrics.", target_date)
            return 0

        metrics_df = compute_metrics_for_universe(bars_df)
        count = upsert_daily_metrics(conn, metrics_df, target_date)
        return count
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute per-stock metrics")
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=date.today() - timedelta(days=1),
        help="Date to compute metrics for (YYYY-MM-DD). Defaults to yesterday.",
    )
    args = parser.parse_args()

    logger.info("Starting calculate for date: %s", args.date)
    count = calculate_daily(args.date)
    logger.info("Calculate complete. Rows: %d", count)


if __name__ == "__main__":
    main()
