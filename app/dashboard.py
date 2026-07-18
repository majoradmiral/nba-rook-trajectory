"""Streamlit dashboard — NBA Rookie Trajectory Explorer.

Run with:
    streamlit run app/dashboard.py
"""

import json
import logging
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import PROCESSED_DIR, RAW_DIR, ROOT

logger = logging.getLogger(__name__)

st.set_page_config(page_title="NBA Rookie Trajectory", layout="wide")

# ── Helpers ──────────────────────────────────────────────────────────────────

@st.cache_data
def load_inference() -> pd.DataFrame:
    path = PROCESSED_DIR / "inference_2025_rookies.parquet"
    if path.exists():
        return pd.read_parquet(path)
    return pd.DataFrame()


@st.cache_data
def load_training() -> pd.DataFrame:
    path = PROCESSED_DIR / "training_data.parquet"
    if path.exists():
        return pd.read_parquet(path)
    return pd.DataFrame()


@st.cache_data
def load_metrics() -> dict:
    path = ROOT / "results" / "metrics.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def load_model(name: str):
    try:
        import joblib
        return joblib.load(ROOT / "models" / f"{name}.pkl")
    except Exception:
        return None


# ── Pages ─────────────────────────────────────────────────────────────────────

def page_overview():
    st.header("Project Overview")
    st.markdown("""
    **Goal:** Predict second-year NBA rookie trajectory (efficiency jump, minutes jump, tier classification)
    using rookie-year stats combined with Summer League performance.

    **Tasks:**
    - Regression: `delta_mpg`, `delta_ppg`, `delta_per`
    - Classification: `tier` ∈ {breakout, bust, neutral}
    """)

    train_df = load_training()
    if not train_df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Training rows", len(train_df))
        seasons = train_df.get("rookie_season", pd.Series(dtype=int))
        c2.metric("Seasons", int(seasons.nunique()) if not seasons.empty else 0)
        tiers = train_df.get("tier", pd.Series())
        breakout_rate = float((tiers == "breakout").mean()) if not tiers.empty else 0.0
        c3.metric("Breakout rate", f"{breakout_rate:.1%}")


def page_predictions():
    st.header("2025 Rookie Predictions")
    infer = load_inference()
    if infer.empty:
        st.warning("No inference data found. Run `python -m src.update_sl` first.")
        return

    clf = load_model("clf_tier")
    reg_mpg = load_model("reg_delta_mpg")
    reg_ppg = load_model("reg_delta_ppg")

    feature_cols = [
        "rookie_gp", "rookie_mpg", "rookie_fg_pct", "rookie_3p_pct",
        "rookie_ft_pct", "rookie_rpg", "rookie_apg", "rookie_spg",
        "rookie_bpg", "rookie_tpg", "rookie_ppg", "rookie_per",
        "rookie_age", "rookie_team_win_pct",
        "draft_round", "draft_pick", "is_first_round", "is_lottery",
    ]
    available = [c for c in feature_cols if c in infer.columns]
    X = infer[available].fillna(0)

    results = infer[["player_name"]].copy()
    if clf:
        results["predicted_tier"] = clf.predict(X)
    if reg_mpg is not None:
        results["pred_delta_mpg"] = reg_mpg.predict(X)
    if reg_ppg is not None:
        results["pred_delta_ppg"] = reg_ppg.predict(X)

    st.dataframe(results, use_container_width=True)
    st.download_button("Download predictions CSV", results.to_csv(index=False), "predictions_2025.csv")


def page_metrics():
    st.header("Model Performance")
    metrics = load_metrics()
    if not metrics:
        st.warning("No metrics found. Run `python train_eval.py` first.")
        return

    reg = metrics.get("regression", {})
    if reg:
        st.subheader("Regression")
        reg_df = pd.DataFrame(reg).T
        st.dataframe(reg_df, use_container_width=True)

    if clf:
        st.subheader("Classification (tier)")
        acc = clf.get("accuracy")
        f1 = clf.get("f1_weighted")
        c1, c2 = st.columns(2)
        c1.metric("Accuracy", f"{acc:.4f}" if acc is not None else "N/A")
        c2.metric("F1 (weighted)", f"{f1:.4f}" if f1 is not None else "N/A")


def page_explorer():
    st.header("Training Data Explorer")
    df = load_training()
    if df.empty:
        st.warning("No training data found.")
        return

    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    col_x = st.selectbox("X axis", numeric_cols, index=numeric_cols.index("rookie_ppg") if "rookie_ppg" in numeric_cols else 0)
    col_y = st.selectbox("Y axis", numeric_cols, index=numeric_cols.index("delta_ppg") if "delta_ppg" in numeric_cols else 1)
    color_col = st.selectbox("Color by", ["tier", "rookie_season", "dataset"], index=0)

    fig = px.scatter(df, x=col_x, y=col_y, color=color_col, hover_data=["player_name"])
    st.plotly_chart(fig, use_container_width=True)


# ── Main ─────────────────────────────────────────────────────────────────────

page = st.sidebar.radio("Navigate", ["Overview", "Predictions 2025", "Metrics", "Explorer"])
if page == "Overview":
    page_overview()
elif page == "Predictions 2025":
    page_predictions()
elif page == "Metrics":
    page_metrics()
elif page == "Explorer":
    page_explorer()
