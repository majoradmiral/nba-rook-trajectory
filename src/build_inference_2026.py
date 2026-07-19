"""Build 2026 draft inference frame.

Usage:
    python -m src.build_inference_2026
"""

from __future__ import annotations

import logging

from src.config import PROCESSED_DIR
from src.pipeline import build_inference_2026_draft

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

if __name__ == "__main__":
    df = build_inference_2026_draft()
    if not df.empty:
        print(f"Built 2026 inference: {len(df)} players")
        print(df[["overall_pick", "player", "team", "rookie_ppg"]].to_string(index=False))
        print(f"\nSaved to: {PROCESSED_DIR / 'inference_2026_draft.parquet'}")
    else:
        print("No data built.")
