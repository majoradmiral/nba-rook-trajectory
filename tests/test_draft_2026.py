"""Tests for src.features.draft_2026."""

from __future__ import annotations

import pandas as pd
import pytest

from src.features.draft_2026 import (
    _build_draft_df,
    get_draft_class_summary,
    load_draft_2026,
)


class TestDraft2026:
    def test_load_returns_dataframe(self):
        df = load_draft_2026()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 30

    def test_has_expected_columns(self):
        df = load_draft_2026()
        expected = {
            "overall_pick", "player", "team", "college", "position",
            "rookie_ppg", "rookie_rpg", "rookie_apg",
            "rookie_fg_pct", "rookie_3p_pct", "rookie_ft_pct",
            "draft_round", "draft_pick", "is_lottery",
        }
        assert expected.issubset(df.columns)

    def test_overall_pick_range(self):
        df = load_draft_2026()
        assert df["overall_pick"].min() == 1
        assert df["overall_pick"].max() == 30
        assert df["overall_pick"].is_unique

    def test_top_pick_is_aj_dybantsa(self):
        df = load_draft_2026()
        top = df[df["overall_pick"] == 1].iloc[0]
        assert top["player"] == "AJ Dybantsa"
        assert top["team"] == "Washington Wizards"

    def test_lottery_flag_set(self):
        df = load_draft_2026()
        assert (df[df["overall_pick"] <= 14]["is_lottery"] == 1).all()
        assert (df[df["overall_pick"] > 14]["is_lottery"] == 0).all()

    def test_summary_returns_subset(self):
        summary = get_draft_class_summary()
        assert len(summary) == 30
        assert "player" in summary.columns
        assert "rookie_ppg" in summary.columns

    def test_build_draft_df_is_deterministic(self):
        df = _build_draft_df()
        assert len(df) == 30
        assert df["rookie_season"].nunique() == 1
        assert df.loc[0, "overall_pick"] == 1
