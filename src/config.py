"""Central config — paths, schedule, constants."""

from datetime import date, datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# ── Time ───────────────────────────────────────
CURRENT_YEAR = datetime.now().year

# ── 2026 Summer League schedule (source: nba.com) ──
SL_2026_SCHEDULE = [
    {"event": "California Classic", "start": "2026-07-03", "end": "2026-07-06"},
    {"event": "Salt Lake City SL",  "start": "2026-07-04", "end": "2026-07-07"},
    {"event": "Las Vegas SL",       "start": "2026-07-09", "end": "2026-07-19"},
]

SL_2026_DAILY = {
    "California Classic": [
        "2026-07-03", "2026-07-04", "2026-07-05", "2026-07-06",
    ],
    "Salt Lake City SL": [
        "2026-07-04", "2026-07-05", "2026-07-06", "2026-07-07",
    ],
    "Las Vegas SL": [
        "2026-07-09", "2026-07-10", "2026-07-11", "2026-07-12",
        "2026-07-13", "2026-07-14", "2026-07-15", "2026-07-16",
        "2026-07-17", "2026-07-18", "2026-07-19",
    ],
}
