"""Tests for src.analysis.team_comparison."""

from __future__ import annotations

import pandas as pd
import pytest

from src.analysis.team_comparison import team_comparison


@pytest.fixture
def draft_sample():
    return pd.DataFrame([
        {"team": "WAS", "overall_pick": 1, "player": "AJ Dybantsa", "rookie_ppg": 25.5, "rookie_rpg": 6.8, "rookie_apg": 3.7, "rookie_fg_pct": 0.51, "rookie_3p_pct": 0.32},
        {"team": "UTA", "overall_pick": 2, "player": "Darryn Peterson", "rookie_ppg": 20.2, "rookie_rpg": 4.2, "rookie_apg": 1.6, "rookie_fg_pct": 0.44, "rookie_3p_pct": 0.38},
        {"team": "MEM", "overall_pick": 3, "player": "Cameron Boozer", "rookie_ppg": 22.5, "rookie_rpg": 10.2, "rookie_apg": 4.1, "rookie_fg_pct": 0.56, "rookie_3p_pct": 0.40},
        {"team": "WAS", "overall_pick": 15, "player": "Caleb Wilson", "rookie_ppg": 17.0, "rookie_rpg": 5.0, "rookie_apg": 2.5, "rookie_fg_pct": 0.48, "rookie_3p_pct": 0.35},
    ])


class TestTeamComparison:
    def test_returns_dataframe(self, draft_sample):
        result = team_comparison(draft_sample)
        assert isinstance(result, pd.DataFrame)

    def test_correct_number_of_teams(self, draft_sample):
        result = team_comparison(draft_sample)
        assert len(result) == 3  # WAS, UTA, MEM

    def test_sorted_by_draft_capital(self, draft_sample):
        result = team_comparison(draft_sample)
        assert result["draft_capital"].is_monotonic_decreasing

    def test_was_has_two_picks(self, draft_sample):
        result = team_comparison(draft_sample)
        was = result[result["team"] == "WAS"].iloc[0]
        assert was["num_picks"] == 2

    def test_uta_has_one_pick(self, draft_sample):
        result = team_comparison(draft_sample)
        uta = result[result["team"] == "UTA"].iloc[0]
        assert uta["num_picks"] == 1

    def test_best_player_column(self, draft_sample):
        result = team_comparison(draft_sample)
        was = result[result["team"] == "WAS"].iloc[0]
        assert was["best_player"] == "AJ Dybantsa"

    def test_total_stats_aggregated(self, draft_sample):
        result = team_comparison(draft_sample)
        was = result[result["team"] == "WAS"].iloc[0]
        assert abs(was["total_ppg"] - (25.5 + 17.0)) < 1e-6

    def test_required_columns_present(self, draft_sample):
        result = team_comparison(draft_sample)
        expected = {"team", "num_picks", "total_ppg", "draft_capital", "best_player", "best_ppg"}
        assert expected.issubset(result.columns)
