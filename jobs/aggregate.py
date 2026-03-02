"""Market summary aggregation: compute all breadth/momentum metrics per trading day.

Translates the full RealTest market monitor metric set into Python/pandas.
McClellan EMA state is carried chronologically — process dates in order.

Two modes:
    daily   — aggregate today's metrics from daily_metrics table
    backfill — called from backfill.py with a pre-loaded metrics DataFrame

Usage (daily mode):
    python -m jobs.aggregate --date 2025-01-15
    python -m jobs.aggregate  # defaults to yesterday
"""

import argparse
import logging
import os
import sys
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd
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

UNIVERSES = ["all", "nyse", "nasdaq"]

# EMA span for McClellan Oscillator (19-day and 39-day)
MCCLELLAN_SPAN_FAST = 19
MCCLELLAN_SPAN_SLOW = 39


# ---------------------------------------------------------------------------
# McClellan EMA helpers
# ---------------------------------------------------------------------------

def _ema_step(value: float, prev_ema: float | None, span: int) -> float:
    """Single EMA step. Returns prev_ema for first observation if None."""
    alpha = 2.0 / (span + 1)
    if prev_ema is None:
        return value
    return alpha * value + (1 - alpha) * prev_ema


def get_last_mcclellan_state(conn: Any) -> dict[str, dict[str, float | None]]:
    """Read the most recent adv_ema19 and adv_ema39 per universe from market_summary."""
    state: dict[str, dict[str, float | None]] = {}
    for universe in UNIVERSES:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT adv_ema19, adv_ema39
                FROM market_summary
                WHERE universe = %s
                ORDER BY date DESC
                LIMIT 1
                """,
                (universe,),
            )
            row = cur.fetchone()
        if row:
            state[universe] = {"ema19": row[0], "ema39": row[1]}
        else:
            state[universe] = {"ema19": None, "ema39": None}
    return state


# ---------------------------------------------------------------------------
# Index data helpers
# ---------------------------------------------------------------------------

def load_index_history(conn: Any, days: int = 210) -> pd.DataFrame:
    """Load recent index bars for computing MAs and RSI overlays."""
    sql = """
        SELECT ticker, date, open, high, low, close
        FROM index_bars
        ORDER BY ticker, date
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=["ticker", "date", "open", "high", "low", "close"])
    return df


def _compute_index_overlays(index_df: pd.DataFrame, target_date: date) -> dict[str, Any]:
    """Compute SPX/NDX/VIX values and their MAs for target_date."""
    result: dict[str, Any] = {}
    if index_df.empty:
        return result

    index_df = index_df.copy()
    index_df["date"] = pd.to_datetime(index_df["date"]).dt.date

    for ticker, col_prefix in [("I:SPX", "spx"), ("I:NDX", "ndx"), ("I:VIX", "vix")]:
        tdf = index_df[index_df["ticker"] == ticker].sort_values("date").reset_index(drop=True)
        if tdf.empty:
            continue

        c = tdf["close"]
        tdf[f"{col_prefix}"] = c

        if col_prefix != "vix":
            for period in [5, 10, 20, 50, 200]:
                tdf[f"{col_prefix}{period:03d}ma"] = c.rolling(period).mean()

            # RSI(14)
            import pandas_ta as ta
            tdf[f"{col_prefix}rsi"] = ta.rsi(c, length=14)

            # Rate of change: (close - close[N]) / close[N]
            for period in [5, 10, 20]:
                tdf[f"roc{col_prefix}{period:03d}"] = (c - c.shift(period)) / c.shift(period)

        # Extract today's row
        today_row = tdf[tdf["date"] == target_date]
        if today_row.empty:
            continue

        for col in tdf.columns:
            if col not in ("ticker", "date"):
                val = today_row.iloc[0][col]
                result[col] = None if pd.isna(val) else float(val)

    return result


# ---------------------------------------------------------------------------
# Per-universe aggregation
# ---------------------------------------------------------------------------

