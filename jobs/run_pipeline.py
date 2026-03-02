"""Daily pipeline orchestrator: ingest → calculate → aggregate → log → purge.

Triggered by Render Cron Job at 4:30 PM ET on trading days.
Logs results to the job_runs table. Handles market holidays gracefully.

Usage:
    python -m jobs.run_pipeline
    python -m jobs.run_pipeline --date 2025-01-15
"""

import argparse
import logging
import os
import sys
import time
from datetime import date, timedelta

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.db import get_connection
from jobs.ingest import ingest
from jobs.calculate import calculate_daily
from jobs.aggregate import aggregate_daily

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

ROLLING_WINDOW_DAYS = 252


# ---------------------------------------------------------------------------
# Job run logging
# ---------------------------------------------------------------------------

def log_job_run(
    conn,
    run_date: date,
    status: str,
    rows_ingested: int = 0,
    duration_seconds: float = 0.0,
    error_message: str | None = None,
    mode: str = "daily",
) -> None:
    """Insert a record into job_runs."""
    sql = """
        INSERT INTO job_runs (run_date, mode, status, rows_ingested, duration_seconds, error_message)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    with conn.cursor() as cur:
        cur.execute(sql, (run_date, mode, status, rows_ingested, round(duration_seconds, 2), error_message))
    conn.commit()
    logger.info("Logged job_run: date=%s status=%s rows=%d duration=%.1fs", run_date, status, rows_ingested, duration_seconds)


# ---------------------------------------------------------------------------
# Rolling window purge
# ---------------------------------------------------------------------------

def purge_rolling_window(conn, cutoff_date: date) -> None:
    """Delete daily_bars and daily_metrics rows older than cutoff_date."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM daily_bars WHERE date < %s", (cutoff_date,))
        bar_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM daily_metrics WHERE date < %s", (cutoff_date,))
        metric_count = cur.fetchone()[0]

    logger.warning(
        "Purging rolling window: %d daily_bars, %d daily_metrics older than %s",
        bar_count, metric_count, cutoff_date,
    )
    with conn.cursor() as cur:
        cur.execute("DELETE FROM daily_bars WHERE date < %s", (cutoff_date,))
        cur.execute("DELETE FROM daily_metrics WHERE date < %s", (cutoff_date,))
    conn.commit()
    logger.info("Rolling window purge complete.")


def _compute_cutoff(target_date: date) -> date:
    """Compute cutoff date approximately 252 trading days before target_date."""
    import pandas as pd
    # Use pandas business day offset as a proxy for trading days
    # 252 trading days ≈ 365 calendar days; add buffer
    cutoff = (pd.Timestamp(target_date) - pd.offsets.BDay(260)).date()
    return cutoff


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline(target_date: date) -> None:
    """Execute the full daily pipeline for target_date."""
    start_time = time.time()
    conn = get_connection()
    rows_ingested = 0

    try:
        logger.info("=== Pipeline start: %s ===", target_date)

        # Step 1: Ingest
        logger.info("Step 1: Ingest")
        rows_ingested = ingest(target_date)

        if rows_ingested == 0:
            # Market holiday or weekend — Polygon returned empty
            logger.info("No data for %s — market holiday or weekend. Logging as skipped.", target_date)
            duration = time.time() - start_time
            log_job_run(conn, target_date, "skipped", 0, duration)
            return

        # Step 2: Calculate per-stock metrics
        logger.info("Step 2: Calculate metrics")
        calculate_daily(target_date)

        # Step 3: Aggregate market summary
        logger.info("Step 3: Aggregate market summary")
        aggregate_daily(target_date)

        # Step 4: Purge rolling window
        logger.info("Step 4: Purge old rows")
        cutoff = _compute_cutoff(target_date)
        purge_rolling_window(conn, cutoff)

        duration = time.time() - start_time
        log_job_run(conn, target_date, "success", rows_ingested, duration)
        logger.info("=== Pipeline complete: %s — %.1fs ===", target_date, duration)

    except Exception as e:
        duration = time.time() - start_time
        error_msg = str(e)
        logger.error("Pipeline failed for %s: %s", target_date, error_msg, exc_info=True)
        try:
            log_job_run(conn, target_date, "failed", rows_ingested, duration, error_msg)
        except Exception as log_err:
            logger.error("Failed to log job_run: %s", log_err)
        raise
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full daily market data pipeline")
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=date.today() - timedelta(days=1),
        help="Date to process (YYYY-MM-DD). Defaults to yesterday.",
    )
    args = parser.parse_args()
    run_pipeline(args.date)


if __name__ == "__main__":
    main()
