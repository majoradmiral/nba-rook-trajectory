"""Over/under-performer detection for draft classes.

Algorithm:
    1. Build an expected-value curve from historical rookie stats vs draft position.
    2. Compare each prospect's pre-draft (or actual) stats against the curve.
    3. Compute a deviation score and flag over/under performers.

Flags:
    - "undervalued"  (over-performer): stats significantly better than expected for pick
    - "overvalued"   (under-performer): stats worse than expected for pick
    - "neutral"
"""

from __future__ import annotations

import logging
from typing import Literal

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Expected-value curves (ppg, rpg, apg per draft position) ─────────────────
# These are simplified linear fits from the repo's historical training data.
# They map overall_pick -> expected per-game production for a rookie.
_EXPECTED_PPG_SLOPE = -0.58   # each 10 picks later ≈ 0.58 fewer PPG
_EXPECTED_PPG_BASE  = 25.0    # pick #1 expected PPG
_EXPECTED_RPG_SLOPE = -0.25
_EXPECTED_RPG_BASE  = 7.0
_EXPECTED_APG_SLOPE = -0.15
_EXPECTED_APG_BASE  = 3.5


def _expected_ppg(pick: int) -> float:
    return max(5.0, _EXPECTED_PPG_BASE + (pick - 1) * _EXPECTED_PPG_SLOPE / 10)


def _expected_rpg(pick: int) -> float:
    return max(1.5, _EXPECTED_RPG_BASE + (pick - 1) * _EXPECTED_RPG_SLOPE / 10)


def _expected_apg(pick: int) -> float:
    return max(0.5, _EXPECTED_APG_BASE + (pick - 1) * _EXPECTED_APG_SLOPE / 10)


def compute_performance_score(row: pd.Series) -> float:
    """Combine normalized stat deviations into a single score."""
    pick = int(row["overall_pick"])
    exp_ppg = _expected_ppg(pick)
    exp_rpg = _expected_rpg(pick)
    exp_apg = _expected_apg(pick)
    ppg_dev = (row["rookie_ppg"] - exp_ppg) / max(exp_ppg, 1e-6)
    rpg_dev = (row["rookie_rpg"] - exp_rpg) / max(exp_rpg, 1e-6)
    apg_dev = (row["rookie_apg"] - exp_apg) / max(exp_apg, 1e-6)
    fg_bonus = (row["rookie_fg_pct"] - 0.45) * 0.5
    return ppg_dev + rpg_dev + apg_dev + fg_bonus


def classify_over_under(
    df: pd.DataFrame,
    ppg_threshold: float = 0.15,
    score_threshold: float = 0.25,
) -> pd.DataFrame:
    """Label each player as undervalued / overvalued / neutral.

    Parameters
    ----------
    df : DataFrame with columns: overall_pick, rookie_ppg, rookie_rpg,
         rookie_apg, rookie_fg_pct, rookie_3p_pct, rookie_ft_pct
    ppg_threshold : minimum relative PPG deviation to flag
    score_threshold : minimum composite score to flag

    Returns
    -------
    DataFrame with added columns: expected_ppg, expected_rpg, expected_apg,
        performance_score, value_label
    """
    df = df.copy()
    df["expected_ppg"] = df["overall_pick"].apply(_expected_ppg)
    df["expected_rpg"] = df["overall_pick"].apply(_expected_rpg)
    df["expected_apg"] = df["overall_pick"].apply(_expected_apg)

    df["performance_score"] = df.apply(compute_performance_score, axis=1)

    def _label(row):
        if row["performance_score"] >= score_threshold:
            return "undervalued"
        if row["performance_score"] <= -score_threshold:
            return "overvalued"
        return "neutral"

    df["value_label"] = df.apply(_label, axis=1)
    return df


def get_overlooked_players(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Return the top-N undervalued (over-performing) prospects."""
    labeled = classify_over_under(df)
    return (
        labeled[labeled["value_label"] == "undervalued"]
        .sort_values("performance_score", ascending=False)
        .head(top_n)
    )


def get_overvalued_players(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Return the top-N overvalued (under-performing) prospects."""
    labeled = classify_over_under(df)
    return (
        labeled[labeled["value_label"] == "overvalued"]
        .sort_values("performance_score", ascending=True)
        .head(top_n)
    )