def _filter_universe(metrics_df: pd.DataFrame, universe: str) -> pd.DataFrame:
    """Filter metrics_df to the given universe (all / nyse / nasdaq)."""
    if universe == "all":
        return metrics_df
    if "exchange" in metrics_df.columns:
        exchange_map = {"nyse": "NYSE", "nasdaq": "NASDAQ"}
        return metrics_df[metrics_df["exchange"] == exchange_map.get(universe, "")]
    return metrics_df


def _aggregate_one_day(
    day_df: pd.DataFrame,
    target_date: date,
    universe: str,
    bars_df: pd.DataFrame | None,
) -> dict[str, Any]:
    """Compute all market_summary metrics for one date and universe.

    Args:
        day_df:      daily_metrics rows for target_date (filtered to universe)
        target_date: the date being aggregated
        universe:    'all', 'nyse', or 'nasdaq'
        bars_df:     daily_bars for target_date (needed for volume and price data)
    """
    row: dict[str, Any] = {"date": target_date, "universe": universe}

    if day_df.empty:
        return row

    # Merge bars for volume and price data
    if bars_df is not None and not bars_df.empty:
        bars_today = bars_df[bars_df["date"] == target_date][["ticker", "open", "close", "volume"]].copy()
        df = day_df.merge(bars_today, on="ticker", how="left", suffixes=("", "_bar"))
        # Use bar close if metrics close not separately stored
        if "close" not in df.columns and "close_bar" in df.columns:
            df["close"] = df["close_bar"]
        if "open" not in df.columns and "open_bar" in df.columns:
            df["open"] = df["open_bar"]
        if "volume" not in df.columns and "volume_bar" in df.columns:
            df["volume"] = df["volume_bar"]
    else:
        df = day_df.copy()

    # Liquidity-filtered universe
    liq = df[df["liqfilter"] == True] if "liqfilter" in df.columns else df
    liq_price = liq[liq["pricefilter"] == True] if "pricefilter" in liq.columns else liq

    stocks = len(df)
    row["stocks"] = stocks

    # Advance / decline (requires close and prior close — computed from bar columns)
    if "close" in df.columns:
        c = df["close"].astype(float)
        o = df["open"].astype(float) if "open" in df.columns else None
        v = df["volume"].astype(float) if "volume" in df.columns else None
        atr21 = df["atr21"].astype(float) if "atr21" in df.columns else None

        # We use ibs and close > sma20 as proxy for advancing (daily bar needed)
        # For the full advance/decline we need prior close — use liqfilter df
        # Note: "close > prior_close" requires prior_close which isn't in daily_metrics.
        # In daily mode, we merge from daily_bars where we have today and yesterday.
        # In backfill mode bars_df contains multi-day history we can derive prior_close from.
        # This is handled via the bars_df passed in from the orchestrator.
        adv_mask = df.get("is_52wk_high", pd.Series(dtype=bool)) | (df["rvol"] > 0)  # placeholder
        # The real adv/dec requires day_prior_close — set in orchestrator via bars_df
        # If prior_close column provided:
        if "prior_close" in df.columns:
            adv_mask = df["close"] > df["prior_close"]
            dec_mask = df["close"] < df["prior_close"]
            row["adv"] = int(adv_mask.sum())
            row["dec"] = int(dec_mask.sum())
            if v is not None:
                row["voladv"] = int(v[adv_mask].sum())
                row["voldec"] = int(v[dec_mask].sum())
                row["volrat"] = row["voladv"] / max(row["voldec"], 1)

        # MA breadth
        for col, key in [("sma50", "a050ma"), ("sma200", "a200ma"), ("sma40", "t2108")]:
            if col in df.columns:
                row[key] = int((df["close"] > df[col]).sum())
                if key == "a050ma":
                    row["b050ma"] = int((df["close"] <= df[col]).sum())
                if key == "a200ma":
                    row["b200ma"] = int((df["close"] <= df[col]).sum())

        # New highs / lows
        if "is_52wk_high" in df.columns:
            row["newhi"] = int(df["is_52wk_high"].sum())
        if "is_52wk_low" in df.columns:
            row["newlo"] = int(df["is_52wk_low"].sum())

        # RSI breadth
        if "rsi14" in df.columns:
            row["rsios"] = int((df["rsi14"] < 30).sum())
            row["rsiob"] = int((df["rsi14"] > 70).sum())

        # Percentage metrics
        if stocks > 0:
            row["pcta200ma"] = round(row.get("a200ma", 0) / stocks, 4)
            row["pctb200ma"] = round(row.get("b200ma", 0) / stocks, 4)
            row["pctnewhi"]  = round(row.get("newhi", 0) / stocks, 4)
            row["pctnewlo"]  = round(row.get("newlo", 0) / stocks, 4)
            row["ratrsios"]  = round(row.get("rsios", 0) / stocks, 4)
            row["ratrsiob"]  = round(row.get("rsiob", 0) / stocks, 4)

        # Extreme candles: close > open, range > atr21, body > 50% of range, advancing/declining
        if o is not None and atr21 is not None and "prior_close" in df.columns:
            bar_range  = (df["high"] - df["low"]).astype(float) if "high" in df.columns else None
            if bar_range is not None:
                body = (df["close"] - o).abs()
                big_range = bar_range > atr21
                big_body  = body > bar_range * 0.5
                row["extremeup"] = int(
                    (df["close"] > o) & big_range & big_body & (df["close"] > df["prior_close"])
                ).sum() if hasattr(
                    ((df["close"] > o) & big_range & big_body & (df["close"] > df["prior_close"])), "sum"
                ) else 0
                row["extremedn"] = int(
                    ((df["close"] < o) & big_range & big_body & (df["close"] < df["prior_close"])).sum()
                )

        # Momentum movers (require prior_close and volume)
        if "prior_close" in df.columns and v is not None:
            pc = df["prior_close"].astype(float)
            pct_chg = (df["close"] - pc) / pc.replace(0, np.nan)

            row["up4"] = int(((pct_chg >= 0.04) & (v >= 100_000)).sum())
            row["dn4"] = int(((pct_chg <= -0.04) & (v >= 100_000)).sum())

        if "hhv063" in df.columns and "llv252" in df.columns:
            row["up25q"] = int((liq["close"] >= 1.25 * liq["llv063"]).sum()) if len(liq) > 0 else 0
            row["dn25q"] = int((liq["close"] <= 0.75 * liq["hhv063"]).sum()) if len(liq) > 0 else 0

        if "sma20" in df.columns:
            # up25m: close >= 1.25 * close[20] (approximated by close vs sma20 trend)
            # Using prior-20-day close stored as sma20 proxy is not exact;
            # the orchestrator should pass prior_close_20 for accuracy.
            # Fall back to available columns:
            if "prior_close_20" in df.columns:
                row["up25m"] = int((liq_price["close"] >= 1.25 * liq_price["prior_close_20"]).sum())
                row["dn25m"] = int((liq_price["close"] <= 0.75 * liq_price["prior_close_20"]).sum())
                row["up50m"] = int((liq_price["close"] >= 1.50 * liq_price["prior_close_20"]).sum())
                row["dn50m"] = int((liq_price["close"] <= 0.50 * liq_price["prior_close_20"]).sum())

        if "hhv034" in df.columns or "llv034" in df.columns:
            if "llv034" in liq.columns:
                row["up1334"] = int((liq["close"] >= 1.13 * liq["llv034"]).sum())
            if "hhv034" in liq.columns:
                row["dn1334"] = int((liq["close"] <= 0.87 * liq["hhv034"]).sum())

        # Breakout quality (bu/bd patterns)
        for days_n, suffix in [(21, "021"), (63, "063"), (252, "252")]:
            hhv_col   = f"hhv{suffix}"
            llv_col   = f"llv{suffix}"
            hhv7_col  = "hhv007"
            llv7_col  = "llv007"
            hhv21_col = "hhv021"
            llv21_col = "llv021"

            if not all(c in df.columns for c in [hhv_col, llv_col, hhv7_col, llv7_col]):
                continue

            if o is not None and "prior_close" in df.columns:
                pc = df["prior_close"].astype(float)

                # bu_ok: close > open, close > hhv_N[1], hhv_7[1] < hhv_N[1]
                # [1] = prior day value — we use shift which isn't available here.
                # During daily mode, these are computed from the merged prior-day metrics.
                # During backfill, prior-day values must be provided in bars_df.
                # Columns: hhv021_prev, hhv063_prev, hhv252_prev etc.
                prev_hhv = f"{hhv_col}_prev"
                prev_hhv7 = f"{hhv7_col}_prev"
                prev_llv = f"{llv_col}_prev"
                prev_llv7 = f"{llv7_col}_prev"

                if prev_hhv in df.columns and prev_hhv7 in df.columns:
                    bu_ok  = (df["close"] > o) & (df["close"] > df[prev_hhv]) & (df[prev_hhv7] < df[prev_hhv])
                    bu_nok = (df["close"] < o) & (df["high"]  > df[prev_hhv]) & (df[prev_hhv7] < df[prev_hhv])
                    row[f"bu{suffix}ok"]  = int(bu_ok.sum())
                    row[f"bu{suffix}nok"] = int(bu_nok.sum())
                    row[f"ratbu{suffix}"] = round(row[f"bu{suffix}ok"] / max(row[f"bu{suffix}nok"], 1), 4)

                if prev_llv in df.columns and prev_llv7 in df.columns:
                    bd_ok  = (df["close"] < o) & (df["close"] < df[prev_llv]) & (df[prev_llv7] > df[prev_llv])
                    bd_nok = (df["close"] > o) & (df["low"]   < df[prev_llv]) & (df[prev_llv7] > df[prev_llv])
                    row[f"bd{suffix}ok"]  = int(bd_ok.sum())
                    row[f"bd{suffix}nok"] = int(bd_nok.sum())
                    row[f"ratbd{suffix}"] = round(row[f"bd{suffix}ok"] / max(row[f"bd{suffix}nok"], 1), 4)

    return row


