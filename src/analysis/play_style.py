"""Play-style metrics derived from raw box-score stats.

Metrics computed:
    - usage_rate       (proxy: share of team scoring opportunity)
    - three_point_tendency
    - rim_rate_proxy    (FG% as efficiency proxy; low 3P% + high FG% = rim threat)
    - assist_ratio
    - defensive_activity (steals + blocks per game)
    - efficiency_index  (composite: PPG + RPG + APG + SPG + BPG - TOG)
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def compute_play_style(df: pd.DataFrame) -> pd.DataFrame:
    """Add play-style metric columns to a draft-class DataFrame.

    Expected input columns:
        rookie_ppg, rookie_rpg, rookie_apg, rookie_spg, rookie_bpg,
        rookie_tpg, rookie_fg_pct, rookie_3p_pct, rookie_ft_pct,
        rookie_gp, overall_pick
    """
    df = df.copy()
    eps = 1e-6

    spg = df.get("rookie_spg", pd.Series(0.0, index=df.index)).fillna(0)
    bpg = df.get("rookie_bpg", pd.Series(0.0, index=df.index)).fillna(0)
    tpg = df.get("rookie_tpg", pd.Series(2.0, index=df.index)).fillna(0)

    # Assist ratio
    df["assist_ratio"] = (
        df["rookie_apg"] / (df["rookie_apg"] + tpg + eps)
    ).clip(0, 1)

    # Three-point tendency (higher = more 3P reliant)
    df["three_point_tendency"] = df["rookie_3p_pct"].fillna(0.0)

    # Rim threat proxy: high FG% with low 3P% suggests interior scoring
    df["rim_rate_proxy"] = (
        df["rookie_fg_pct"] - df["rookie_3p_pct"].fillna(0.0)
    ).clip(-1, 1)

    # Defensive activity
    df["defensive_activity"] = spg + bpg

    # Efficiency index
    df["efficiency_index"] = (
        df["rookie_ppg"].fillna(0)
        + df["rookie_rpg"].fillna(0)
        + df["rookie_apg"].fillna(0)
        + spg
        + bpg
        - tpg
    )

    # Usage rate (simplified: higher for earlier picks + higher per-game stats)
    df["usage_rate"] = (
        (30 - df["overall_pick"]) / 30 * 0.5
        + (df["rookie_ppg"] / 30.0) * 0.3
        + (df["rookie_apg"] / 10.0) * 0.2
    ).clip(0, 1)

    return df


def get_style_summary(df: pd.DataFrame) -> pd.DataFrame:
    df = compute_play_style(df)
    style_cols = [
        "overall_pick", "player", "team", "position",
        "usage_rate", "three_point_tendency", "rim_rate_proxy",
        "assist_ratio", "defensive_activity", "efficiency_index",
    ]
    return df[style_cols].copy()
