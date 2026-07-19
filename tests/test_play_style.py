"""Tests for src.analysis.play_style."""

from __future__ import annotations

import pandas as pd
import pytest

from src.analysis.play_style import compute_play_style, get_style_summary


@pytest.fixture
def draft_sample():
    return pd.DataFrame([
        {
            "overall_pick": 1, "player": "A", "team": "WAS", "position": "F",
            "rookie_ppg": 25.5, "rookie_rpg": 6.8, "rookie_apg": 3.7,
            "rookie_spg": 1.3, "rookie_bpg": 0.5, "rookie_tpg": 2.5,
            "rookie_fg_pct": 0.51, "rookie_3p_pct": 0.32, "rookie_ft_pct": 0.74,
        },
        {
            "overall_pick": 5, "player": "B", "team": "LAC", "position": "G",
            "rookie_ppg": 17.9, "rookie_rpg": 5.1, "rookie_apg": 4.2,
            "rookie_spg": 1.5, "rookie_bpg": 0.3, "rookie_tpg": 2.0,
            "rookie_fg_pct": 0.45, "rookie_3p_pct": 0.40, "rookie_ft_pct": 0.80,
        },
    ])


class TestComputePlayStyle:
    def test_adds_metric_columns(self, draft_sample):
        result = compute_play_style(draft_sample)
        expected = {
            "usage_rate", "three_point_tendency", "rim_rate_proxy",
            "assist_ratio", "defensive_activity", "efficiency_index",
        }
        assert expected.issubset(result.columns)

    def test_metrics_in_valid_range(self, draft_sample):
        result = compute_play_style(draft_sample)
        assert result["usage_rate"].between(0, 1).all()
        assert result["three_point_tendency"].between(0, 1).all()
        assert result["assist_ratio"].between(0, 1).all()
        assert (result["defensive_activity"] >= 0).all()
        assert (result["efficiency_index"] >= 0).all()

    def test_efficiency_index_formula(self, draft_sample):
        result = compute_play_style(draft_sample)
        row = result.iloc[0]
        expected = (
            row["rookie_ppg"] + row["rookie_rpg"] + row["rookie_apg"]
            + row["rookie_spg"] + row["rookie_bpg"] - row["rookie_tpg"]
        )
        assert abs(row["efficiency_index"] - expected) < 1e-6

    def test_does_not_mutate_input(self, draft_sample):
        original_cols = set(draft_sample.columns)
        compute_play_style(draft_sample)
        assert set(draft_sample.columns) == original_cols

    def test_handles_missing_spg_bpg(self):
        df = pd.DataFrame([{
            "overall_pick": 1, "rookie_ppg": 20.0, "rookie_rpg": 5.0,
            "rookie_apg": 3.0, "rookie_tpg": 2.0,
            "rookie_fg_pct": 0.45, "rookie_3p_pct": 0.35, "rookie_ft_pct": 0.75,
        }])
        result = compute_play_style(df)
        assert "defensive_activity" in result.columns
        assert result.iloc[0]["defensive_activity"] == 0.0


class TestGetStyleSummary:
    def test_returns_correct_columns(self, draft_sample):
        result = get_style_summary(draft_sample)
        expected = {
            "overall_pick", "player", "team", "position",
            "usage_rate", "three_point_tendency", "rim_rate_proxy",
            "assist_ratio", "defensive_activity", "efficiency_index",
        }
        assert expected.issubset(result.columns)

    def test_sorted_by_efficiency(self, draft_sample):
        result = get_style_summary(draft_sample)
        assert result["efficiency_index"].is_monotonic_decreasing
