"""End-to-end training and evaluation entry point.

Usage:
    python train_eval.py                # full pipeline
    python train_eval.py --season 2024  # single season only
"""

from __future__ import annotations

import argparse
import logging
import sys

from src.config import PROCESSED_DIR
from src.features.engineer import build_training_data
from src.models.train import train_and_evaluate


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="NBA-Rook training pipeline")
    p.add_argument("--season", type=int, default=None, help="Restrict training to one rookie season")
    p.add_argument("--skip-build", action="store_true", help="Skip feature engineering (use existing parquet)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

    if not args.skip_build:
        logging.info("Step 1/2: building training data")
        df = build_training_data(season=args.season)
        if df.empty:
            logging.error("Training data is empty — aborting")
            return 1
    else:
        logging.info("Skipping feature engineering")

    logging.info("Step 2/2: training models")
    metrics = train_and_evaluate(season=args.season)
    print("\n=== Final Metrics ===")
    for task, vals in metrics.items():
        if isinstance(vals, dict):
            print(f"\n{task}:")
            for k, v in vals.items():
                print(f"  {k}: {v}")
        else:
            print(f"{task}: {vals}")

    out = PROCESSED_DIR / "inference_2025_rookies.parquet"
    print(f"\nInference frame: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
