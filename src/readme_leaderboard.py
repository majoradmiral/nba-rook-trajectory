"""Inject the preseason rookie leaderboard into the project README.

Rewrites the block between the ``<!-- TOP_PERFORMERS:START -->`` and
``<!-- TOP_PERFORMERS:END -->`` markers with the current top rookies, ranked
by plus/minus per game (team impact). Everything outside the markers is left
untouched.

Usage:
    python -m src.readme_leaderboard
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import pandas as pd

from src.config import ROOT
from src.preseason_db import DB_PATH, load_preseason_rookie_totals

logger = logging.getLogger(__name__)

README_PATH = ROOT / "README.md"
START_MARKER = "<!-- TOP_PERFORMERS:START -->"
END_MARKER = "<!-- TOP_PERFORMERS:END -->"
MIN_GAMES = 3
LIMIT = 10


def build_leaderboard(
    totals: pd.DataFrame,
    min_games: int = MIN_GAMES,
    limit: int = LIMIT,
) -> str:
    """Render the top rookies as a markdown table, ranked by +/- per game."""
    if totals.empty:
        return "_No preseason rookie data yet — run `python -m src.preseason_db`._"

    frame = totals.copy()
    qualified = frame[frame["games_played"] >= min_games]
    if not qualified.empty:
        frame = qualified
    frame["plus_minus_per_game"] = frame["plus_minus"] / frame["games_played"]
    frame = frame.sort_values(
        ["plus_minus_per_game", "points_per_game"],
        ascending=False,
    ).head(limit)

    lines = [
        f"_Updated {pd.Timestamp.today().date()} · ranked by +/- per game · "
        f"min {min_games} games_",
        "",
        "| # | Player | Team | PPG | APG | RPG | +/- |",
        "|---|--------|------|-----|-----|-----|-----|",
    ]
    for rank, row in enumerate(frame.itertuples(index=False), start=1):
        lines.append(
            f"| {rank} | {row.player_name} | {row.team_abbr} | "
            f"{row.points_per_game:.1f} | {row.assists_per_game:.1f} | "
            f"{row.rebounds_per_game:.1f} | {row.plus_minus_per_game:+.1f} |"
        )
    return "\n".join(lines)


def render_section(
    totals: pd.DataFrame,
    min_games: int = MIN_GAMES,
    limit: int = LIMIT,
) -> str:
    """Wrap the leaderboard table in the README markers."""
    body = build_leaderboard(totals, min_games=min_games, limit=limit)
    return f"{START_MARKER}\n{body}\n{END_MARKER}"


def update_readme(
    db_path: str | Path = DB_PATH,
    readme_path: str | Path = README_PATH,
    min_games: int = MIN_GAMES,
    limit: int = LIMIT,
) -> bool:
    """Rewrite the marked README block with fresh leaderboard data."""
    db_path = Path(db_path)
    readme_path = Path(readme_path)
    if not db_path.exists():
        logger.warning("Preseason database not found at %s — README left unchanged", db_path)
        return False

    try:
        totals = load_preseason_rookie_totals(db_path)
    except sqlite3.OperationalError as exc:
        logger.warning("Could not read preseason totals (%s) — README left unchanged", exc)
        return False

    section = render_section(totals, min_games=min_games, limit=limit)
    text = readme_path.read_text(encoding="utf-8")

    if START_MARKER in text and END_MARKER in text:
        before = text.split(START_MARKER, 1)[0]
        after = text.split(END_MARKER, 1)[1]
        updated = f"{before}{section}{after}"
    else:
        updated = f"{text.rstrip()}\n\n## Top Performers\n\n{section}\n"

    readme_path.write_text(updated, encoding="utf-8")
    logger.info("Updated leaderboard in %s", readme_path)
    return True


def main() -> None:
    if update_readme():
        print(f"README leaderboard updated: {README_PATH}")
    else:
        print("README leaderboard not updated (no data available).")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    main()
