"""Tests for src.features.engineer."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.config import RAW_DIR
from src.features.engineer import (
    _assign_tier,
    _compute_deltas,
    _load_draft_info,
    _load_rookie_stats,
    _load_sophomore_stats,
    _safe_div,
    build_training_data,
    get_feature_columns,
    get_target_columns,
)


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_df():
    n = 30
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "player_id": range(n),
        "rookie_gp": rng.integers(40, 83, n),
        "rookie_mpg": rng.uniform(5, 35, n),
        "rookie_ppg": rng.uniform(2, 25, n),
        "rookie_rpg": rng.uniform(1, 12, n),
        "rookie_apg": rng.uniform(0, 8, n),
        "rookie_spg": rng.uniform(0, 2, n),
        "rookie_bpg": rng.uniform(0, 3, n),
        "rookie_tpg": rng.uniform(0, 4, n),
        "rookie_per": rng.uniform(5, 30, n),
        "rookie_fg_pct": rng.uniform(0.35, 0.55, n),
        "rookie_3p_pct": rng.uniform(0.25, 0.45, n),
        "rookie_ft_pct": rng.uniform(0.6, 0.9, n),
        "is_first_round": rng.integers(0, 2, n),
        "soph_mpg": rng.uniform(5, 40, n),
        "soph_ppg": rng.uniform(2, 30, n),
        "soph_rpg": rng.uniform(1, 14, n),
        "soph_apg": rng.uniform(0, 10, n),
        "soph_efficiency": rng.uniform(5, 35, n),
        "soph_plus_minus": rng.integers(-500, 500, n),
        "soph_gp": rng.integers(40, 83, n),
    })


@pytest.fixture
def tmp_raw(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    return raw


# ── _safe_div ─────────────────────────────────────────────────────────────────

class TestSafeDiv:
    def test_basic(self):
        num = pd.Series([10.0, 20.0, 30.0])
        den = pd.Series([2.0, 4.0, 5.0])
        result = _safe_div(num, den)
        np.testing.assert_allclose(result, [5.0, 5.0, 6.0])

    def test_zero_denominator_fills(self):
        num = pd.Series([10.0, 20.0])
        den = pd.Series([0.0, 5.0])
        result = _safe_div(num, den, fill=-1.0)
        assert result.iloc[0] == -1.0
        np.testing.assert_allclose(result.iloc[1], 4.0)

    def test_nan_handling(self):
        num = pd.Series([10.0, np.nan])
        den = pd.Series([2.0, 5.0])
        result = _safe_div(num, den, fill=-1.0)
        assert result.iloc[0] == pytest.approx(5.0)
        assert result.iloc[1] == -1.0


# ── _compute_deltas ───────────────────────────────────────────────────────────

class TestComputeDeltas:
    def test_columns_created(self, sample_df):
        result = _compute_deltas(sample_df.copy())
        expected = {"delta_mpg", "delta_ppg", "delta_per", "delta_min_total"}
        assert expected.issubset(result.columns)

    def test_delta_mpg_formula(self, sample_df):
        result = _compute_deltas(sample_df.copy())
        np.testing.assert_allclose(result["delta_mpg"], result["soph_mpg"] - result["rookie_mpg"])

    def test_delta_ppg_formula(self, sample_df):
        result = _compute_deltas(sample_df.copy())
        np.testing.assert_allclose(result["delta_ppg"], result["soph_ppg"] - result["rookie_ppg"])

    def test_delta_per_formula(self, sample_df):
        result = _compute_deltas(sample_df.copy())
        np.testing.assert_allclose(result["delta_per"], result["soph_efficiency"] - result["rookie_per"])

    def test_delta_min_total_with_existing(self, sample_df):
        df = sample_df.copy()
        df["soph_min_total"] = df["soph_mpg"] * df["soph_gp"]
        result = _compute_deltas(df)
        expected = df["soph_min_total"] - (df["rookie_mpg"] * df["rookie_gp"])
        np.testing.assert_allclose(result["delta_min_total"], expected)

    def test_delta_min_total_fallback_when_missing(self, sample_df):
        result = _compute_deltas(sample_df.copy())
        expected = (sample_df["soph_mpg"] * sample_df["soph_gp"]) - (sample_df["rookie_mpg"] * sample_df["rookie_gp"])
        np.testing.assert_allclose(result["delta_min_total"], expected, rtol=1e-5)


# ── _assign_tier ──────────────────────────────────────────────────────────────

class TestAssignTier:
    def test_breakout_by_mpg(self, sample_df):
        df = _compute_deltas(sample_df.copy())
        df.loc[0, "delta_mpg"] = 10.0
        df.loc[0, "delta_ppg"] = 0.0
        result = _assign_tier(df)
        assert result.loc[0, "tier"] == "breakout"

    def test_breakout_by_ppg(self, sample_df):
        df = _compute_deltas(sample_df.copy())
        df.loc[0, "delta_mpg"] = 0.0
        df.loc[0, "delta_ppg"] = 5.0
        result = _assign_tier(df)
        assert result.loc[0, "tier"] == "breakout"

    def test_bust_by_mpg(self, sample_df):
        df = _compute_deltas(sample_df.copy())
        df.loc[0, "delta_mpg"] = -10.0
        df.loc[0, "delta_ppg"] = 0.0
        result = _assign_tier(df)
        assert result.loc[0, "tier"] == "bust"

    def test_bust_by_ppg(self, sample_df):
        df = _compute_deltas(sample_df.copy())
        df.loc[0, "delta_mpg"] = 0.0
        df.loc[0, "delta_ppg"] = -5.0
        result = _assign_tier(df)
        assert result.loc[0, "tier"] == "bust"

    def test_neutral_when_below_thresholds(self, sample_df):
        df = _compute_deltas(sample_df.copy())
        df.loc[0, "delta_mpg"] = 2.0
        df.loc[0, "delta_ppg"] = 1.0
        result = _assign_tier(df)
        assert result.loc[0, "tier"] == "neutral"

    def test_neutral_when_above_bust_but_below_breakout(self, sample_df):
        df = _compute_deltas(sample_df.copy())
        df.loc[0, "delta_mpg"] = -2.0
        df.loc[0, "delta_ppg"] = -1.0
        result = _assign_tier(df)
        assert result.loc[0, "tier"] == "neutral"

    def test_tier_is_categorical(self, sample_df):
        df = _compute_deltas(sample_df.copy())
        result = _assign_tier(df)
        assert result["tier"].dtype.name == "category"

    def test_all_categories_present(self, sample_df):
        df = _compute_deltas(sample_df.copy())
        df.loc[0, "delta_mpg"] = 10.0
        df.loc[0, "delta_ppg"] = 0.0
        df.loc[1, "delta_mpg"] = -10.0
        df.loc[1, "delta_ppg"] = 0.0
        df.loc[2, "delta_mpg"] = 1.0
        df.loc[2, "delta_ppg"] = 1.0
        result = _assign_tier(df)
        cats = set(result["tier"].cat.categories)
        assert {"breakout", "bust", "neutral"}.issubset(cats)


# ── _load_rookie_stats ────────────────────────────────────────────────────────

class TestLoadRookieStats:
    def test_missing_file_returns_empty(self, tmp_raw, monkeypatch):
        monkeypatch.setattr("src.features.engineer.RAW_DIR", tmp_raw)
        result = _load_rookie_stats()
        assert result.empty

    def test_reads_parquet(self, tmp_raw, monkeypatch):
        df = pd.DataFrame({
            "PLAYER_ID": [1, 2],
            "PLAYER": ["A", "B"],
            "TEAM_ID": [10, 20],
            "TEAM": ["X", "Y"],
            "GP": [70, 65],
            "MIN": [28.0, 22.0],
            "FG_PCT": [0.48, 0.42],
            "FG3_PCT": [0.35, 0.31],
            "FT_PCT": [0.78, 0.82],
            "REB": [7.0, 5.0],
            "AST": [3.0, 2.0],
            "STL": [1.0, 0.9],
            "BLK": [0.5, 0.3],
            "TOV": [2.0, 1.5],
            "PTS": [16.0, 11.0],
            "EFF": [18.0, 12.0],
            "season": [2024, 2024],
        })
        df.to_parquet(tmp_raw / "rookie_stats.parquet")
        monkeypatch.setattr("src.features.engineer.RAW_DIR", tmp_raw)
        result = _load_rookie_stats()
        assert len(result) == 2
        assert "rookie_mpg" in result.columns
        assert "rookie_fg_pct" in result.columns

    def test_per_fallback_when_missing(self, tmp_raw, monkeypatch):
        df = pd.DataFrame({
            "PLAYER_ID": [1],
            "PLAYER": ["A"],
            "TEAM_ID": [10],
            "TEAM": ["X"],
            "GP": [70],
            "MIN": [28.0],
            "REB": [7.0],
            "AST": [3.0],
            "STL": [1.0],
            "BLK": [0.5],
            "TOV": [2.0],
            "PTS": [16.0],
            "season": [2024],
        })
        df.to_parquet(tmp_raw / "rookie_stats.parquet")
        monkeypatch.setattr("src.features.engineer.RAW_DIR", tmp_raw)
        result = _load_rookie_stats()
        assert "rookie_per" in result.columns
        assert result.loc[0, "rookie_per"] == pytest.approx(16 + 7 + 3 + 1 + 0.5 - 2)


# ── _load_sophomore_stats ─────────────────────────────────────────────────────

class TestLoadSophomoreStats:
    def test_missing_file_returns_empty(self, tmp_raw, monkeypatch):
        monkeypatch.setattr("src.features.engineer.RAW_DIR", tmp_raw)
        result = _load_sophomore_stats()
        assert result.empty

    def test_reads_parquet_and_computes_soph_min_total(self, tmp_raw, monkeypatch):
        df = pd.DataFrame({
            "PLAYER_ID": [1, 2],
            "GP": [70, 65],
            "MIN": [28.0, 22.0],
            "PTS": [16.0, 11.0],
            "REB": [7.0, 5.0],
            "AST": [3.0, 2.0],
            "EFF": [18.0, 12.0],
            "PLUS_MINUS": [100, -50],
        })
        df.to_parquet(tmp_raw / "sophomore_stats.parquet")
        monkeypatch.setattr("src.features.engineer.RAW_DIR", tmp_raw)
        result = _load_sophomore_stats()
        assert len(result) == 2
        assert "soph_min_total" in result.columns
        assert result.loc[0, "soph_min_total"] == pytest.approx(28.0 * 70)


# ── _load_draft_info ──────────────────────────────────────────────────────────

class TestLoadDraftInfo:
    def test_empty_when_rookie_missing(self, tmp_raw, monkeypatch):
        monkeypatch.setattr("src.features.engineer.RAW_DIR", tmp_raw)
        result = _load_draft_info()
        assert result.empty

    def test_derives_draft_fields(self, tmp_raw, monkeypatch):
        df = pd.DataFrame({
            "PLAYER_ID": [1, 2, 3],
            "PLAYER": ["A", "B", "C"],
            "ROUND_NUMBER": [1.0, 2.0, np.nan],
            "OVERALL_PICK": [5.0, 30.0, 45.0],
            "season": [2024, 2024, 2024],
        })
        df.to_parquet(tmp_raw / "rookie_stats.parquet")
        monkeypatch.setattr("src.features.engineer.RAW_DIR", tmp_raw)
        result = _load_draft_info()
        assert result.loc[0, "draft_round"] == 1
        assert result.loc[1, "draft_round"] == 2
        assert result.loc[2, "draft_round"] == 2  # default
        assert result.loc[0, "is_lottery"] == 1
        assert result.loc[2, "is_lottery"] == 0


# ── build_training_data ───────────────────────────────────────────────────────

class TestBuildTrainingData:
    def test_returns_empty_when_rookie_missing(self, tmp_raw, monkeypatch):
        monkeypatch.setattr("src.features.engineer.RAW_DIR", tmp_raw)
        result = build_training_data()
        assert result.empty

    def test_returns_empty_when_soph_missing(self, tmp_raw, monkeypatch):
        rookie = pd.DataFrame({
            "PLAYER_ID": [1], "PLAYER": ["A"], "TEAM_ID": [10], "TEAM": ["X"],
            "GP": [70], "MIN": [28.0], "FG_PCT": [0.48], "FG3_PCT": [0.35],
            "FT_PCT": [0.78], "REB": [7.0], "AST": [3.0], "STL": [1.0],
            "BLK": [0.5], "TOV": [2.0], "PTS": [16.0], "EFF": [18.0],
            "season": [2024],
        })
        rookie.to_parquet(tmp_raw / "rookie_stats.parquet")
        monkeypatch.setattr("src.features.engineer.RAW_DIR", tmp_raw)
        result = build_training_data()
        assert result.empty

    def test_writes_parquet_and_has_expected_cols(self, tmp_raw, tmp_path, monkeypatch):
        rookie = pd.DataFrame({
            "PLAYER_ID": [1, 2], "PLAYER": ["A", "B"], "TEAM_ID": [10, 20],
            "TEAM": ["X", "Y"], "GP": [70, 65], "MIN": [28.0, 22.0],
            "FG_PCT": [0.48, 0.42], "FG3_PCT": [0.35, 0.31], "FT_PCT": [0.78, 0.82],
            "REB": [7.0, 5.0], "AST": [3.0, 2.0], "STL": [1.0, 0.9],
            "BLK": [0.5, 0.3], "TOV": [2.0, 1.5], "PTS": [16.0, 11.0],
            "EFF": [18.0, 12.0], "season": [2024, 2024],
        })
        soph = pd.DataFrame({
            "PLAYER_ID": [1, 2],
            "GP": [75, 70], "MIN": [30.0, 25.0], "PTS": [18.0, 13.0],
            "REB": [8.0, 6.0], "AST": [4.0, 3.0], "EFF": [20.0, 14.0],
            "PLUS_MINUS": [120, -30],
        })
        processed = tmp_path / "processed"
        processed.mkdir()
        rookie.to_parquet(tmp_raw / "rookie_stats.parquet")
        soph.to_parquet(tmp_raw / "sophomore_stats.parquet")
        monkeypatch.setattr("src.features.engineer.RAW_DIR", tmp_raw)
        monkeypatch.setattr("src.features.engineer.PROCESSED_DIR", processed)
        result = build_training_data()
        assert len(result) == 2
        assert "delta_mpg" in result.columns
        assert "tier" in result.columns
        assert "dataset" in result.columns
        assert (processed / "training_data.parquet").exists()

    def test_season_filter(self, tmp_raw, tmp_path, monkeypatch):
        rookie = pd.DataFrame({
            "PLAYER_ID": [1, 2, 3],
            "PLAYER": ["A", "B", "C"], "TEAM_ID": [10, 20, 30],
            "TEAM": ["X", "Y", "Z"], "GP": [70, 65, 60],
            "MIN": [28.0, 22.0, 20.0], "FG_PCT": [0.48, 0.42, 0.40],
            "FG3_PCT": [0.35, 0.31, 0.30], "FT_PCT": [0.78, 0.82, 0.80],
            "REB": [7.0, 5.0, 4.0], "AST": [3.0, 2.0, 1.5],
            "STL": [1.0, 0.9, 0.8], "BLK": [0.5, 0.3, 0.2],
            "TOV": [2.0, 1.5, 1.8], "PTS": [16.0, 11.0, 10.0],
            "EFF": [18.0, 12.0, 11.0],
            "season": [2024, 2025, 2024],
        })
        soph = pd.DataFrame({
            "PLAYER_ID": [1, 2, 3],
            "GP": [75, 70, 68], "MIN": [30.0, 25.0, 22.0],
            "PTS": [18.0, 13.0, 12.0], "REB": [8.0, 6.0, 5.0],
            "AST": [4.0, 3.0, 2.5], "EFF": [20.0, 14.0, 13.0],
            "PLUS_MINUS": [120, -30, 50],
        })
        processed = tmp_path / "processed"
        processed.mkdir()
        rookie.to_parquet(tmp_raw / "rookie_stats.parquet")
        soph.to_parquet(tmp_raw / "sophomore_stats.parquet")
        monkeypatch.setattr("src.features.engineer.RAW_DIR", tmp_raw)
        monkeypatch.setattr("src.features.engineer.PROCESSED_DIR", processed)
        result = build_training_data(season=2024)
        assert len(result) == 2
        assert (result["rookie_season"] == 2024).all()


# ── get_feature_columns / get_target_columns ──────────────────────────────────

class TestSchemaHelpers:
    def test_feature_columns_non_empty(self):
        cols = get_feature_columns()
        assert len(cols) > 0

    def test_feature_columns_no_duplicates(self):
        cols = get_feature_columns()
        assert len(cols) == len(set(cols))

    def test_feature_columns_required_keys(self):
        required = {"rookie_ppg", "rookie_mpg", "rookie_per", "rookie_gp", "is_first_round"}
        assert required.issubset(set(get_feature_columns()))

    def test_target_columns_has_regression_and_classification(self):
        targets = get_target_columns()
        assert "regression_delta_mpg" in targets
        assert "regression_delta_ppg" in targets
        assert "regression_delta_per" in targets
        assert "classification_tier" in targets

    def test_target_columns_values_exist_in_output(self):
        targets = get_target_columns()
        for col in targets.values():
            assert col in ["delta_mpg", "delta_ppg", "delta_per", "tier"]
