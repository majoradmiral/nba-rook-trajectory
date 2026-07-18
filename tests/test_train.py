"""Tests for src.models.train."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from src.features.engineer import _assign_tier, _compute_deltas
from src.models.train import (
    _NUMERIC_FEATURES,
    get_feature_columns,
    train_and_evaluate,
    train_classification,
    train_regression,
)


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def training_df():
    np.random.seed(42)
    n = 100
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "player_id": range(n),
        "rookie_gp": rng.integers(40, 83, n),
        "rookie_mpg": rng.uniform(5, 35, n),
        "rookie_fg_pct": rng.uniform(0.35, 0.55, n),
        "rookie_3p_pct": rng.uniform(0.25, 0.45, n),
        "rookie_ft_pct": rng.uniform(0.6, 0.9, n),
        "rookie_rpg": rng.uniform(1, 12, n),
        "rookie_apg": rng.uniform(0, 8, n),
        "rookie_spg": rng.uniform(0, 2, n),
        "rookie_bpg": rng.uniform(0, 3, n),
        "rookie_tpg": rng.uniform(0, 4, n),
        "rookie_ppg": rng.uniform(2, 25, n),
        "rookie_per": rng.uniform(5, 30, n),
        "rookie_age": rng.uniform(19, 23, n),
        "rookie_team_win_pct": rng.uniform(0.2, 0.75, n),
        "draft_round": rng.integers(1, 3, n),
        "draft_pick": rng.uniform(1, 60, n),
        "is_first_round": rng.integers(0, 2, n),
        "is_lottery": rng.integers(0, 2, n),
        "soph_mpg": rng.uniform(5, 40, n),
        "soph_ppg": rng.uniform(2, 30, n),
        "soph_rpg": rng.uniform(1, 14, n),
        "soph_apg": rng.uniform(0, 10, n),
        "soph_efficiency": rng.uniform(5, 35, n),
        "soph_plus_minus": rng.integers(-500, 500, n),
        "soph_gp": rng.integers(40, 83, n),
    })


@pytest.fixture
def trained_df(training_df):
    df = _compute_deltas(training_df.copy())
    df = _assign_tier(df)
    return df


# ── Deltas & Tiers ────────────────────────────────────────────────────────────

class TestDeltasAndTiers:
    def test_compute_deltas_adds_columns(self, training_df):
        df = _compute_deltas(training_df.copy())
        assert "delta_mpg" in df.columns
        assert "delta_ppg" in df.columns
        assert "delta_per" in df.columns
        assert "delta_min_total" in df.columns

    def test_assign_tier_produces_valid_categories(self, training_df):
        df = _compute_deltas(training_df.copy())
        df = _assign_tier(df)
        assert df["tier"].dtype.name == "category"
        valid = {"breakout", "bust", "neutral"}
        assert set(df["tier"].cat.categories).issubset(valid)

    def test_assign_tier_breakout_at_threshold(self, training_df):
        df = _compute_deltas(training_df.copy())
        df.loc[0, "delta_mpg"] = 5.0
        df.loc[0, "delta_ppg"] = 0.0
        df = _assign_tier(df)
        assert df.loc[0, "tier"] == "breakout"

    def test_assign_tier_bust_at_threshold(self, training_df):
        df = _compute_deltas(training_df.copy())
        df.loc[0, "delta_mpg"] = -3.0
        df.loc[0, "delta_ppg"] = 0.0
        df = _assign_tier(df)
        assert df.loc[0, "tier"] == "bust"

    def test_assign_tier_boundary_breakout_mpg(self, training_df):
        df = _compute_deltas(training_df.copy())
        df.loc[0, "delta_mpg"] = 4.99
        df.loc[0, "delta_ppg"] = 0.0
        df = _assign_tier(df)
        assert df.loc[0, "tier"] == "neutral"

    def test_assign_tier_boundary_bust_mpg(self, training_df):
        df = _compute_deltas(training_df.copy())
        df.loc[0, "delta_mpg"] = -2.99
        df.loc[0, "delta_ppg"] = 0.0
        df = _assign_tier(df)
        assert df.loc[0, "tier"] == "neutral"

    def test_all_three_categories_can_appear(self, training_df):
        df = _compute_deltas(training_df.copy())
        df.loc[0, "delta_mpg"] = 10.0
        df.loc[1, "delta_mpg"] = -10.0
        df.loc[2, "delta_mpg"] = 1.0
        df = _assign_tier(df)
        cats = set(df["tier"].cat.categories)
        assert {"breakout", "bust", "neutral"}.issubset(cats)


# ── train_regression ──────────────────────────────────────────────────────────

class TestTrainRegression:
    def test_returns_metrics_for_each_target(self, trained_df):
        metrics = train_regression(trained_df)
        assert "delta_mpg" in metrics
        assert "delta_ppg" in metrics
        assert "delta_per" in metrics

    def test_metrics_have_expected_keys(self, trained_df):
        metrics = train_regression(trained_df)
        for name, vals in metrics.items():
            assert "mae" in vals
            assert "rmse" in vals
            assert "r2" in vals

    def test_metrics_are_finite(self, trained_df):
        metrics = train_regression(trained_df)
        for name, vals in metrics.items():
            assert np.isfinite(vals["mae"])
            assert np.isfinite(vals["rmse"])
            assert np.isfinite(vals["r2"])

    def test_mae_is_non_negative(self, trained_df):
        metrics = train_regression(trained_df)
        for name, vals in metrics.items():
            assert vals["mae"] >= 0

    def test_skips_missing_target(self, trained_df):
        df = trained_df.drop(columns=["delta_per"])
        metrics = train_regression(df)
        assert "delta_per" not in metrics

    def test_persists_models(self, trained_df, tmp_path, monkeypatch):
        models_dir = tmp_path / "models"
        results_dir = tmp_path / "results"
        models_dir.mkdir()
        results_dir.mkdir()
        monkeypatch.setattr("src.models.train.MODELS_DIR", models_dir)
        monkeypatch.setattr("src.models.train.RESULTS_DIR", results_dir)
        train_regression(trained_df)
        assert (models_dir / "reg_delta_mpg.pkl").exists()
        assert (models_dir / "reg_delta_ppg.pkl").exists()
        assert (models_dir / "reg_delta_per.pkl").exists()


# ── train_classification ──────────────────────────────────────────────────────

class TestTrainClassification:
    def test_returns_expected_keys(self, trained_df):
        metrics = train_classification(trained_df)
        assert "accuracy" in metrics
        assert "f1_weighted" in metrics
        assert "classes" in metrics
        assert "confusion_matrix" in metrics
        assert "classification_report" in metrics

    def test_accuracy_in_range(self, trained_df):
        metrics = train_classification(trained_df)
        assert 0.0 <= metrics["accuracy"] <= 1.0

    def test_f1_in_range(self, trained_df):
        metrics = train_classification(trained_df)
        assert 0.0 <= metrics["f1_weighted"] <= 1.0

    def test_classes_match_tier_categories(self, trained_df):
        metrics = train_classification(trained_df)
        expected = set(trained_df["tier"].cat.categories)
        assert set(metrics["classes"]).issubset(expected)

    def test_persists_model(self, trained_df, tmp_path, monkeypatch):
        models_dir = tmp_path / "models"
        results_dir = tmp_path / "results"
        models_dir.mkdir()
        results_dir.mkdir()
        monkeypatch.setattr("src.models.train.MODELS_DIR", models_dir)
        monkeypatch.setattr("src.models.train.RESULTS_DIR", results_dir)
        train_classification(trained_df)
        assert (models_dir / "clf_tier.pkl").exists()

    def test_skips_when_tier_missing(self, trained_df):
        df = trained_df.drop(columns=["tier"])
        metrics = train_classification(df)
        assert metrics == {}


# ── train_and_evaluate ────────────────────────────────────────────────────────

class TestTrainAndEvaluate:
    def test_returns_complete_metrics(self, tmp_path, monkeypatch):
        processed = tmp_path / "processed"
        models = tmp_path / "models"
        results = tmp_path / "results"
        raw = tmp_path / "raw"
        for d in (processed, models, results, raw):
            d.mkdir()
        _write_raw_data(raw)
        monkeypatch.setattr("src.features.engineer.RAW_DIR", raw)
        monkeypatch.setattr("src.features.engineer.PROCESSED_DIR", processed)
        monkeypatch.setattr("src.models.train.PROCESSED_DIR", processed)
        monkeypatch.setattr("src.models.train.MODELS_DIR", models)
        monkeypatch.setattr("src.models.train.RESULTS_DIR", results)
        metrics = train_and_evaluate()
        assert "regression" in metrics
        assert "classification" in metrics
        assert "n_rows" in metrics
        assert "n_features" in metrics

    def test_writes_metrics_json(self, tmp_path, monkeypatch):
        processed = tmp_path / "processed"
        models = tmp_path / "models"
        results = tmp_path / "results"
        raw = tmp_path / "raw"
        for d in (processed, models, results, raw):
            d.mkdir()
        _write_raw_data(raw)
        monkeypatch.setattr("src.features.engineer.RAW_DIR", raw)
        monkeypatch.setattr("src.features.engineer.PROCESSED_DIR", processed)
        monkeypatch.setattr("src.models.train.PROCESSED_DIR", processed)
        monkeypatch.setattr("src.models.train.MODELS_DIR", models)
        monkeypatch.setattr("src.models.train.RESULTS_DIR", results)
        train_and_evaluate()
        assert (results / "metrics.json").exists()
        with open(results / "metrics.json") as f:
            data = json.load(f)
        assert "regression" in data

    def test_raises_on_empty_data(self, tmp_path, monkeypatch):
        processed = tmp_path / "processed"
        models = tmp_path / "models"
        results = tmp_path / "results"
        for d in (processed, models, results):
            d.mkdir()
        monkeypatch.setattr("src.models.train.PROCESSED_DIR", processed)
        monkeypatch.setattr("src.models.train.MODELS_DIR", models)
        monkeypatch.setattr("src.models.train.RESULTS_DIR", results)
        with patch("src.features.engineer.build_training_data", return_value=pd.DataFrame()):
            with pytest.raises(ValueError, match="Empty training data"):
                train_and_evaluate()

    def test_season_filter_passed_to_build(self, tmp_path, monkeypatch):
        processed = tmp_path / "processed"
        models = tmp_path / "models"
        results = tmp_path / "results"
        for d in (processed, models, results):
            d.mkdir()
        df = _make_trained_df()
        with patch("src.features.engineer.build_training_data", return_value=df) as mock_build:
            monkeypatch.setattr("src.models.train.PROCESSED_DIR", processed)
            monkeypatch.setattr("src.models.train.MODELS_DIR", models)
            monkeypatch.setattr("src.models.train.RESULTS_DIR", results)
            train_and_evaluate(season=2024)
            mock_build.assert_called_once_with(season=2024)


def _make_trained_df() -> pd.DataFrame:
    np.random.seed(42)
    n = 60
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "player_id": range(n),
        "rookie_gp": rng.integers(40, 83, n),
        "rookie_mpg": rng.uniform(5, 35, n),
        "rookie_fg_pct": rng.uniform(0.35, 0.55, n),
        "rookie_3p_pct": rng.uniform(0.25, 0.45, n),
        "rookie_ft_pct": rng.uniform(0.6, 0.9, n),
        "rookie_rpg": rng.uniform(1, 12, n),
        "rookie_apg": rng.uniform(0, 8, n),
        "rookie_spg": rng.uniform(0, 2, n),
        "rookie_bpg": rng.uniform(0, 3, n),
        "rookie_tpg": rng.uniform(0, 4, n),
        "rookie_ppg": rng.uniform(2, 25, n),
        "rookie_per": rng.uniform(5, 30, n),
        "rookie_age": rng.uniform(19, 23, n),
        "rookie_team_win_pct": rng.uniform(0.2, 0.75, n),
        "draft_round": rng.integers(1, 3, n),
        "draft_pick": rng.uniform(1, 60, n),
        "is_first_round": rng.integers(0, 2, n),
        "is_lottery": rng.integers(0, 2, n),
        "soph_mpg": rng.uniform(5, 40, n),
        "soph_ppg": rng.uniform(2, 30, n),
        "soph_rpg": rng.uniform(1, 14, n),
        "soph_apg": rng.uniform(0, 10, n),
        "soph_efficiency": rng.uniform(5, 35, n),
        "soph_plus_minus": rng.integers(-500, 500, n),
        "soph_gp": rng.integers(40, 83, n),
    })
    df = _compute_deltas(df)
    df = _assign_tier(df)
    return df


def _write_raw_data(raw_dir: Path) -> None:
    np.random.seed(99)
    n = 30
    rng = np.random.default_rng(99)
    rookie = pd.DataFrame({
        "PLAYER_ID": range(n),
        "PLAYER": [f"Player{i}" for i in range(n)],
        "TEAM_ID": rng.integers(1610612740, 1610612755, n),
        "TEAM": ["TeamX"] * n,
        "GP": rng.integers(40, 83, n),
        "MIN": rng.uniform(15, 35, n),
        "FG_PCT": rng.uniform(0.35, 0.55, n),
        "FG3_PCT": rng.uniform(0.25, 0.45, n),
        "FT_PCT": rng.uniform(0.6, 0.9, n),
        "REB": rng.uniform(3, 12, n),
        "AST": rng.uniform(1, 7, n),
        "STL": rng.uniform(0.2, 2.0, n),
        "BLK": rng.uniform(0.1, 2.0, n),
        "TOV": rng.uniform(0.5, 4.0, n),
        "PTS": rng.uniform(5, 25, n),
        "EFF": rng.uniform(8, 28, n),
        "ROUND_NUMBER": rng.integers(1, 3, n),
        "OVERALL_PICK": rng.uniform(1, 60, n),
        "AGE": rng.uniform(19, 23, n),
        "TEAM_WIN_PCT": rng.uniform(0.2, 0.75, n),
        "season": [2024] * n,
    })
    soph = pd.DataFrame({
        "PLAYER_ID": range(n),
        "GP": rng.integers(40, 83, n),
        "MIN": rng.uniform(15, 38, n),
        "PTS": rng.uniform(5, 28, n),
        "REB": rng.uniform(3, 14, n),
        "AST": rng.uniform(1, 9, n),
        "EFF": rng.uniform(8, 30, n),
        "PLUS_MINUS": rng.integers(-400, 400, n),
    })
    rookie.to_parquet(raw_dir / "rookie_stats.parquet")
    soph.to_parquet(raw_dir / "sophomore_stats.parquet")


# ── Schema consistency ────────────────────────────────────────────────────────

class TestSchemaConsistency:
    def test_feature_columns_match_numeric_features(self):
        features = set(get_feature_columns())
        numeric = set(_NUMERIC_FEATURES)
        assert features == numeric

    def test_feature_columns_no_targets_leakage(self):
        targets = {"delta_mpg", "delta_ppg", "delta_per", "delta_min_total", "tier", "dataset"}
        features = set(get_feature_columns())
        assert targets.isdisjoint(features)

    def test_feature_columns_no_sophomore_leakage(self):
        soph_cols = {"soph_mpg", "soph_ppg", "soph_rpg", "soph_apg",
                     "soph_efficiency", "soph_plus_minus", "soph_gp"}
        features = set(get_feature_columns())
        assert soph_cols.isdisjoint(features)
