"""Pipeline helpers used by update_sl.py.

pull_rookie_stats()  — read the raw rookie stats parquet
build_inference_2025_rookies() — produce the inference frame for the dashboard
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import RAW_DIR, PROCESSED_DIR

logger = logging.getLogger(__name__)

# ── Column mappings (raw NBA API → internal) ──
_ROOKIE_RENAME = {
    "PLAYER_ID": "player_id",
    "PLAYER": "player_name",
    "RANK": "RANK",
    "TEAM_ID": "team_id",
    "TEAM": "TEAM",
    "GP": "rookie_gp",
    "MIN": "rookie_mpg",
    "FGM": "FGM",
    "FGA": "FGA",
    "FG_PCT": "rookie_fg_pct",
    "FG3M": "FG3M",
    "FG3A": "FG3A",
    "FG3_PCT": "rookie_3p_pct",
    "FTM": "FTM",
    "FTA": "FTA",
    "FT_PCT": "rookie_ft_pct",
    "OREB": "OREB",
    "DREB": "DREB",
    "REB": "rookie_rpg",
    "AST": "rookie_apg",
    "STL": "rookie_spg",
    "BLK": "rookie_bpg",
    "TOV": "rookie_tpg",
    "PTS": "rookie_ppg",
    "EFF": "rookie_per",
}


def pull_rookie_stats() -> pd.DataFrame:
    """Read and normalise the raw rookie stats parquet."""
    path = RAW_DIR / "rookie_stats.parquet"
    if not path.exists():
        logger.warning(f"rookie_stats.parquet not found at {path}")
        return pd.DataFrame()

    df = pd.read_parquet(path)
    df = df.rename(columns={k: v for k, v in _ROOKIE_RENAME.items() if k in df.columns})

    if "season" in df.columns:
        df["rookie_season"] = df["season"].astype(int)

    # PER fallback: if rookie_per is missing, compute simple version
    if "rookie_per" not in df.columns or df["rookie_per"].isna().all():
        df["rookie_per"] = (
            df.get("rookie_ppg", 0)
            + df.get("rookie_rpg", 0)
            + df.get("rookie_apg", 0)
            + df.get("rookie_spg", 0)
            + df.get("rookie_bpg", 0)
            - df.get("rookie_tpg", 0)
        )

    logger.info(f"Loaded rookie stats: {len(df)} rows, {df['rookie_season'].nunique()} seasons")
    return df


def build_inference_2025_rookies(
    rookie: pd.DataFrame,
    sl_available: bool = False,
) -> pd.DataFrame:
    """Build the inference frame for 2025-rookie class.

    This mirrors the schema expected by the Streamlit dashboard so it can
    drop straight into ``data/processed/inference_2025_rookies.parquet``.
    """
    if rookie.empty:
        return pd.DataFrame()

    # Normalise season column (may be "season" or "rookie_season" depending on caller)
    if "rookie_season" not in rookie.columns and "season" in rookie.columns:
        rookie = rookie.copy()
        rookie["rookie_season"] = rookie["season"].astype(int)

    df = rookie[rookie["rookie_season"] == 2025].copy()
    if df.empty:
        logger.warning("No 2025 rookie rows found in rookie stats")
        return pd.DataFrame()

    # Ensure all required columns exist
    df["season"] = df["rookie_season"]
    df["dataset"] = "inference_2025"
    df["sl_available"] = sl_available

    keep = [
        "player_id", "RANK", "player_name", "TEAM_ID", "TEAM",
        "rookie_gp", "rookie_mpg",
        "FGM", "FGA", "rookie_fg_pct",
        "FG3M", "FG3A", "rookie_3p_pct",
        "FTM", "FTA", "rookie_ft_pct",
        "OREB", "DREB", "rookie_rpg",
        "rookie_apg", "rookie_spg", "rookie_bpg", "rookie_tpg",
        "rookie_ppg", "rookie_per",
        "season", "rookie_season", "dataset",
    ]
    existing = [c for c in keep if c in df.columns]
    df = df[existing].reset_index(drop=True)

    logger.info(f"Built inference frame: {len(df)} rookies (SL={'available' if sl_available else 'pending'})")
    return df
