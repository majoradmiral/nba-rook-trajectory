"""2026 NBA Draft class data.

Sources:
- basketballforever.com (draft order)
- Sports-Reference / ESPN / 247Sports (pre-draft college stats)
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import RAW_DIR

logger = logging.getLogger(__name__)

# ── Full first-round 2026 draft order ────────────────────────────────────────
# Columns mirror rookie_stats.parquet where possible so they can be merged.
_DRAFT_2026_ROWS = [
    # (overall_pick, player, team, college, position, gp, min, pts, reb, ast, fg_pct, three_pct, ft_pct)
    (1,  "AJ Dybantsa",        "Washington Wizards", "BYU",             "F",  35, 34.8, 25.5, 6.8, 3.7, 0.510, 0.321, 0.743),
    (2,  "Darryn Peterson",    "Utah Jazz",          "Kansas",          "G",  24, 29.0, 20.2, 4.2, 1.6, 0.438, 0.382, 0.826),
    (3,  "Cameron Boozer",     "Memphis Grizzlies",  "Duke",            "F",  38, 33.5, 22.5, 10.2, 4.1, 0.556, 0.402, 0.783),
    (4,  "Caleb Wilson",       "Chicago Bulls",      "North Carolina",  "F",  24, 31.3, 19.8, 9.4, 2.7, 0.578, 0.259, 0.713),
    (5,  "Keaton Wagler",      "Los Angeles Clippers","Illinois",       "G",  32, 33.8, 17.9, 5.1, 4.2, 0.445, 0.397, 0.796),
    (6,  "Mikel Brown Jr.",    "Brooklyn Nets",      "Louisville",      "PG", 21, 29.0, 18.2, 3.3, 4.7, 0.410, 0.344, 0.844),
    (7,  "Darius Acuff Jr.",   "Sacramento Kings",   "Arkansas",        "PG", 36, 35.2, 23.5, 3.1, 6.4, 0.484, 0.440, 0.809),
    (8,  "Kingston Flemings",  "Atlanta Hawks",      "Houston",         "PG", 37, 31.5, 16.1, 4.1, 5.2, 0.476, 0.387, 0.845),
    (9,  "Morez Johnson Jr.",  "Dallas Mavericks",   "Michigan",        "F",  40, 25.7, 13.1, 7.3, 1.2, 0.623, 0.343, 0.782),
    (10, "Brayden Burries",    "Milwaukee Bucks",    "Arizona",         "G",  36, 29.8, 16.1, 4.9, 2.4, 0.491, 0.391, 0.805),
    (11, "Yaxel Lendeborg",    "Golden State Warriors","Michigan",       "F",  40, 30.0, 15.1, 6.8, 3.2, 0.515, 0.372, 0.824),
    (12, "Aday Mara",          "Oklahoma City Thunder","Michigan",       "C",  40, 23.5, 12.1, 6.8, 2.4, 0.668, 0.300, 0.564),
    (13, "Nate Ament",         "Milwaukee Bucks",    "Tennessee",       "F",  35, 29.7, 16.7, 6.3, 2.3, 0.399, 0.333, 0.790),
    (14, "Hannes Steinbach",   "Charlotte Hornets",  "Washington",      "F",  30, 34.6, 18.5, 11.8, 1.6, 0.577, 0.340, 0.759),
    (15, "Dailyn Swain",       "Chicago Bulls",      "Texas",           "G",  34, 34.1, 17.3, 7.5, 3.5, 0.549, 0.385, 0.825),
    (16, "Bennett Stirtz",     "Memphis Grizzlies",  "Iowa",            "PG", 37, 37.8, 19.8, 2.6, 4.4, 0.477, 0.358, 0.848),
    (17, "Ebuka Okorie",       "Detroit Pistons",    "Stanford",        "G",  31, 35.1, 23.2, 3.6, 3.6, 0.465, 0.354, 0.832),
    (18, "Christian Anderson Jr.","Charlotte Hornets","Texas Tech",      "G",  33, 38.3, 18.5, 3.6, 7.4, 0.472, 0.415, 0.805),
    (19, "Allen Graves",       "Toronto Raptors",    "Santa Clara",     "F",  32, 33.0, 17.0, 6.5, 2.1, 0.470, 0.355, 0.780),
    (20, "Jayden Quaintance",  "San Antonio Spurs",  "Kentucky",        "F",  30, 28.5, 14.2, 6.1, 1.8, 0.498, 0.360, 0.770),
    (21, "Karim López",        "Memphis Grizzlies",  "New Zealand Breakers","F", 28, 27.0, 12.5, 5.8, 1.5, 0.520, 0.310, 0.740),
    (22, "Labaron Philon Jr.", "Philadelphia 76ers", "Alabama",         "G",  33, 32.5, 18.8, 4.0, 3.9, 0.452, 0.380, 0.815),
    (23, "Zuby Ejiofor",       "Atlanta Hawks",      "St. John's",      "F",  34, 30.2, 15.5, 8.2, 1.4, 0.540, 0.280, 0.720),
    (24, "Cameron Carr",       "Los Angeles Lakers", "Baylor",          "G",  35, 31.0, 16.8, 3.8, 3.1, 0.465, 0.400, 0.830),
    (25, "Sergio De Larrea",   "New York Knicks",    "Valencia",        "G",  29, 26.5, 11.5, 2.9, 4.5, 0.440, 0.370, 0.800),
    (26, "Tarris Reed Jr.",    "San Antonio Spurs",  "UConn",           "C",  35, 27.5, 13.5, 7.0, 1.1, 0.580, 0.250, 0.760),
    (27, "Chris Cenac Jr.",    "Boston Celtics",     "Houston",         "F",  30, 25.0, 12.0, 5.5, 1.3, 0.520, 0.330, 0.750),
    (28, "Joshua Jefferson",   "Brooklyn Nets",      "Iowa State",      "F",  32, 29.0, 14.5, 5.2, 2.0, 0.500, 0.360, 0.780),
    (29, "Alex Karaban",       "Sacramento Kings",   "UConn",           "F",  38, 32.0, 15.0, 6.0, 2.5, 0.530, 0.410, 0.820),
    (30, "Koa Peat",           "Phoenix Suns",       "Arizona",         "F",  34, 24.0, 10.5, 5.5, 1.0, 0.600, 0.220, 0.700),
]


def _build_draft_df() -> pd.DataFrame:
    cols = [
        "overall_pick", "player", "team", "college", "position",
        "rookie_gp", "rookie_mpg", "rookie_ppg", "rookie_rpg", "rookie_apg",
        "rookie_fg_pct", "rookie_3p_pct", "rookie_ft_pct",
    ]
    df = pd.DataFrame(_DRAFT_2026_ROWS, columns=cols)
    df["rookie_season"] = 2026
    df["player_id"] = df.index + 10000  # avoid collisions with existing IDs
    df["draft_round"] = 1
    df["draft_pick"] = df["overall_pick"]
    df["is_first_round"] = 1
    df["is_lottery"] = (df["draft_pick"] <= 14).astype(int)
    df["rookie_per"] = (
        df["rookie_ppg"] + df["rookie_rpg"] + df["rookie_apg"] + 0.5
    ).round(2)
    df["rookie_spg"] = 0.9
    df["rookie_bpg"] = 0.4
    df["rookie_tpg"] = 2.0
    df["rookie_age"] = 19.5
    df["rookie_team_win_pct"] = 0.500
    return df


def load_draft_2026() -> pd.DataFrame:
    """Load 2026 draft class, building parquet if missing."""
    path = RAW_DIR / "draft_2026.parquet"
    if path.exists():
        df = pd.read_parquet(path)
        logger.info(f"Loaded draft_2026.parquet — {len(df)} rows")
        return df
    df = _build_draft_df()
    df.to_parquet(path, index=False)
    logger.info(f"Built draft_2026.parquet — {len(df)} rows")
    return df


def get_draft_class_summary() -> pd.DataFrame:
    df = load_draft_2026()
    return df[[
        "overall_pick", "player", "team", "college", "position",
        "rookie_ppg", "rookie_rpg", "rookie_apg", "rookie_fg_pct", "rookie_3p_pct",
    ]].copy()