# ---------------------------------------------------------------------------
# McClellan update
# ---------------------------------------------------------------------------

def _update_mcclellan(
    row: dict[str, Any],
    universe: str,
    mcclellan_state: dict,
) -> dict[str, Any]:
    """Compute McClellan EMA step and update state in-place."""
    adv = row.get("adv", 0) or 0
    dec = row.get("dec", 0) or 0
    total = adv + dec
    if total == 0:
        return mcclellan_state

    normalized_ad = ((adv - dec) / total) * 1000.0
    state = mcclellan_state.get(universe, {"ema19": None, "ema39": None})

    ema19 = _ema_step(normalized_ad, state["ema19"], MCCLELLAN_SPAN_FAST)
    ema39 = _ema_step(normalized_ad, state["ema39"], MCCLELLAN_SPAN_SLOW)

    row["adv_ema19"] = round(ema19, 4)
    row["adv_ema39"] = round(ema39, 4)
    row["mcclellan"] = round(ema19 - ema39, 4)

    mcclellan_state[universe] = {"ema19": ema19, "ema39": ema39}
    return mcclellan_state


# ---------------------------------------------------------------------------
# Rolling A/D ratio helpers (require multi-day context)
# ---------------------------------------------------------------------------

def _fill_rolling_ratios(summary_rows: list[dict], universe: str) -> list[dict]:
    """Compute rat5, rat10, volrat5, volrat10 from accumulated summary rows."""
    df = pd.DataFrame(summary_rows)
    df = df[df["universe"] == universe].sort_values("date").reset_index(drop=True)

    if "adv" in df.columns and "dec" in df.columns:
        df["rat"]    = df["adv"] / df["dec"].replace(0, np.nan)
        df["rat5"]   = df["adv"].rolling(5).sum() / df["dec"].rolling(5).sum()
        df["rat10"]  = df["adv"].rolling(10).sum() / df["dec"].rolling(10).sum()

    if "voladv" in df.columns and "voldec" in df.columns:
        df["volrat"]  = df["voladv"] / df["voldec"].replace(0, np.nan)
        df["volrat5"] = df["voladv"].rolling(5).sum() / df["voldec"].rolling(5).sum()
        df["volrat10"]= df["voladv"].rolling(10).sum() / df["voldec"].rolling(10).sum()

    if "newhi" in df.columns:
        df["newhi010ma"] = df["newhi"].rolling(10).mean()
        df["newlo010ma"] = df["newlo"].rolling(10).mean()

    return df.to_dict("records")


