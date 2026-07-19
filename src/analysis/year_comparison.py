"""Year-over-year rookie class comparison — MVP tracker.

Builds a comparison table across draft classes (2015-2025) showing:
  - Class size, average rookie PPG / RPG / APG / PER
  - Top rookie scorer per year
  - Biggest breakout / bust (for years with sophomore data)
  - Rookie-of-the-Year candidate stats

Usage:
    python -m src.analysis.year_comparison
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_candidate = Path(__file__).resolve()
while not (_candidate / "src").is_dir() and _candidate != _candidate.parent:
    _candidate = _candidate.parent
sys.path.insert(0, str(_candidate))

from src.config import RAW_DIR, PROCESSED_DIR

logger = logging.getLogger(__name__)


def _load_rookie() -> pd.DataFrame:
    path = RAW_DIR / "rookie_stats.parquet"
    df = pd.read_parquet(path)
    rename = {
        "PLAYER_ID": "player_id", "PLAYER": "player", "TEAM": "team",
        "GP": "gp", "MIN": "mpg", "PTS": "ppg", "REB": "rpg", "AST": "apg",
        "STL": "spg", "BLK": "bpg", "TOV": "tpg",
        "FG_PCT": "fg_pct", "FG3_PCT": "tp_pct", "FT_PCT": "ft_pct", "EFF": "eff",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    if "season" in df.columns:
        df["season"] = df["season"].astype(int)
    return df


def _load_sophomore() -> pd.DataFrame:
    path = RAW_DIR / "sophomore_stats.parquet"
    df = pd.read_parquet(path)
    rename = {
        "PLAYER_ID": "player_id", "PLAYER_NAME": "player",
        "GP": "soph_gp", "MIN": "soph_min_total", "PTS": "soph_pts_total",
        "REB": "soph_reb_total", "AST": "soph_ast_total", "STL": "soph_stl_total",
        "BLK": "soph_blk_total", "TOV": "soph_tov_total",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    if "soph_season" in df.columns:
        df["soph_season"] = df["soph_season"].astype(int)

    gp = df["soph_gp"].replace(0, np.nan)
    df["soph_mpg"] = df["soph_min_total"] / gp
    df["soph_ppg"] = df["soph_pts_total"] / gp
    df["soph_rpg"] = df["soph_reb_total"] / gp
    df["soph_apg"] = df["soph_ast_total"] / gp
    df["soph_spg"] = df["soph_stl_total"] / gp
    df["soph_bpg"] = df["soph_blk_total"] / gp

    return df


def build_class_summary() -> pd.DataFrame:
    """One row per draft class with aggregated rookie stats."""
    rookie = _load_rookie()
    cols = ["player_id", "player", "team", "season", "gp", "mpg", "ppg", "rpg", "apg",
            "spg", "bpg", "tpg", "fg_pct", "tp_pct", "ft_pct", "eff"]
    rookie = rookie[[c for c in cols if c in rookie.columns]].copy()

    summary_rows = []
    for season, grp in rookie.groupby("season"):
        top_scorer = grp.loc[grp["ppg"].idxmax()] if len(grp) > 0 else None
        row = {
            "season": int(season),
            "class_size": len(grp),
            "avg_ppg": round(grp["ppg"].mean(), 1),
            "avg_rpg": round(grp["rpg"].mean(), 1),
            "avg_apg": round(grp["apg"].mean(), 1),
            "avg_eff": round(grp["eff"].mean(), 1),
            "avg_mpg": round(grp["mpg"].mean(), 1),
            "top_scorer": top_scorer["player"] if top_scorer is not None else "",
            "top_ppg": round(top_scorer["ppg"], 1) if top_scorer is not None else 0,
            "top_team": top_scorer["team"] if top_scorer is not None else "",
        }
        summary_rows.append(row)

    return pd.DataFrame(summary_rows)


def build_delta_comparison() -> pd.DataFrame:
    """Year-over-year breakout/bust comparison (years with sophomore data only)."""
    rookie = _load_rookie()
    soph = _load_sophomore()

    rookie_cols = ["player_id", "player", "team", "season", "mpg", "ppg", "rpg", "apg"]
    rookie = rookie[[c for c in rookie_cols if c in rookie.columns]].copy()
    rookie = rookie.rename(columns={"season": "rookie_season"})

    soph_cols = ["player_id", "soph_season", "soph_mpg", "soph_ppg", "soph_rpg", "soph_apg"]
    soph = soph[[c for c in soph_cols if c in soph.columns]].copy()

    merged = rookie.merge(soph, on="player_id", how="inner")
    merged = merged[merged["soph_season"] == merged["rookie_season"] + 1].copy()
    if merged.empty:
        return pd.DataFrame()

    merged["delta_ppg"] = merged["soph_ppg"] - merged["ppg"]
    merged["delta_mpg"] = merged["soph_mpg"] - merged["mpg"]
    merged["delta_rpg"] = merged["soph_rpg"] - merged["rpg"]
    merged["delta_apg"] = merged["soph_apg"] - merged["apg"]

    rows = []
    for season, grp in merged.groupby("rookie_season"):
        best_improver = grp.loc[grp["delta_ppg"].idxmax()] if len(grp) > 0 else None
        worst_decline = grp.loc[grp["delta_ppg"].idxmin()] if len(grp) > 0 else None
        top_rookie = grp.loc[grp["ppg"].idxmax()] if len(grp) > 0 else None

        breakout_count = int((grp["delta_ppg"] >= 3.0).sum())
        bust_count = int((grp["delta_ppg"] <= -3.0).sum())

        row = {
            "season": int(season),
            "matched": len(grp),
            "avg_delta_ppg": round(grp["delta_ppg"].mean(), 1),
            "avg_delta_mpg": round(grp["delta_mpg"].mean(), 1),
            "top_rookie_ppg": round(top_rookie["ppg"], 1) if top_rookie is not None else 0,
            "top_rookie_name": top_rookie["player"] if top_rookie is not None else "",
            "best_improver_name": best_improver["player"] if best_improver is not None else "",
            "best_improver_delta": round(best_improver["delta_ppg"], 1) if best_improver is not None else 0,
            "worst_decline_name": worst_decline["player"] if worst_decline is not None else "",
            "worst_decline_delta": round(worst_decline["delta_ppg"], 1) if worst_decline is not None else 0,
            "breakout_3ppg": breakout_count,
            "bust_neg3ppg": bust_count,
        }
        rows.append(row)

    return pd.DataFrame(rows)


def build_top_prospects_2025() -> pd.DataFrame:
    """Load 2025 rookie stats (inference frame) — awaiting sophomore data."""
    path = PROCESSED_DIR / "inference_2025_rookies.parquet"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    keep = ["RANK", "player_name", "TEAM", "rookie_gp", "rookie_mpg", "rookie_ppg",
            "rookie_rpg", "rookie_apg", "rookie_spg", "rookie_bpg", "rookie_per",
            "rookie_fg_pct", "rookie_3p_pct"]
    existing = [c for c in keep if c in df.columns]
    df = df[existing].copy()
    df.columns = [c.replace("rookie_", "").replace("RANK", "rank") for c in df.columns]
    df["status"] = "awaiting_yr2"
    return df.head(20)


def print_comparison():
    """Print formatted year-over-year comparison tables."""
    print("=" * 90)
    print(" NBA ROOKIE CLASS COMPARISON — YEAR-OVER-YEAR MVP TRACKER")
    print("=" * 90)

    # --- Part 1: Rookie class averages ---
    summary = build_class_summary()
    print("\n── ROOKIE CLASS AVERAGES (all classes) ──\n")
    print(summary.to_string(index=False))

    # --- Part 2: Delta comparison (sophomore data available) ---
    deltas = build_delta_comparison()
    if not deltas.empty:
        print("\n\n── YEAR-OVER-YEAR SOPHOMORE JUMP (classes with yr2 data) ──\n")
        print(deltas.to_string(index=False))

    # --- Part 3: 2025 class (awaiting results) ---
    prospects = build_top_prospects_2025()
    if not prospects.empty:
        print("\n\n── 2025 ROOKIE CLASS — TOP 20 (awaiting sophomore results) ──\n")
        print(prospects.to_string(index=False))

    print("\n" + "=" * 90)
    print(" NOTE: 2025 class marked 'awaiting_yr2' — update after sophomore season.")
    print("=" * 90)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    print_comparison()
