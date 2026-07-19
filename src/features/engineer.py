"""Feature engineering: raw parquet -> training_data.parquet.

Reads:
    data/raw/rookie_stats.parquet
    data/raw/sophomore_stats.parquet
    data/raw/summer_league.parquet  (optional, merged by player_id if available)

Writes:
    data/processed/training_data.parquet

The output schema matches the 52-column frame used by train_eval.py and
the Streamlit dashboard.
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

# ── Column groups ────────────────────────────────────────────────────────────
_ROOKIE_COLS = [
    "player_id", "player_name", "rookie_gp", "rookie_mpg",
    "rookie_fg_pct", "rookie_3p_pct", "rookie_ft_pct",
    "rookie_rpg", "rookie_apg", "rookie_spg", "rookie_bpg", "rookie_tpg",
    "rookie_ppg", "rookie_per", "rookie_season", "rookie_age",
    "rookie_team_win_pct",
]

_SOPH_COLS = [
    "player_id", "soph_gp", "soph_mpg", "soph_ppg", "soph_rpg",
    "soph_apg", "soph_efficiency", "soph_plus_minus", "soph_min_total",
]

_DRAFT_COLS = [
    "player_id", "ROUND_NUMBER", "OVERALL_PICK", "draft_round", "draft_pick",
    "is_first_round", "is_lottery",
]

# ── Tier thresholds ──────────────────────────────────────────────────────────
_BREAKOUT_MPG_DELTA = 5.0
_BREAKOUT_PPG_DELTA = 3.0
_BUST_MPG_DELTA = -3.0
_BUST_PPG_DELTA = -2.0


def _safe_div(numerator: pd.Series, denominator: pd.Series, fill: float = 0.0) -> pd.Series:
    denom = denominator.replace(0, np.nan)
    result = pd.Series(numerator.values / denom.values, index=numerator.index)
    return result.fillna(fill)


def _compute_deltas(df: pd.DataFrame) -> pd.DataFrame:
    """Add delta columns (sophomore - rookie)."""
    df["delta_mpg"] = df["soph_mpg"] - df["rookie_mpg"]
    df["delta_ppg"] = df["soph_ppg"] - df["rookie_ppg"]
    df["delta_per"] = df["soph_efficiency"] - df["rookie_per"]
    soph_min_total = df.get("soph_min_total")
    if soph_min_total is None:
        soph_min_total = df.get("soph_mpg", 0) * df.get("soph_gp", 1)
    df["delta_min_total"] = soph_min_total - (df["rookie_mpg"] * df["rookie_gp"])
    return df


def _assign_tier(df: pd.DataFrame) -> pd.DataFrame:
    """Label each player as breakout / bust / neutral."""
    conditions = [
        (df["delta_mpg"] >= _BREAKOUT_MPG_DELTA) | (df["delta_ppg"] >= _BREAKOUT_PPG_DELTA),
        (df["delta_mpg"] <= _BUST_MPG_DELTA) | (df["delta_ppg"] <= _BUST_PPG_DELTA),
    ]
    choices = ["breakout", "bust"]
    df["tier"] = np.select(conditions, choices, default="neutral")
    df["tier"] = df["tier"].astype("category")
    return df


def _load_rookie_stats() -> pd.DataFrame:
    path = RAW_DIR / "rookie_stats.parquet"
    if not path.exists():
        logger.error(f"rookie_stats.parquet not found at {path}")
        return pd.DataFrame()
    df = pd.read_parquet(path)
    rename = {
        "PLAYER_ID": "player_id",
        "PLAYER": "player_name",
        "TEAM_ID": "team_id",
        "TEAM": "TEAM",
        "GP": "rookie_gp",
        "MIN": "rookie_mpg",
        "FG_PCT": "rookie_fg_pct",
        "FG3_PCT": "rookie_3p_pct",
        "FT_PCT": "rookie_ft_pct",
        "REB": "rookie_rpg",
        "AST": "rookie_apg",
        "STL": "rookie_spg",
        "BLK": "rookie_bpg",
        "TOV": "rookie_tpg",
        "PTS": "rookie_ppg",
        "EFF": "rookie_per",
        "AGE": "rookie_age",
        "TEAM_WIN_PCT": "rookie_team_win_pct",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    if "season" in df.columns and "rookie_season" not in df.columns:
        df["rookie_season"] = df["season"].astype(int)
    if "rookie_per" not in df.columns or df["rookie_per"].isna().all():
        df["rookie_per"] = (
            df.get("rookie_ppg", 0) + df.get("rookie_rpg", 0) +
            df.get("rookie_apg", 0) + df.get("rookie_spg", 0) +
            df.get("rookie_bpg", 0) - df.get("rookie_tpg", 0)
        )
    logger.info(f"Loaded rookie stats: {len(df)} rows")
    return df


def _load_sophomore_stats() -> pd.DataFrame:
    path = RAW_DIR / "sophomore_stats.parquet"
    if not path.exists():
        logger.error(f"sophomore_stats.parquet not found at {path}")
        return pd.DataFrame()
    df = pd.read_parquet(path)
    rename = {
        "PLAYER_ID": "player_id",
        "GP": "soph_gp",
        "MIN": "soph_mpg",
        "PTS": "soph_ppg",
        "REB": "soph_rpg",
        "AST": "soph_apg",
        "EFF": "soph_efficiency",
        "PLUS_MINUS": "soph_plus_minus",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    if "soph_mpg" in df.columns and "soph_gp" in df.columns:
        df["soph_min_total"] = df["soph_mpg"] * df["soph_gp"]
    else:
        df["soph_min_total"] = np.nan
    if "soph_efficiency" not in df.columns:
        df["soph_efficiency"] = (
            df.get("soph_ppg", 0) + df.get("soph_rpg", 0) +
            df.get("soph_apg", 0) + df.get("soph_spg", 0) +
            df.get("soph_bpg", 0) - df.get("soph_tpg", 0)
        )
    logger.info(f"Loaded sophomore stats: {len(df)} rows")
    return df


def _load_draft_info() -> pd.DataFrame:
    """Load draft metadata from rookie_stats if present, otherwise return empty."""
    rookie = _load_rookie_stats()
    if rookie.empty:
        return pd.DataFrame()
    draft_cols = ["player_id", "ROUND_NUMBER", "OVERALL_PICK", "draft_round", "draft_pick",
                  "is_first_round", "is_lottery", "TEAM_ID", "TEAM", "team_id", "player_name"]
    existing = [c for c in draft_cols if c in rookie.columns]
    df = rookie[existing].copy()
    if "draft_round" not in df.columns and "ROUND_NUMBER" in df.columns:
        df["draft_round"] = df["ROUND_NUMBER"].fillna(2).astype(int)
    if "draft_pick" not in df.columns and "OVERALL_PICK" in df.columns:
        df["draft_pick"] = df["OVERALL_PICK"]
    if "is_first_round" not in df.columns:
        draft_series = df.get("draft_round")
        if draft_series is None:
            draft_series = pd.Series(2, index=df.index)
        df["is_first_round"] = (draft_series == 1).astype(int)
    if "is_lottery" not in df.columns and "draft_pick" in df.columns:
        df["is_lottery"] = (df["draft_pick"] <= 14).astype(int)
    return df


def build_training_data(season: int | None = None) -> pd.DataFrame:
    """Build the labeled training frame.

    Parameters
    ----------
    season : int, optional
        Restrict to a single rookie season.  None keeps all seasons.

    Returns
    -------
    pd.DataFrame with 52 columns (features + targets + labels).
    """
    rookie = _load_rookie_stats()
    soph = _load_sophomore_stats()
    draft = _load_draft_info()

    if rookie.empty or soph.empty:
        logger.error("Cannot build training data: missing raw parquet files")
        return pd.DataFrame()

    base = rookie.merge(soph, on="player_id", how="inner")
    if base.empty:
        logger.error("No overlapping player_ids between rookie and sophomore stats")
        return pd.DataFrame()

    if not draft.empty:
        base = base.merge(draft, on="player_id", how="left")

    base = _compute_deltas(base)
    base = _assign_tier(base)
    base["dataset"] = "training"

    if season is not None and "rookie_season" in base.columns:
        base = base[base["rookie_season"] == season]

    out = PROCESSED_DIR / "training_data.parquet"
    base.to_parquet(out, index=False)
    logger.info(f"Saved training_data.parquet — {len(base)} rows, {len(base.columns)} cols")
    return base


def build_training_data_with_draft_class(
    draft_df: pd.DataFrame | None = None,
    season: int = 2026,
) -> pd.DataFrame:
    """Build a training frame that includes the draft class as inference rows.

    This appends the 2026 draft class (without sophomore targets) to the
    historical training data so the model can produce predictions for the
    current rookie class.

    Parameters
    ----------
    draft_df : DataFrame, optional
        Pre-loaded draft class.  If None, loads from draft_2026.parquet.
    season : int
        Rookie season label for the draft class rows.

    Returns
    -------
    pd.DataFrame with historical training rows + draft-class inference rows.
    """
    historical = build_training_data(season=None)
    if historical.empty and not draft_df is None:
        historical = pd.DataFrame()

    if draft_df is None:
        try:
            from src.features.draft_2026 import load_draft_2026
            draft_df = load_draft_2026()
        except Exception as exc:
            logger.warning(f"Could not load draft_2026: {exc}")
            draft_df = pd.DataFrame()

    if draft_df.empty:
        logger.warning("No draft class data available")
        return historical

    draft = draft_df.copy()
    draft["rookie_season"] = season
    draft["dataset"] = "inference_2026"
    draft["tier"] = pd.Categorical(draft["tier"].astype(str) if "tier" in draft.columns else ["neutral"] * len(draft))
    for col in ["delta_mpg", "delta_ppg", "delta_per", "delta_min_total",
                "soph_mpg", "soph_ppg", "soph_rpg", "soph_apg",
                "soph_efficiency", "soph_plus_minus", "soph_gp"]:
        if col not in draft.columns:
            draft[col] = np.nan

    combined = pd.concat([historical, draft], ignore_index=True)
    out = PROCESSED_DIR / "training_data_with_draft_2026.parquet"
    combined.to_parquet(out, index=False)
    logger.info(f"Saved training_data_with_draft_2026.parquet — {len(combined)} rows")
    return combined


def get_feature_columns() -> list[str]:
    """Return the ordered list of feature columns used by the model."""
    return [
        "rookie_gp", "rookie_mpg", "rookie_fg_pct", "rookie_3p_pct",
        "rookie_ft_pct", "rookie_rpg", "rookie_apg", "rookie_spg",
        "rookie_bpg", "rookie_tpg", "rookie_ppg", "rookie_per",
        "rookie_age", "rookie_team_win_pct",
        "draft_round", "draft_pick", "is_first_round", "is_lottery",
    ]


def get_target_columns() -> dict[str, str]:
    """Return target column names by task."""
    return {
        "regression_delta_mpg": "delta_mpg",
        "regression_delta_ppg": "delta_ppg",
        "regression_delta_per": "delta_per",
        "classification_tier": "tier",
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    df = build_training_data()
    if not df.empty:
        print(df[get_feature_columns() + list(get_target_columns().values())].describe())
        print("\nTier distribution:")
        print(df["tier"].value_counts())
