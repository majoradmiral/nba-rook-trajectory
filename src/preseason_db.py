"""SQLite storage and summaries for NBA preseason rookie box scores."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import pandas as pd

from src.config import PROCESSED_DIR
from src.espn_client import (
    default_nba_season_year,
    fetch_nba_preseason_games,
    fetch_nba_preseason_rookie_stats,
    fetch_nba_rookie_roster,
)

logger = logging.getLogger(__name__)
DB_PATH = PROCESSED_DIR / "nba_preseason.db"

def ensure_preseason_tables(conn: sqlite3.Connection) -> None:
    """Create rookie-only tables, removing the earlier team-summary table."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS preseason_games (
            game_id TEXT PRIMARY KEY,
            season_year INTEGER NOT NULL,
            game_date TEXT NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_score INTEGER NOT NULL,
            away_score INTEGER NOT NULL,
            winner TEXT,
            status TEXT NOT NULL,
            detail TEXT,
            source TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS preseason_rookie_game_stats (
            game_id TEXT NOT NULL,
            season_year INTEGER NOT NULL,
            game_date TEXT NOT NULL,
            player_id TEXT NOT NULL,
            player_name TEXT NOT NULL,
            team_id TEXT,
            team_name TEXT,
            team_abbr TEXT,
            position TEXT,
            starter INTEGER NOT NULL,
            minutes REAL NOT NULL,
            points INTEGER NOT NULL,
            field_goals_made INTEGER NOT NULL,
            field_goals_attempted INTEGER NOT NULL,
            three_pointers_made INTEGER NOT NULL,
            three_pointers_attempted INTEGER NOT NULL,
            free_throws_made INTEGER NOT NULL,
            free_throws_attempted INTEGER NOT NULL,
            rebounds INTEGER NOT NULL,
            assists INTEGER NOT NULL,
            turnovers INTEGER NOT NULL,
            steals INTEGER NOT NULL,
            blocks INTEGER NOT NULL,
            offensive_rebounds INTEGER NOT NULL,
            defensive_rebounds INTEGER NOT NULL,
            personal_fouls INTEGER NOT NULL,
            plus_minus INTEGER NOT NULL,
            PRIMARY KEY (game_id, player_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS preseason_rookie_totals (
            season_year INTEGER NOT NULL,
            player_id TEXT NOT NULL,
            player_name TEXT NOT NULL,
            team_id TEXT,
            team_name TEXT,
            team_abbr TEXT,
            position TEXT,
            games_played INTEGER NOT NULL,
            starts INTEGER NOT NULL,
            total_minutes REAL NOT NULL,
            minutes_per_game REAL NOT NULL,
            total_points INTEGER NOT NULL,
            points_per_game REAL NOT NULL,
            field_goals_made INTEGER NOT NULL,
            field_goals_attempted INTEGER NOT NULL,
            field_goal_pct REAL,
            three_pointers_made INTEGER NOT NULL,
            three_pointers_attempted INTEGER NOT NULL,
            three_point_pct REAL,
            free_throws_made INTEGER NOT NULL,
            free_throws_attempted INTEGER NOT NULL,
            free_throw_pct REAL,
            total_rebounds INTEGER NOT NULL,
            rebounds_per_game REAL NOT NULL,
            assists INTEGER NOT NULL,
            assists_per_game REAL NOT NULL,
            turnovers INTEGER NOT NULL,
            steals INTEGER NOT NULL,
            blocks INTEGER NOT NULL,
            offensive_rebounds INTEGER NOT NULL,
            defensive_rebounds INTEGER NOT NULL,
            personal_fouls INTEGER NOT NULL,
            plus_minus INTEGER NOT NULL,
            PRIMARY KEY (season_year, player_id)
        )
        """
    )
    conn.execute("DROP TABLE IF EXISTS preseason_team_totals")


def build_preseason_rookie_totals(stats: pd.DataFrame) -> pd.DataFrame:
    """Aggregate player-game rows into season totals and per-game rates."""
    if stats.empty:
        return pd.DataFrame()

    totals = stats.groupby(
        ["season_year", "player_id", "player_name"],
        as_index=False,
        sort=True,
    ).agg(
        team_id=("team_id", "last"),
        team_name=("team_name", "last"),
        team_abbr=("team_abbr", "last"),
        position=("position", "last"),
        games_played=("game_id", "nunique"),
        starts=("starter", "sum"),
        total_minutes=("minutes", "sum"),
        total_points=("points", "sum"),
        field_goals_made=("field_goals_made", "sum"),
        field_goals_attempted=("field_goals_attempted", "sum"),
        three_pointers_made=("three_pointers_made", "sum"),
        three_pointers_attempted=("three_pointers_attempted", "sum"),
        free_throws_made=("free_throws_made", "sum"),
        free_throws_attempted=("free_throws_attempted", "sum"),
        total_rebounds=("rebounds", "sum"),
        assists=("assists", "sum"),
        turnovers=("turnovers", "sum"),
        steals=("steals", "sum"),
        blocks=("blocks", "sum"),
        offensive_rebounds=("offensive_rebounds", "sum"),
        defensive_rebounds=("defensive_rebounds", "sum"),
        personal_fouls=("personal_fouls", "sum"),
        plus_minus=("plus_minus", "sum"),
    )

    totals["minutes_per_game"] = totals["total_minutes"] / totals["games_played"]
    totals["points_per_game"] = totals["total_points"] / totals["games_played"]
    totals["rebounds_per_game"] = totals["total_rebounds"] / totals["games_played"]
    totals["assists_per_game"] = totals["assists"] / totals["games_played"]
    totals["field_goal_pct"] = (
        totals["field_goals_made"]
        / totals["field_goals_attempted"].replace(0, float("nan"))
    )
    totals["three_point_pct"] = (
        totals["three_pointers_made"]
        / totals["three_pointers_attempted"].replace(0, float("nan"))
    )
    totals["free_throw_pct"] = (
        totals["free_throws_made"]
        / totals["free_throws_attempted"].replace(0, float("nan"))
    )
    return totals[
        [
            "season_year", "player_id", "player_name", "team_id", "team_name",
            "team_abbr", "position", "games_played", "starts", "total_minutes",
            "minutes_per_game", "total_points", "points_per_game",
            "field_goals_made", "field_goals_attempted", "field_goal_pct",
            "three_pointers_made", "three_pointers_attempted", "three_point_pct",
            "free_throws_made", "free_throws_attempted", "free_throw_pct",
            "total_rebounds", "rebounds_per_game", "assists", "assists_per_game",
            "turnovers", "steals", "blocks", "offensive_rebounds",
            "defensive_rebounds", "personal_fouls", "plus_minus",
        ]
    ]


def _game_rows_for_database(games: pd.DataFrame) -> pd.DataFrame:
    rows = games[
        [
            "game_id", "season_year", "game_date", "home_team", "away_team",
            "home_score", "away_score", "status", "detail", "source",
        ]
    ].copy()
    rows["game_id"] = rows["game_id"].astype(str)
    rows["game_date"] = rows["game_date"].astype(str)
    rows["winner"] = rows.apply(
        lambda row: (
            row["home_team"] if row["home_score"] > row["away_score"]
            else row["away_team"] if row["away_score"] > row["home_score"]
            else "tie"
        ),
        axis=1,
    )
    return rows[
        [
            "game_id", "season_year", "game_date", "home_team", "away_team",
            "home_score", "away_score", "winner", "status", "detail", "source",
        ]
    ]


def _replace_season_data(
    conn: sqlite3.Connection,
    season_year: int,
    games: pd.DataFrame,
    stats: pd.DataFrame,
    totals: pd.DataFrame,
) -> None:
    game_rows = _game_rows_for_database(games)
    conn.execute("DELETE FROM preseason_games WHERE season_year = ?", (season_year,))
    conn.execute(
        "DELETE FROM preseason_rookie_game_stats WHERE season_year = ?",
        (season_year,),
    )
    conn.execute(
        "DELETE FROM preseason_rookie_totals WHERE season_year = ?",
        (season_year,),
    )
    game_rows.to_sql("preseason_games", conn, if_exists="append", index=False)
    stats.to_sql("preseason_rookie_game_stats", conn, if_exists="append", index=False)
    totals.to_sql("preseason_rookie_totals", conn, if_exists="append", index=False)


def load_preseason_rookie_stats(db_path: str | Path = DB_PATH) -> pd.DataFrame:
    """Read per-game box scores for rookies only."""
    conn = sqlite3.connect(db_path)
    try:
        return pd.read_sql_query(
            """
            SELECT * FROM preseason_rookie_game_stats
            ORDER BY game_date, player_name, game_id
            """,
            conn,
        )
    finally:
        conn.close()


def load_preseason_rookie_totals(db_path: str | Path = DB_PATH) -> pd.DataFrame:
    """Read aggregated preseason stats for rookies only."""
    conn = sqlite3.connect(db_path)
    try:
        return pd.read_sql_query(
            """
            SELECT * FROM preseason_rookie_totals
            ORDER BY total_points DESC, player_name
            """,
            conn,
        )
    finally:
        conn.close()


def sync_preseason_data(
    db_path: str | Path = DB_PATH,
    season_year: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch, persist, and return completed preseason game lines for rookies."""
    season_year = season_year or default_nba_season_year(pd.Timestamp.today().date())
    games = fetch_nba_preseason_games(season_year)
    if games.empty:
        raise RuntimeError(f"No completed NBA preseason games found for season {season_year}")

    rookie_roster = fetch_nba_rookie_roster(season_year)
    stats = fetch_nba_preseason_rookie_stats(games, rookie_roster)
    if stats.empty:
        raise RuntimeError(
            f"No rookie box-score lines found in {len(games)} completed games "
            f"for season {season_year}"
        )
    totals = build_preseason_rookie_totals(stats)

    conn = sqlite3.connect(db_path)
    try:
        ensure_preseason_tables(conn)
        with conn:
            _replace_season_data(conn, season_year, games, stats, totals)
    finally:
        conn.close()

    logger.info(
        "Stored %d completed games, %d rookie game lines, %d rookies in %s",
        len(games),
        len(stats),
        len(totals),
        db_path,
    )
    return stats, totals


def main() -> None:
    stats, totals = sync_preseason_data()
    print(f"Rookie player-game rows: {len(stats)}")
    print(f"Unique rookies with stats: {stats['player_id'].nunique()}")
    print(f"Completed preseason games: {stats['game_id'].nunique()}")
    print("\nPreseason rookie leaders by total points:")
    columns = [
        "player_name", "team_abbr", "games_played", "minutes_per_game",
        "points_per_game", "total_points", "total_rebounds", "assists",
        "field_goal_pct", "three_point_pct", "free_throw_pct",
    ]
    print(
        totals.sort_values("total_points", ascending=False)[columns]
        .head(25)
        .to_string(index=False)
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    main()
