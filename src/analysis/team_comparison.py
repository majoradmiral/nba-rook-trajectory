"""Team-level aggregation and comparison for draft classes.

For each NBA team with a 2026 first-round pick, compute:
    - total_ppg, total_rpg, total_apg
    - avg_fg_pct, avg_3p_pct
    - best_player (highest PPG)
    - draft_capital (sum of 1/overall_pick weights)
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def team_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate draft-class stats by NBA team.

    Parameters
    ----------
    df : DataFrame with at least: team, overall_pick, rookie_ppg,
         rookie_rpg, rookie_apg, rookie_fg_pct, rookie_3p_pct, player

    Returns
    -------
    DataFrame grouped by team with aggregated metrics.
    """
    required = {"team", "overall_pick", "rookie_ppg", "rookie_rpg", "rookie_apg", "player"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"team_comparison missing columns: {missing}")

    def _best_player(ppg_series: pd.Series) -> Any:
        idx = ppg_series.idxmax()
        return df.loc[idx, "player"]

    grouped = (
        df.groupby("team")
        .agg(
            num_picks=("overall_pick", "count"),
            total_ppg=("rookie_ppg", "sum"),
            total_rpg=("rookie_rpg", "sum"),
            total_apg=("rookie_apg", "sum"),
            avg_fg_pct=("rookie_fg_pct", "mean"),
            avg_3p_pct=("rookie_3p_pct", "mean"),
            best_ppg=("rookie_ppg", "max"),
            best_player=("rookie_ppg", _best_player),
            draft_capital=("overall_pick", lambda p: sum(1.0 / x for x in p)),
        )
        .reset_index()
        .sort_values("draft_capital", ascending=False)
    )
    return grouped
