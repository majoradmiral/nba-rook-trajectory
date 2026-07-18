"""Tests for src.pipeline."""

from __future__ import annotations

import pandas as pd
import pytest

from src.pipeline import build_inference_2025_rookies, pull_rookie_stats


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_rookie_df():
    return pd.DataFrame({
        "player_id": [1, 2, 3],
        "player_name": ["Alice", "Bob", "Charlie"],
        "team_id": [1610612747, 1610612748, 1610612749],
        "TEAM": ["Lakers", "Celtics", "Heat"],
        "rookie_gp": [70, 65, 60],
        "rookie_mpg": [28.5, 22.0, 19.5],
        "FGM": [10.0, 8.0, 7.5],
        "FGA": [21.0, 19.0, 17.0],
        "rookie_fg_pct": [0.48, 0.42, 0.45],
        "FG3M": [2.0, 1.5, 1.8],
        "FG3A": [6.0, 5.0, 5.5],
        "rookie_3p_pct": [0.35, 0.31, 0.33],
        "FTM": [3.0, 2.5, 2.0],
        "FTA": [4.0, 3.5, 3.0],
        "rookie_ft_pct": [0.78, 0.82, 0.75],
        "OREB": [1.5, 1.0, 0.8],
        "DREB": [5.7, 4.1, 3.7],
        "rookie_rpg": [7.2, 5.1, 4.5],
        "rookie_apg": [3.4, 2.8, 2.0],
        "rookie_spg": [1.1, 0.9, 0.8],
        "rookie_bpg": [0.6, 0.3, 0.4],
        "rookie_tpg": [2.1, 1.5, 1.8],
        "rookie_ppg": [16.3, 11.2, 10.5],
        "rookie_per": [18.0, 12.5, 11.0],
        "rookie_season": [2025, 2025, 2025],
    })


# ── build_inference_2025_rookies ──────────────────────────────────────────────

class TestBuildInference2025Rookies:
    def test_filters_2025_only(self, sample_rookie_df):
        df = sample_rookie_df.copy()
        result = build_inference_2025_rookies(df)
        assert len(result) == 3

    def test_returns_empty_for_non_2025(self, sample_rookie_df):
        df = sample_rookie_df.copy()
        df["rookie_season"] = 2024
        result = build_inference_2025_rookies(df)
        assert result.empty

    def test_sets_dataset_tag(self, sample_rookie_df):
        result = build_inference_2025_rookies(sample_rookie_df)
        assert (result["dataset"] == "inference_2025").all()

    def test_sets_sl_available_flag(self, sample_rookie_df):
        result = build_inference_2025_rookies(sample_rookie_df, sl_available=True)
        assert "sl_available" in result.columns
        assert (result["sl_available"] == True).all()

    def test_sl_available_false_by_default(self, sample_rookie_df):
        result = build_inference_2025_rookies(sample_rookie_df)
        assert "sl_available" in result.columns
        assert (result["sl_available"] == False).all()

    def test_empty_input_returns_empty(self):
        result = build_inference_2025_rookies(pd.DataFrame())
        assert result.empty

    def test_preserves_required_columns(self, sample_rookie_df):
        result = build_inference_2025_rookies(sample_rookie_df)
        required = {"player_name", "rookie_mpg", "rookie_ppg", "rookie_per", "season"}
        assert required.issubset(result.columns)

    def test_resets_index(self, sample_rookie_df):
        result = build_inference_2025_rookies(sample_rookie_df)
        assert list(result.index) == list(range(len(result)))

    def test_mixed_seasons_filters_correctly(self, sample_rookie_df):
        df = sample_rookie_df.copy()
        df.loc[0, "rookie_season"] = 2024
        df.loc[1, "rookie_season"] = 2025
        df.loc[2, "rookie_season"] = 2025
        result = build_inference_2025_rookies(df)
        assert len(result) == 2
        assert set(result["player_name"]) == {"Bob", "Charlie"}

    def test_normalizes_season_column(self):
        df = pd.DataFrame({
            "player_id": [1],
            "player_name": ["A"],
            "rookie_mpg": [25.0],
            "rookie_ppg": [15.0],
            "rookie_per": [18.0],
            "season": [2025],
        })
        result = build_inference_2025_rookies(df)
        assert "rookie_season" in result.columns
        assert result.loc[0, "rookie_season"] == 2025
