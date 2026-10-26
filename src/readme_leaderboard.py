"""Inject the current rookie leaderboard into the project README.

Rewrites the block between the ``<!-- TOP_PERFORMERS:START -->`` and
``<!-- TOP_PERFORMERS:END -->`` markers with the best-performing rookies,
ranked by a per-game performance score:

    PTS + 1.2*REB + 1.5*AST + 2*STL + 2*BLK - TOV

Regular season and playoff games are used once they exist; preseason totals are
the fallback before opening night. Everything outside the markers is left
untouched.

Usage:
    python -m src.readme_leaderboard              # regular season + playoffs
    python -m src.readme_leaderboard --preseason  # preseason fallback
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

from src.config import ROOT
from src.preseason_db import DB_PATH, load_preseason_rookie_totals

logger = logging.getLogger(__name__)

README_PATH = ROOT / "README.md"
START_MARKER = "<!-- TOP_PERFORMERS:START -->"
END_MARKER = "<!-- TOP_PERFORMERS:END -->"
MIN_GAMES = 3
SEASON_MIN_GAMES = 1
SEASON_MIN_MINUTES = 10.0
LIMIT = 10

SEASON_DB_PATH = ROOT / "data" / "processed" / "nba_season.db"
COMPETITIVE_TYPES = ("regular", "playoffs")

SCORE_NOTE = "performance score"


def _per_game(
    frame: pd.DataFrame,
    total_columns: str | tuple[str, ...],
    per_game_column: str,
) -> pd.Series:
    """Per-game values from a per-game column or a season total."""
    if per_game_column in frame.columns:
        return frame[per_game_column].fillna(0).astype(float)
    totals = (total_columns,) if isinstance(total_columns, str) else total_columns
    for total_column in totals:
        if total_column in frame.columns:
            games = frame["games_played"].replace(0, pd.NA)
            return (frame[total_column] / games).fillna(0).astype(float)
    return pd.Series(0.0, index=frame.index)


def _add_performance_score(frame: pd.DataFrame) -> pd.DataFrame:
    """Attach per-game rates and the score used to rank the table."""
    frame = frame.copy()
    for per_game_column, total_column in (
        ("points_per_game", "total_points"),
        ("rebounds_per_game", "total_rebounds"),
        ("assists_per_game", ("total_assists", "assists")),
        ("steals_per_game", ("total_steals", "steals")),
        ("blocks_per_game", ("total_blocks", "blocks")),
        ("turnovers_per_game", ("total_turnovers", "turnovers")),
    ):
        if per_game_column not in frame.columns:
            frame[per_game_column] = _per_game(frame, total_column, per_game_column)

    if "plus_minus_per_game" not in frame.columns:
        games = frame["games_played"].replace(0, pd.NA)
        frame["plus_minus_per_game"] = (frame["plus_minus"] / games).fillna(0).astype(float)

    frame["performance_score"] = (
        frame["points_per_game"]
        + 1.2 * frame["rebounds_per_game"]
        + 1.5 * frame["assists_per_game"]
        + 2.0 * frame["steals_per_game"]
        + 2.0 * frame["blocks_per_game"]
        - frame["turnovers_per_game"]
    ).round(2)
    return frame


def _format_pct(value: object, attempts: object = None) -> str:
    if value is None or pd.isna(value):
        return "—"
    if attempts is not None and (pd.isna(attempts) or float(attempts) == 0):
        return "—"
    return f"{float(value) * 100:.1f}%"


def _format_signed(value: object) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):+.1f}"


def build_leaderboard(
    totals: pd.DataFrame,
    min_games: int = MIN_GAMES,
    limit: int = LIMIT,
    min_minutes: float = 0.0,
    note: Optional[str] = None,
) -> str:
    """Render the top rookies as a markdown table, ranked by performance score."""
    if totals.empty:
        return "_No rookie data yet — run the season sync or `python -m src.preseason_db`._"

    frame = _add_performance_score(totals)
    qualified = frame[frame["games_played"] >= min_games]
    if min_minutes and "minutes_per_game" in frame.columns:
        qualified = qualified[qualified["minutes_per_game"] >= min_minutes]
    if not qualified.empty:
        frame = qualified
    frame = frame.sort_values(
        ["performance_score", "plus_minus_per_game", "points_per_game"],
        ascending=False,
    ).head(limit)

    qualifier = f"min {min_minutes:g} MPG" if min_minutes else f"min {min_games} games"
    header = f"_Updated {pd.Timestamp.today().date()} · {note + ' · ' if note else ''}" \
             f"ranked by {SCORE_NOTE} · {qualifier}_"
    lines = [
        header,
        "",
        "| # | Player | Team | GP | MPG | PPG | RPG | APG | FG% | 3P% | +/- | Score |",
        "|---|--------|------|----|-----|-----|-----|-----|-----|-----|-----|-------|",
    ]
    for rank, row in enumerate(frame.itertuples(index=False), start=1):
        mpg = getattr(row, "minutes_per_game", None)
        mpg_text = "—" if mpg is None or pd.isna(mpg) else f"{float(mpg):.1f}"
        fg_pct = getattr(row, "field_goal_pct", None)
        fg_att = getattr(row, "field_goals_attempted", None)
        tp_pct = getattr(row, "three_point_pct", None)
        tp_att = getattr(row, "three_pointers_attempted", None)
        lines.append(
            f"| {rank} | {row.player_name} | {row.team_abbr} | "
            f"{int(row.games_played)} | {mpg_text} | "
            f"{row.points_per_game:.1f} | {row.rebounds_per_game:.1f} | "
            f"{row.assists_per_game:.1f} | {_format_pct(fg_pct, fg_att)} | "
            f"{_format_pct(tp_pct, tp_att)} | {_format_signed(row.plus_minus_per_game)} | "
            f"{row.performance_score:.1f} |"
        )
    return "\n".join(lines)


def render_section(
    totals: pd.DataFrame,
    min_games: int = MIN_GAMES,
    limit: int = LIMIT,
    min_minutes: float = 0.0,
    note: Optional[str] = None,
) -> str:
    """Wrap the leaderboard table in the README markers."""
    body = build_leaderboard(
        totals,
        min_games=min_games,
        limit=limit,
        min_minutes=min_minutes,
        note=note,
    )
    return f"{START_MARKER}\n{body}\n{END_MARKER}"


def load_season_totals(
    db_path: str | Path = SEASON_DB_PATH,
    season_types: Iterable[str] = COMPETITIVE_TYPES,
) -> pd.DataFrame:
    """Season totals for rookies from the regular season and playoffs.

    Mirrors the shape of the preseason totals table so the same renderer can
    be reused.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        return pd.DataFrame()

    season_types = tuple(season_types)
    placeholders = ",".join("?" * len(season_types))
    conn = sqlite3.connect(db_path)
    try:
        rows = pd.read_sql_query(
            f"""
            SELECT
                player_id,
                player_name,
                team_abbr,
                MAX(season_year) AS season_year,
                MAX(game_date) AS last_game_date,
                MAX(CASE WHEN season_type = 'playoffs' THEN 1 ELSE 0 END) AS has_playoffs,
                COUNT(DISTINCT game_id) AS games_played,
                SUM(minutes) AS total_minutes,
                SUM(points) AS total_points,
                SUM(rebounds) AS total_rebounds,
                SUM(assists) AS total_assists,
                SUM(steals) AS total_steals,
                SUM(blocks) AS total_blocks,
                SUM(turnovers) AS total_turnovers,
                SUM(field_goals_made) AS field_goals_made,
                SUM(field_goals_attempted) AS field_goals_attempted,
                SUM(three_pointers_made) AS three_pointers_made,
                SUM(three_pointers_attempted) AS three_pointers_attempted,
                SUM(plus_minus) AS plus_minus
            FROM season_player_stats
            WHERE is_rookie = 1
              AND season_type IN ({placeholders})
            GROUP BY player_id
            """,
            conn,
            params=list(season_types),
        )
    except sqlite3.OperationalError as exc:
        logger.warning("Could not read season totals (%s)", exc)
        return pd.DataFrame()
    finally:
        conn.close()

    if rows.empty:
        return rows

    games = rows["games_played"].replace(0, pd.NA)
    rows["minutes_per_game"] = (rows["total_minutes"] / games).fillna(0).astype(float)
    rows["points_per_game"] = (rows["total_points"] / games).fillna(0).astype(float)
    rows["rebounds_per_game"] = (rows["total_rebounds"] / games).fillna(0).astype(float)
    rows["assists_per_game"] = (rows["total_assists"] / games).fillna(0).astype(float)
    rows["steals_per_game"] = (rows["total_steals"] / games).fillna(0).astype(float)
    rows["blocks_per_game"] = (rows["total_blocks"] / games).fillna(0).astype(float)
    rows["turnovers_per_game"] = (rows["total_turnovers"] / games).fillna(0).astype(float)
    rows["plus_minus_per_game"] = (rows["plus_minus"] / games).fillna(0).astype(float)
    rows["field_goal_pct"] = [
        made / attempted if attempted else float("nan")
        for made, attempted in zip(rows["field_goals_made"], rows["field_goals_attempted"])
    ]
    rows["three_point_pct"] = [
        made / attempted if attempted else float("nan")
        for made, attempted in zip(
            rows["three_pointers_made"], rows["three_pointers_attempted"]
        )
    ]
    return rows