# ---------------------------------------------------------------------------
# DB I/O
# ---------------------------------------------------------------------------

def load_metrics_for_date(conn: Any, target_date: date) -> pd.DataFrame:
    """Load daily_metrics for target_date joined with stocks for exchange info."""
    sql = """
        SELECT
            dm.ticker, dm.date,
            dm.sma20, dm.sma40, dm.sma50, dm.sma200,
            dm.ema_dollar_vol_20, dm.liqfilter, dm.pricefilter,
            dm.rsi14, dm.atr14, dm.atr21, dm.ibs, dm.rvol,
            dm.hhv007, dm.hhv021, dm.hhv063, dm.hhv252,
            dm.llv007, dm.llv021, dm.llv063, dm.llv252,
            dm.is_52wk_high, dm.is_52wk_low,
            s.exchange
        FROM daily_metrics dm
        LEFT JOIN stocks s ON s.ticker = dm.ticker
        WHERE dm.date = %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (target_date,))
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
    return pd.DataFrame(rows, columns=cols)


def load_bars_window(conn: Any, target_date: date, lookback: int = 2) -> pd.DataFrame:
    """Load last `lookback` days of daily_bars to derive prior_close, volume etc."""
    cutoff = target_date - timedelta(days=lookback + 5)
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


def _enrich_with_prior_close(metrics_df: pd.DataFrame, bars_df: pd.DataFrame, target_date: date) -> pd.DataFrame:
    """Add prior_close and prior_close_20 columns to metrics_df from bars_df."""
    bars_df = bars_df.copy()
    bars_df["date"] = pd.to_datetime(bars_df["date"]).dt.date

    today_bars    = bars_df[bars_df["date"] == target_date][["ticker", "open", "close", "high", "low", "volume"]]
    prior_bars    = bars_df[bars_df["date"] < target_date].sort_values("date")

    # Most recent prior close per ticker
    prior_close   = prior_bars.groupby("ticker")["close"].last().reset_index().rename(columns={"close": "prior_close"})
    # 20-day prior close: take the close from 20 trading days ago
    prior_20 = prior_bars.groupby("ticker").nth(-20)[["close"]].reset_index().rename(columns={"close": "prior_close_20"})

    df = metrics_df.copy()
    df = df.merge(today_bars[["ticker", "open", "close", "high", "low", "volume"]], on="ticker", how="left")
    df = df.merge(prior_close, on="ticker", how="left")
    df = df.merge(prior_20,    on="ticker", how="left")

    return df


def upsert_market_summary_rows(conn: Any, rows: list[dict]) -> None:
    """Upsert market_summary rows."""
    if not rows:
        return

    # Gather all column names across rows
    all_cols = set()
    for r in rows:
        all_cols.update(r.keys())

    fixed_cols = ["date", "universe"]
    metric_cols = sorted(all_cols - set(fixed_cols))
    col_names = fixed_cols + metric_cols

    def _val(r: dict, col: str) -> Any:
        v = r.get(col)
        if v is None:
            return None
        if isinstance(v, float) and np.isnan(v):
            return None
        return v

    sql_rows = [tuple(_val(r, c) for c in col_names) for r in rows]
    update_set = ", ".join(f"{c} = EXCLUDED.{c}" for c in metric_cols)

    sql = f"""
        INSERT INTO market_summary ({", ".join(col_names)})
        VALUES %s
        ON CONFLICT (date, universe) DO UPDATE SET {update_set}
    """
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, sql_rows, page_size=500)
    conn.commit()
    logger.info("Upserted %d market_summary rows", len(rows))


# ---------------------------------------------------------------------------
# Main aggregate function
# ---------------------------------------------------------------------------

def aggregate_market_summary(
    conn: Any,
    metrics_df: pd.DataFrame | None = None,
    index_conn: Any = None,
    mcclellan_state: dict | None = None,
    mode: str = "daily",
    target_date: date | None = None,
) -> dict:
    """Aggregate market_summary for one or more dates.

    Args:
        conn:             DB connection
        metrics_df:       Pre-loaded metrics DataFrame (backfill mode) or None (daily mode)
        index_conn:       Connection for index bars (usually same as conn)
        mcclellan_state:  Dict of {universe: {ema19, ema39}} — carried across calls
        mode:             'daily' or 'backfill'
        target_date:      Date to aggregate (daily mode only)

    Returns:
        Updated mcclellan_state dict.
    """
    if mcclellan_state is None:
        mcclellan_state = get_last_mcclellan_state(conn)

    if index_conn is None:
        index_conn = conn

    index_df = load_index_history(index_conn)

    if mode == "daily":
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        metrics_df = load_metrics_for_date(conn, target_date)
        if metrics_df.empty:
            logger.info("No metrics for %s — skipping aggregation.", target_date)
            return mcclellan_state

        bars_df = load_bars_window(conn, target_date, lookback=25)
        metrics_df = _enrich_with_prior_close(metrics_df, bars_df, target_date)

        all_rows = []
        for universe in UNIVERSES:
            univ_df = _filter_universe(metrics_df, universe)
            row = _aggregate_one_day(univ_df, target_date, universe, bars_df)
            index_overlays = _compute_index_overlays(index_df, target_date)
            row.update(index_overlays)
            mcclellan_state = _update_mcclellan(row, universe, mcclellan_state)
            all_rows.append(row)

        upsert_market_summary_rows(conn, all_rows)
        return mcclellan_state

    else:  # backfill mode — metrics_df contains multiple dates
        if metrics_df is None or metrics_df.empty:
            return mcclellan_state

        metrics_df = metrics_df.copy()
        metrics_df["date"] = pd.to_datetime(metrics_df["date"]).dt.date
        sorted_dates = sorted(metrics_df["date"].unique())

        accumulated_rows: list[dict] = []

        for d in sorted_dates:
            day_metrics = metrics_df[metrics_df["date"] == d].copy()
            # No bars_df available in backfill mode; prior_close derived from metrics_df history
            # Use prior dates in metrics_df to derive prior_close
            prior_metrics = metrics_df[metrics_df["date"] < d]

            if not prior_metrics.empty:
                # Most recent prior close per ticker
                prior_close = (
                    prior_metrics.sort_values("date")
                    .groupby("ticker")["close"].last()
                    .reset_index()
                    .rename(columns={"close": "prior_close"})
                    if "close" in prior_metrics.columns
                    else pd.DataFrame(columns=["ticker", "prior_close"])
                )
                day_metrics = day_metrics.merge(prior_close, on="ticker", how="left")

            for universe in UNIVERSES:
                univ_df = _filter_universe(day_metrics, universe)
                row = _aggregate_one_day(univ_df, d, universe, None)
                index_overlays = _compute_index_overlays(index_df, d)
                row.update(index_overlays)
                mcclellan_state = _update_mcclellan(row, universe, mcclellan_state)
                accumulated_rows.append(row)

        # Fill rolling A/D ratios
        filled_rows: list[dict] = []
        for universe in UNIVERSES:
            univ_rows = _fill_rolling_ratios(accumulated_rows, universe)
            filled_rows.extend(univ_rows)

        upsert_market_summary_rows(conn, filled_rows)
        return mcclellan_state


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def aggregate_daily(target_date: date) -> None:
    """Run daily aggregation for a single date."""
    conn = get_connection()
    try:
        mcclellan_state = get_last_mcclellan_state(conn)
        aggregate_market_summary(
            conn=conn,
            mcclellan_state=mcclellan_state,
            mode="daily",
            target_date=target_date,
        )
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate market_summary for a date")
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=date.today() - timedelta(days=1),
        help="Date to aggregate (YYYY-MM-DD). Defaults to yesterday.",
    )
    args = parser.parse_args()

    logger.info("Starting aggregation for date: %s", args.date)
    aggregate_daily(args.date)
    logger.info("Aggregation complete.")


if __name__ == "__main__":
    main()
