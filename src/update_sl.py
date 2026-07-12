"""Automated Summer League updater.

Usage (manual):
    python -m src.update_sl

The same script can be scheduled via cron / GitHub Actions /
Task Scheduler to run after every SL game day.

Sources (in order of preference):
  1. nba_api: ``leaguegamelog`` + ``BoxScoreTraditionalV2`` for the SL date window
  2. Playwright scraper: ``src.scrape.summer_league_playwright``
  3. Manual CSV: ``data/raw/summer_league.csv``
"""
from __future__ import annotations

import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

from src.config import (
    ROOT, RAW_DIR, PROCESSED_DIR,
    SL_2026_SCHEDULE, SL_2026_DAILY,
    CURRENT_YEAR,
)
from src.summer_league_scraper import scrape_summer_league

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Schedule helpers
# ──────────────────────────────────────────────
def get_sl_event_today(today: Optional[date] = None) -> Optional[dict]:
    """Return the active SL event for *today*, or None."""
    today = today or date.today()
    for ev in SL_2026_SCHEDULE:
        start = date.fromisoformat(ev["start"])
        end = date.fromisoformat(ev["end"])
        if start <= today <= end:
            return ev
    return None


def days_remaining_in_sl(today: Optional[date] = None) -> int:
    """Days left in the 2026 SL window (negative if finished)."""
    today = today or date.today()
    lv_end = date.fromisoformat("2026-07-19")
    return (lv_end - today).days


# ──────────────────────────────────────────────
# Data layer
# ──────────────────────────────────────────────
def append_today_box_scores(today: Optional[date] = None) -> pd.DataFrame:
    """Pull box scores for *today*'s SL games and append to the master parquet."""
    today = today or date.today()
    event = get_sl_event_today(today)
    if event is None:
        logger.info(f"No SL event active on {today} — skipping box-score pull")
        return pd.DataFrame()

    df = scrape_summer_league(today.year)
    if df.empty:
        logger.info("No new SL data scraped today")
        return pd.DataFrame()

    dedup_col = "PLAYER_ID" if "PLAYER_ID" in df.columns else "game_id"
    parquet_path = RAW_DIR / f"summer_league_{today.year}.parquet"
    if parquet_path.exists():
        existing = pd.read_parquet(parquet_path)
        combined = pd.concat([existing, df], ignore_index=True).drop_duplicates(dedup_col)
    else:
        combined = df

    combined.to_parquet(parquet_path, index=False)
    logger.info(f"Updated {parquet_path} — {len(combined)} rows")
    return combined


def refresh_sl_parquet() -> str:
    """Full refresh of the default ``summer_league.parquet``."""
    df = scrape_summer_league(datetime.now().year)
    out = RAW_DIR / "summer_league.parquet"
    if df.empty:
        logger.warning("No Summer League data — removing stale parquet")
        if out.exists():
            out.unlink()
        return str(out)
    df.to_parquet(out, index=False)
    logger.info(f"Refreshed {out} — {len(df)} rows")
    return str(out)


# ──────────────────────────────────────────────
# Convenience: rebuild pipeline outputs
# ──────────────────────────────────────────────
def rebuild_inference() -> str:
    """Re-run just the inference step so the dashboard picks up fresh SL data."""
    from src.pipeline import (
        pull_rookie_stats,
        build_inference_2025_rookies,
    )

    rookie = pull_rookie_stats()
    sl_path = RAW_DIR / "summer_league.parquet"
    sl_available = sl_path.exists() and sl_path.stat().st_size > 0
    infer = build_inference_2025_rookies(rookie, sl_available)
    out = PROCESSED_DIR / "inference_2025_rookies.parquet"
    infer.to_parquet(out, index=False)
    logger.info(f"Rebuilt inference: {out} — {len(infer)} rows")
    return str(out)


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────
if __name__ == "__main__":
    today = date.today()
    event = get_sl_event_today(today)

    print(f"\nSummer League Updater - {today}")
    print(f"Days remaining in LV SL: {days_remaining_in_sl()}")
    if event:
        print(f"Active event: {event['event']} ({event['start']} - {event['end']})")
    else:
        print("No SL event active today.")

    # Full refresh
    path = refresh_sl_parquet()

    # Rebuild inference so Streamlit picks it up
    rebuild_inference()

    print(f"\nDone. Next run: schedule this script after each game day.")
    print("Windows (Task Scheduler) example:")
    print(f'  schtasks /create /tn "RookSLUpdate" /tr "python -m src.update_sl" /sc daily /st 23:00')
