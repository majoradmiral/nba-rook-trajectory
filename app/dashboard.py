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
from src.features.draft_2026 import load_draft_2026
from src.analysis.over_under import classify_over_under, get_overlooked_players, get_overvalued_players
from src.analysis.play_style import compute_play_style, get_style_summary
from src.analysis.team_comparison import team_comparison

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
def load_inference_2026() -> pd.DataFrame:
    path = PROCESSED_DIR / "inference_2026_draft.parquet"
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

    clf_metrics = metrics.get("classification", {})
    if clf_metrics:
        st.subheader("Classification (tier)")
        acc = clf_metrics.get("accuracy")
        f1 = clf_metrics.get("f1_weighted")
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


def page_draft_2026():
    st.header("2026 Draft Class — Best Overall")
    try:
        draft_df = load_draft_2026()
    except Exception as exc:
        st.error(f"Could not load draft_2026.parquet: {exc}")
        return

    if draft_df.empty:
        st.warning("No 2026 draft data found.")
        return

    st.subheader("Full First Round")
    display_cols = [
        "overall_pick", "player", "team", "college", "position",
        "rookie_ppg", "rookie_rpg", "rookie_apg",
        "rookie_fg_pct", "rookie_3p_pct", "rookie_ft_pct",
    ]
    st.dataframe(draft_df[display_cols], use_container_width=True)

    st.subheader("Top Scoring Prospects")
    top_pts = draft_df.nlargest(10, "rookie_ppg")[
        ["overall_pick", "player", "team", "rookie_ppg", "rookie_rpg", "rookie_apg"]
    ]
    fig_pts = px.bar(top_pts, x="player", y="rookie_ppg", color="team", title="PPG (pre-draft)")
    st.plotly_chart(fig_pts, use_container_width=True)


def page_over_under():
    st.header("Over / Under Performers — 2026 Draft Class")
    try:
        draft_df = load_draft_2026()
    except Exception as exc:
        st.error(f"Could not load draft_2026.parquet: {exc}")
        return

    if draft_df.empty:
        st.warning("No 2026 draft data found.")
        return

    labeled = classify_over_under(draft_df)

    st.subheader("Value Map (pick vs performance score)")
    fig = px.scatter(
        labeled, x="overall_pick", y="performance_score",
        color="value_label", hover_data=["player", "team", "rookie_ppg"],
        color_discrete_map={"undervalued": "#2ecc71", "overvalued": "#e74c3c", "neutral": "#95a5a6"},
    )
    fig.add_hline(y=0, line_dash="dash")
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Undervalued Gems")
        overlooked = get_overlooked_players(labeled)
        if not overlooked.empty:
            st.dataframe(overlooked[["overall_pick", "player", "team", "rookie_ppg", "performance_score"]], use_container_width=True)
        else:
            st.info("No undervalued players found.")

    with col2:
        st.subheader("Overvalued Busts")
        overvalued = get_overvalued_players(labeled)
        if not overvalued.empty:
            st.dataframe(overvalued[["overall_pick", "player", "team", "rookie_ppg", "performance_score"]], use_container_width=True)
        else:
            st.info("No overvalued players found.")


def page_play_style():
    st.header("Play Style Analysis — 2026 Draft Class")
    try:
        draft_df = load_draft_2026()
    except Exception as exc:
        st.error(f"Could not load draft_2026.parquet: {exc}")
        return

    if draft_df.empty:
        st.warning("No 2026 draft data found.")
        return

    styled = compute_play_style(draft_df)

    st.subheader("Style Radar")
    style_cols = [
        "overall_pick", "player", "team", "position",
        "usage_rate", "three_point_tendency", "rim_rate_proxy",
        "assist_ratio", "defensive_activity", "efficiency_index",
    ]
    st.dataframe(styled[style_cols].sort_values("efficiency_index", ascending=False), use_container_width=True)

    st.subheader("Usage vs Efficiency")
    fig = px.scatter(
        styled, x="usage_rate", y="efficiency_index",
        size="rookie_ppg", color="position",
        hover_data=["player", "team", "rookie_ppg"],
    )
    st.plotly_chart(fig, use_container_width=True)


def page_teams():
    st.header("Team Comparison — 2026 Draft Capital")
    try:
        draft_df = load_draft_2026()
    except Exception as exc:
        st.error(f"Could not load draft_2026.parquet: {exc}")
        return

    if draft_df.empty:
        st.warning("No 2026 draft data found.")
        return

    teams = team_comparison(draft_df)
    st.dataframe(teams, use_container_width=True)

    st.subheader("Draft Capital by Team")
    fig = px.bar(teams, x="team", y="draft_capital", color="num_picks", title="Draft Capital (sum of 1/pick)")
    st.plotly_chart(fig, use_container_width=True)


# ── Main ─────────────────────────────────────────────────────────────────────

page = st.sidebar.radio("Navigate", [
    "Overview",
    "Predictions 2025",
    "Metrics",
    "Explorer",
    "Draft 2026",
    "Over/Under Performers",
    "Play Style",
    "Team Comparison",
])
if page == "Overview":
    page_overview()
elif page == "Predictions 2025":
    page_predictions()
elif page == "Metrics":
    page_metrics()
elif page == "Explorer":
    page_explorer()
elif page == "Draft 2026":
    page_draft_2026()
elif page == "Over/Under Performers":
    page_over_under()
elif page == "Play Style":
    page_play_style()
elif page == "Team Comparison":
    page_teams()

