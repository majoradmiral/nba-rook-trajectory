"""Model training, cross-validation, evaluation, and serialization.

Supports two task families:
  1. Regression — predicts delta_mpg, delta_ppg, delta_per
  2. Classification — predicts tier (breakout / bust / neutral)

Artifacts are written to ``models/`` and metrics to ``results/metrics.json``.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

_candidate = Path(__file__).resolve()
while not (_candidate / "src").is_dir() and _candidate != _candidate.parent:
    _candidate = _candidate.parent
sys.path.insert(0, str(_candidate))

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.config import PROCESSED_DIR, ROOT
from src.features.engineer import get_feature_columns, get_target_columns

logger = logging.getLogger(__name__)

MODELS_DIR = ROOT / "models"
RESULTS_DIR = ROOT / "results"
MODELS_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

RANDOM_STATE = 42
TEST_SIZE = 0.2

# ── Feature spec ─────────────────────────────────────────────────────────────
_NUMERIC_FEATURES = [
    "rookie_gp", "rookie_mpg", "rookie_fg_pct", "rookie_3p_pct",
    "rookie_ft_pct", "rookie_rpg", "rookie_apg", "rookie_spg",
    "rookie_bpg", "rookie_tpg", "rookie_ppg", "rookie_per",
    "rookie_age", "rookie_team_win_pct",
    "draft_round", "draft_pick", "is_first_round", "is_lottery",
]
_CATEGORIC_FEATURES: list[str] = []


def _build_preprocessor() -> ColumnTransformer:
    transformers = [
        ("num", StandardScaler(), _NUMERIC_FEATURES),
    ]
    if _CATEGORIC_FEATURES:
        transformers.append(("cat", OneHotEncoder(handle_unknown="ignore"), _CATEGORIC_FEATURES))
    return ColumnTransformer(transformers)


def _build_regressor() -> Pipeline:
    return Pipeline([
        ("pre", _build_preprocessor()),
        ("model", GradientBoostingRegressor(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            random_state=RANDOM_STATE,
        )),
    ])


def _build_classifier() -> Pipeline:
    return Pipeline([
        ("pre", _build_preprocessor()),
        ("model", GradientBoostingClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            random_state=RANDOM_STATE,
        )),
    ])


# ── Train / eval ─────────────────────────────────────────────────────────────

def load_training_data() -> pd.DataFrame:
    path = PROCESSED_DIR / "training_data.parquet"
    if not path.exists():
        raise FileNotFoundError(f"training_data.parquet not found at {path}. Run engineer.build_training_data() first.")
    df = pd.read_parquet(path)
    logger.info(f"Loaded training data: {len(df)} rows")
    return df


def train_test_split_df(df: pd.DataFrame, target_col: str):
    """Stratified split when possible (classification), else random."""
    X = df[get_feature_columns()]
    y = df[target_col]
    stratify = y if y.dtype.name == "category" else None
    return train_test_split(X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=stratify)


def train_regression(df: pd.DataFrame) -> dict[str, Any]:
    """Train regressors for all delta targets. Returns metrics dict."""
    targets = {
        "delta_mpg": "delta_mpg",
        "delta_ppg": "delta_ppg",
        "delta_per": "delta_per",
    }
    results: dict[str, Any] = {}
    models: dict[str, Pipeline] = {}

    for name, col in targets.items():
        if col not in df.columns:
            logger.warning(f"Target column {col} missing — skipping")
            continue
        X_train, X_test, y_train, y_test = train_test_split_df(df, col)
        model = _build_regressor()
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        mae = mean_absolute_error(y_test, preds)
        rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
        r2 = float(r2_score(y_test, preds))
        results[name] = {"mae": round(float(mae), 4), "rmse": round(rmse, 4), "r2": round(r2, 4)}
        models[name] = model
        logger.info(f"[{name}] MAE={mae:.4f} RMSE={rmse:.4f} R2={r2:.4f}")

    # Persist models
    for name, model in models.items():
        joblib.dump(model, MODELS_DIR / f"reg_{name}.pkl")
    return results


def train_classification(df: pd.DataFrame) -> dict[str, Any]:
    """Train tier classifier. Returns metrics dict."""
    if "tier" not in df.columns:
        logger.warning("tier column missing — skipping classification")
        return {}
    X_train, X_test, y_train, y_test = train_test_split_df(df, "tier")
    model = _build_classifier()
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    f1 = f1_score(y_test, preds, average="weighted")
    cm = confusion_matrix(y_test, preds, labels=model.classes_).tolist()
    report = classification_report(y_test, preds, output_dict=True)
    results = {
        "accuracy": round(float(acc), 4),
        "f1_weighted": round(float(f1), 4),
        "classes": list(model.classes_),
        "confusion_matrix": cm,
        "classification_report": report,
    }
    joblib.dump(model, MODELS_DIR / "clf_tier.pkl")
    logger.info(f"[tier] accuracy={acc:.4f} f1={f1:.4f}")
    return results


def train_and_evaluate(season: int | None = None) -> dict[str, Any]:
    """Run full training pipeline and return metrics."""
    from src.features.engineer import build_training_data
    df = build_training_data(season=season)
    if df.empty:
        raise ValueError("Empty training data — cannot train models")

    metrics = {
        "regression": train_regression(df),
        "classification": train_classification(df),
        "n_rows": len(df),
        "n_features": len(get_feature_columns()),
    }

    out = RESULTS_DIR / "metrics.json"
    with open(out, "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    logger.info(f"Metrics saved to {out}")
    return metrics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    metrics = train_and_evaluate()
    print(json.dumps(metrics, indent=2))