def _write_section(readme_path: Path, section: str) -> None:
    """Replace the marked block (or append it) inside the README."""
    text = readme_path.read_text(encoding="utf-8")
    if START_MARKER in text and END_MARKER in text:
        before = text.split(START_MARKER, 1)[0]
        after = text.split(END_MARKER, 1)[1]
        updated = f"{before}{section}{after}"
    else:
        updated = f"{text.rstrip()}\n\n## Top Performers\n\n{section}\n"
    readme_path.write_text(updated, encoding="utf-8")


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

    note = None
    if not totals.empty and "season_year" in totals.columns:
        year = int(totals["season_year"].max())
        note = f"{year - 1}-{str(year)[-2:]} preseason"
    section = render_section(totals, min_games=min_games, limit=limit, note=note)
    _write_section(readme_path, section)
    logger.info("Updated leaderboard in %s", readme_path)
    return True


def _season_note(totals: pd.DataFrame) -> str:
    """Human-readable phase/date stamp for the README header."""
    season_year = int(totals["season_year"].max())
    label = f"{season_year - 1}-{str(season_year)[-2:]}"
    through = str(totals["last_game_date"].max())
    playoffs = int(totals["has_playoffs"].max()) == 1
    phase = "regular season + playoffs" if playoffs else "regular season"
    return f"{label} {phase} through {through}"


def update_readme_from_season(
    db_path: str | Path = SEASON_DB_PATH,
    readme_path: str | Path = README_PATH,
    min_games: int = SEASON_MIN_GAMES,
    limit: int = LIMIT,
    min_minutes: float = SEASON_MIN_MINUTES,
) -> bool:
    """Rewrite the README block from regular season + playoff rookie data."""
    totals = load_season_totals(db_path)
    if totals.empty:
        logger.warning("No regular-season rookie data in %s — README left unchanged", db_path)
        return False

    section = render_section(
        totals,
        min_games=min_games,
        limit=limit,
        min_minutes=min_minutes,
        note=_season_note(totals),
    )
    _write_section(Path(readme_path), section)
    logger.info("Updated season leaderboard in %s", readme_path)
    return True


def main(argv: Optional[Iterable[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Refresh the README leaderboard.")
    parser.add_argument(
        "--preseason",
        action="store_true",
        help="Use preseason data instead of the regular season + playoffs.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    updated = update_readme() if args.preseason else update_readme_from_season()
    if updated:
        print(f"README leaderboard updated: {README_PATH}")
    else:
        print("README leaderboard not updated (no data available).")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    main()
