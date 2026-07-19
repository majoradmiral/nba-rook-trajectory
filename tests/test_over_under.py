"""Tests for src.analysis.over_under."""

from __future__ import annotations

import pandas as pd
import pytest

from src.analysis.over_under import (
    _expected_ppg,
    classify_over_under,
    compute_performance_score,
    get_overlooked_players,
    get_overvalued_players,
)


@pytest.fixture
def draft_sample():
    return pd.DataFrame([
        {"overall_pick": 1, "rookie_ppg": 25.5, "rookie_rpg": 6.8, "rookie_apg": 3.7, "rookie_fg_pct": 0.51, "rookie_3p_pct": 0.32, "rookie_ft_pct": 0.74},
        {"overall_pick": 2, "rookie_ppg": 20.2, "rookie_rpg": 4.2, "rookie_apg": 1.6, "rookie_fg_pct": 0.44, "rookie_3p_pct": 0.38, "rookie_ft_pct": 0.83},
        {"overall_pick": 3, "rookie_ppg": 22.5, "rookie_rpg": 10.2, "rookie_apg": 4.1, "rookie_fg_pct": 0.56, "rookie_3p_pct": 0.40, "rookie_ft_pct": 0.78},
        {"overall_pick": 30, "rookie_ppg": 8.0, "rookie_rpg": 3.0, "rookie_apg": 1.0, "rookie_fg_pct": 0.45, "rookie_3p_pct": 0.33, "rookie_ft_pct": 0.75},
        {"overall_pick": 15, "rookie_ppg": 12.0, "rookie_rpg": 4.0, "rookie_apg": 2.0, "rookie_fg_pct": 0.40, "rookie_3p_pct": 0.30, "rookie_ft_pct": 0.70},
    ])


class TestExpectedCurves:
    def test_ppg_declines_with_pick(self):
        assert _expected_ppg(1) > _expected_ppg(10)
        assert _expected_ppg(10) > _expected_ppg(30)

    def test_ppg_floor(self):
        assert _expected_ppg(60) >= 5.0


class TestComputePerformanceScore:
    def test_returns_scalar(self, draft_sample):
        score = compute_performance_score(draft_sample.iloc[0])
        assert isinstance(score, float)

    def test_top_pick_has_positive_score(self, draft_sample):
        row = draft_sample.iloc[0]
        score = compute_performance_score(row)
        assert score > 0

    def test_last_pick_penalized(self, draft_sample):
        row = draft_sample.iloc[3]
        score = compute_performance_score(row)
        assert score < 0


class TestClassifyOverUnder:
    def test_returns_dataframe_with_labels(self, draft_sample):
        result = classify_over_under(draft_sample)
        assert "value_label" in result.columns
        assert set(result["value_label"]).issubset({"undervalued", "overvalued", "neutral"})

    def test_top_pick_likely_neutral_or_undervalued(self, draft_sample):
        result = classify_over_under(draft_sample)
        top = result[result["overall_pick"] == 1].iloc[0]
        assert top["value_label"] in {"undervalued", "neutral"}

    def test_bottom_pick_likely_overvalued(self, draft_sample):
        result = classify_over_under(draft_sample)
        bottom = result[result["overall_pick"] == 30].iloc[0]
        assert bottom["value_label"] in {"overvalued", "neutral"}

    def test_adds_expected_columns(self, draft_sample):
        result = classify_over_under(draft_sample)
        assert "expected_ppg" in result.columns
        assert "expected_rpg" in result.columns
        assert "expected_apg" in result.columns
        assert "performance_score" in result.columns


class TestGetOverlooked:
    def test_returns_dataframe(self, draft_sample):
        result = get_overlooked_players(draft_sample)
        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            assert (result["value_label"] == "undervalued").all()

    def test_sorted_descending(self, draft_sample):
        result = get_overlooked_players(draft_sample)
        if len(result) > 1:
            assert result["performance_score"].is_monotonic_decreasing


class TestGetOvervalued:
    def test_returns_dataframe(self, draft_sample):
        result = get_overvalued_players(draft_sample)
        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            assert (result["value_label"] == "overvalued").all()

    def test_sorted_ascending(self, draft_sample):
        result = get_overvalued_players(draft_sample)
        if len(result) > 1:
            assert result["performance_score"].is_monotonic_increasing
