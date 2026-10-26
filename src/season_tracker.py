"""Season-wide NBA ingestion: games, box scores, and shot charts from ESPN.

Covers every phase of a season — preseason (type 1), regular season (type 2),
and playoffs (type 3) — so the weekly timeline page can be rebuilt from a local
database without touching the network.

Storage lives in ``data/processed/nba_season.db``:

    season_games          one row per completed game
    season_player_stats   one row per player per game (all players)
    season_shots          one row per shot attempt with court coordinates
    season_fetch_log      days already pulled from the ESPN scoreboard

Usage:
    python -m src.season_tracker
    python -m src.season_tracker --days 45
"""

from __future__ import annotations

import argparse
import logging
import math
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd
import requests

from src.config import PROCESSED_DIR
from src.espn_client import (
    BASE_URL,
    _parse_made_attempted,
    _parse_minutes,
    _parse_stat_number,
    default_nba_season_year,
)

logger = logging.getLogger(__name__)

DB_PATH = PROCESSED_DIR / "nba_season.db"

SEASON_TYPES = {1: "preseason", 2: "regular", 3: "playoffs"}

# ESPN shot coordinates: x spans the 50 ft width of the court (25 = centre
# line of the floor), y is the depth in feet from the baseline of the basket
# being attacked. Free throws carry a sentinel coordinate and are skipped.
SENTINEL_LIMIT = 1000
COURT_HALF_WIDTH = 25.0
RIM_OFFSET = 1.575  # rim centre sits 1.575 ft inside the baseline

_DISTANCE_RE = re.compile(r"(\d+)-foot")
_THREE_RE = re.compile(r"three[- ]?(?:point|pointer|pt)|3PT", re.IGNORECASE)
_SHOT_TYPES = (
    ("dunk", "dunk"),
    ("alley-oop", "alley-oop"),
    ("putback", "putback"),
    ("layup", "layup"),
    ("hook", "hook shot"),
    ("floater", "floater"),
    ("floating", "floater"),
    ("finger roll", "finger roll"),
    ("tip", "tip-in"),
    ("fadeaway", "fadeaway"),
    ("bank", "bank shot"),
    ("jump shot", "jump shot"),
    ("jumper", "jumper"),
)

PLAYER_STAT_COLUMNS = [
    "game_id", "season_year", "season_type", "game_date",
    "player_id", "player_name", "team_id", "team_abbr", "position",
    "starter", "minutes", "points", "field_goals_made", "field_goals_attempted",
    "three_pointers_made", "three_pointers_attempted",
    "free_throws_made", "free_throws_attempted", "rebounds", "assists",
    "turnovers", "steals", "blocks", "offensive_rebounds", "defensive_rebounds",
    "personal_fouls", "plus_minus", "is_rookie",
]

SHOT_COLUMNS = [
    "game_id", "season_year", "season_type", "game_date",
    "player_id", "player_name", "team_abbr",
    "court_x", "court_y", "made", "is_three", "distance",
    "shot_type", "period", "clock", "description",
]


# ── Database ──────────────────────────────────────────────────────────────────

def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create the season tables if they do not exist yet."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS season_games (
            game_id TEXT PRIMARY KEY,
            season_year INTEGER NOT NULL,
            season_type TEXT NOT NULL,
            game_date TEXT NOT NULL,
            home_team_id TEXT,
            home_team TEXT,
            home_abbr TEXT,
            home_score INTEGER,
            away_team_id TEXT,
            away_team TEXT,
            away_abbr TEXT,
            away_score INTEGER,
            status TEXT,
            source TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS season_player_stats (
            game_id TEXT NOT NULL,
            season_year INTEGER NOT NULL,
            season_type TEXT NOT NULL,
            game_date TEXT NOT NULL,
            player_id TEXT NOT NULL,
            player_name TEXT NOT NULL,
            team_id TEXT,
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
            is_rookie INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (game_id, player_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS season_shots (
            game_id TEXT NOT NULL,
            season_year INTEGER NOT NULL,
            season_type TEXT NOT NULL,
            game_date TEXT NOT NULL,
            player_id TEXT NOT NULL,
            player_name TEXT NOT NULL,
            team_abbr TEXT,
            court_x REAL NOT NULL,
            court_y REAL NOT NULL,
            made INTEGER NOT NULL,
            is_three INTEGER NOT NULL,
            distance REAL NOT NULL,
            shot_type TEXT,
            period INTEGER,
            clock TEXT,
            description TEXT,
            PRIMARY KEY (game_id, player_id, period, clock, description)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS season_fetch_log (
            game_date TEXT PRIMARY KEY,
            season_year INTEGER NOT NULL,
            games_found INTEGER NOT NULL DEFAULT 0,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _connect(db_path: str | Path = DB_PATH) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    ensure_schema(conn)
    return conn


# ── ESPN fetching ────────────────────────────────────────────────────────────

def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    return session


def fetch_completed_games_for_day(
    day: date,
    season_year: int,
    session: Optional[requests.Session] = None,
) -> list[dict]:
    """Return completed games played on ``day`` as plain dicts."""
    session = session or _session()
    response = session.get(
        f"{BASE_URL}/nba/scoreboard",
        params={"dates": day.strftime("%Y%m%d"), "season": season_year},
        timeout=25,
    )
    response.raise_for_status()
    payload = response.json()

    games: list[dict] = []
    for event in payload.get("events", []):
        for competition in event.get("competitions", []):
            status = competition.get("status", {}).get("type", {})
            if not status.get("completed") and status.get("state") != "post":
                continue

            season_meta = event.get("season", {}) or {}
            season_type_id = int(season_meta.get("type", 0) or 0)
            season_type = SEASON_TYPES.get(season_type_id, "unknown")

            teams: dict[str, dict] = {}
            for competitor in competition.get("competitors", []):
                side = competitor.get("homeAway")
                team = competitor.get("team", {})
                name = team.get("displayName") or team.get("name") or ""
                if side not in {"home", "away"} or not name:
                    continue
                teams[side] = {
                    "id": str(team.get("id", "")),
                    "name": name,
                    "abbr": team.get("abbreviation", ""),
                    "score": int(_parse_stat_number(competitor.get("score", 0))),
                }
            if "home" not in teams or "away" not in teams:
                continue

            games.append(
                {
                    "game_id": str(competition.get("id") or event.get("id", "")),
                    "season_year": int(season_meta.get("year", season_year)),
                    "season_type": season_type,
                    "game_date": day.isoformat(),
                    "home_team_id": teams["home"]["id"],
                    "home_team": teams["home"]["name"],
                    "home_abbr": teams["home"]["abbr"],
                    "home_score": teams["home"]["score"],
                    "away_team_id": teams["away"]["id"],
                    "away_team": teams["away"]["name"],
                    "away_abbr": teams["away"]["abbr"],
                    "away_score": teams["away"]["score"],
                    "status": status.get("state", ""),
                    "source": "espn_scoreboard",
                }
            )
    return games


def fetch_season_games(
    start: date,
    end: date,
    season_year: int,
    session: Optional[requests.Session] = None,
) -> list[dict]:
    """Fetch every completed game between ``start`` and ``end`` (inclusive)."""
    session = session or _session()
    days = [start + timedelta(days=offset) for offset in range((end - start).days + 1)]

    def safe_day(day: date) -> list[dict]:
        try:
            return fetch_completed_games_for_day(day, season_year, session=session)
        except Exception as exc:  # network hiccups should not kill the run
            logger.warning("Scoreboard fetch failed for %s: %s", day, exc)
            return []

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(safe_day, days))

    games: dict[str, dict] = {}
    for game_rows in results:
        for game in game_rows:
            games.setdefault(game["game_id"], game)
    ordered = sorted(games.values(), key=lambda g: (g["game_date"], g["game_id"]))
    logger.info("Fetched %d completed games between %s and %s", len(ordered), start, end)
    return ordered


# ── Shot + box-score parsing ─────────────────────────────────────────────────

def is_three_pointer(description: str) -> bool:
    """True when ESPN's play text describes a three-point attempt."""
    return bool(_THREE_RE.search(description or ""))


def parse_reported_distance(description: str) -> Optional[float]:
    """Extract the shot distance ESPN reports (e.g. ``24-foot`` → 24.0)."""
    match = _DISTANCE_RE.search(description or "")
    if not match:
        return None
    return float(match.group(1))


def parse_shot_type(description: str) -> str:
    """Normalise the shot type out of ESPN's play text."""
    text = (description or "").lower()
    for needle, label in _SHOT_TYPES:
        if needle in text:
            return label
    return "shot"


def court_coordinates(coordinate: dict) -> Optional[tuple[float, float]]:
    """Convert an ESPN coordinate into rim-centred court feet.

    Returns ``None`` for free throws and other non-located plays, which ESPN
    reports with a sentinel coordinate.
    """
    if not isinstance(coordinate, dict):
        return None
    x = coordinate.get("x")
    y = coordinate.get("y")
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        return None
    if abs(x) > SENTINEL_LIMIT or abs(y) > SENTINEL_LIMIT:
        return None
    return round(float(x) - COURT_HALF_WIDTH, 2), round(float(y), 2)


def _box_score_rows(summary: dict, game: dict, rookie_ids: set[str]) -> list[dict]:
    rows: list[dict] = []
    for team_group in summary.get("boxscore", {}).get("players", []):
        team = team_group.get("team", {})
        team_id = str(team.get("id", ""))
        team_abbr = team.get("abbreviation", "")
        for stat_group in team_group.get("statistics", []):
            labels = stat_group.get("labels") or stat_group.get("names") or []
            keys = stat_group.get("keys", [])
            for player in stat_group.get("athletes", []):
                athlete = player.get("athlete", {})
                player_id = str(athlete.get("id", ""))
                if not player_id:
                    continue

                values = player.get("stats", [])
                stat_values = dict(zip(labels, values))
                stat_values.update(dict(zip(keys, values)))

                def stat(label: str, key: str) -> object:
                    return stat_values.get(label, stat_values.get(key, 0))

                fgm, fga = _parse_made_attempted(stat("FG", "fieldGoalsMade-fieldGoalsAttempted"))
                tpm, tpa = _parse_made_attempted(
                    stat("3PT", "threePointFieldGoalsMade-threePointFieldGoalsAttempted")
                )
                ftm, fta = _parse_made_attempted(
                    stat("FT", "freeThrowsMade-freeThrowsAttempted")
                )
                rows.append(
                    {
                        "game_id": game["game_id"],
                        "season_year": game["season_year"],
                        "season_type": game["season_type"],
                        "game_date": game["game_date"],
                        "player_id": player_id,
                        "player_name": athlete.get("displayName", ""),
                        "team_id": team_id,
                        "team_abbr": team_abbr,
                        "position": athlete.get("position", {}).get("abbreviation", ""),
                        "starter": int(bool(player.get("starter", False))),
                        "minutes": _parse_minutes(stat("MIN", "minutes")),
                        "points": int(_parse_stat_number(stat("PTS", "points"))),
                        "field_goals_made": fgm,
                        "field_goals_attempted": fga,
                        "three_pointers_made": tpm,
                        "three_pointers_attempted": tpa,
                        "free_throws_made": ftm,
                        "free_throws_attempted": fta,
                        "rebounds": int(_parse_stat_number(stat("REB", "rebounds"))),
                        "assists": int(_parse_stat_number(stat("AST", "assists"))),
                        "turnovers": int(_parse_stat_number(stat("TO", "turnovers"))),
                        "steals": int(_parse_stat_number(stat("STL", "steals"))),
                        "blocks": int(_parse_stat_number(stat("BLK", "blocks"))),
                        "offensive_rebounds": int(
                            _parse_stat_number(stat("OREB", "offensiveRebounds"))
                        ),
                        "defensive_rebounds": int(
                            _parse_stat_number(stat("DREB", "defensiveRebounds"))
                        ),
                        "personal_fouls": int(_parse_stat_number(stat("PF", "fouls"))),
                        "plus_minus": int(_parse_stat_number(stat("+/-", "plusMinus"))),
                        "is_rookie": int(player_id in rookie_ids),
                    }
                )
    return rows


def _shot_rows(summary: dict, game: dict, names: dict[str, str]) -> list[dict]:
    rows: list[dict] = []
    for play in summary.get("plays", []):
        if not play.get("shootingPlay"):
            continue
        description = str(play.get("text", ""))
        position = court_coordinates(play.get("coordinate") or {})
        if position is None:
            continue

        participants = play.get("participants") or []
        if not participants:
            continue
        shooter_id = str(participants[0].get("athlete", {}).get("id", ""))
        if not shooter_id:
            continue

        court_x, court_y = position
        distance = round(math.hypot(court_x, court_y - RIM_OFFSET), 2)
        period = (play.get("period") or {}).get("number")
        clock = (play.get("clock") or {}).get("displayValue", "")
        rows.append(
            {
                "game_id": game["game_id"],
                "season_year": game["season_year"],
                "season_type": game["season_type"],
                "game_date": game["game_date"],
                "player_id": shooter_id,
                "player_name": names.get(shooter_id, ""),
                "team_abbr": "",
                "court_x": court_x,
                "court_y": court_y,
                "made": int(bool(play.get("scoringPlay"))),
                "is_three": int(is_three_pointer(description)),
                "distance": distance,
                "shot_type": parse_shot_type(description),
                "period": period,
                "clock": clock,
                "description": description,
            }
        )
    return rows


def fetch_game_details(
    game: dict,
    rookie_ids: set[str],
    session: Optional[requests.Session] = None,
) -> tuple[list[dict], list[dict]]:
    """Fetch one game's box score and shot chart from the ESPN summary feed."""
    session = session or _session()
    response = session.get(
        f"{BASE_URL}/nba/summary",
        params={"event": str(game["game_id"])},
        timeout=30,
    )
    response.raise_for_status()
    summary = response.json()

    player_rows = _box_score_rows(summary, game, rookie_ids)
    names = {row["player_id"]: row["player_name"] for row in player_rows}
    teams = {row["player_id"]: row["team_abbr"] for row in player_rows}
    shot_rows = _shot_rows(summary, game, names)
    for row in shot_rows:
        row["team_abbr"] = teams.get(row["player_id"], "")
    return player_rows, shot_rows


# ── Sync ─────────────────────────────────────────────────────────────────────

def _known_rookie_ids(conn: sqlite3.Connection, season_year: int) -> set[str]:
    """Rookie ids already flagged in the database for this season."""
    rows = conn.execute(
        "SELECT DISTINCT player_id FROM season_player_stats "
        "WHERE season_year = ? AND is_rookie = 1",
        (season_year,),
    ).fetchall()
    return {str(row[0]) for row in rows}


def _rookie_ids(season_year: int, conn: Optional[sqlite3.Connection] = None) -> set[str]:
    """First-year player ids for the season, falling back to the local database."""
    known = _known_rookie_ids(conn, season_year) if conn is not None else set()
    try:
        from src.espn_client import fetch_nba_rookie_roster

        roster = fetch_nba_rookie_roster(season_year)
        return known | set(roster["player_id"].astype(str))
    except Exception as exc:
        logger.warning(
            "Could not load rookie roster (%s) — using %d previously flagged rookies",
            exc,
            len(known),
        )
        return known


def _refresh_rookie_flags(
    conn: sqlite3.Connection,
    season_year: int,
    rookie_ids: set[str],
) -> None:
    """Re-apply rookie flags after an ingest (new rows default to zero)."""
    if not rookie_ids:
        return
    placeholders = ",".join("?" * len(rookie_ids))
    conn.execute(
        f"""
        UPDATE season_player_stats
        SET is_rookie = CASE
            WHEN player_id IN ({placeholders}) THEN 1
            ELSE 0
        END
        WHERE season_year = ?
        """,
        (*sorted(rookie_ids), season_year),
    )


def sync_season(
    season_year: Optional[int] = None,
    start: Optional[date] = None,
    end: Optional[date] = None,
    db_path: str | Path = DB_PATH,
    force_days: bool = False,
) -> dict:
    """Pull completed games (and their details) into the season database.

    Days that were already fetched are skipped, so a weekly run only pays for
    the games that are new (plus the current day, which is always re-checked).
    """
    today = date.today()
    season_year = season_year or default_nba_season_year(today)
    start = start or date(season_year - 1, 10, 1)
    end = min(end or today, today)

    conn = _connect(db_path)
    try:
        with conn:
            logged = {
                row[0]
                for row in conn.execute("SELECT game_date FROM season_fetch_log").fetchall()
            }

            today_iso = today.isoformat()
            todo_days = []
            for offset in range((end - start).days + 1):
                day = start + timedelta(days=offset)
                day_iso = day.isoformat()
                # Today is always re-checked so games that finished late are not
                # missed; earlier days are only fetched once.
                if force_days or day_iso not in logged or day_iso == today_iso:
                    todo_days.append(day)

            session = _session()
            games: list[dict] = []
            for day in todo_days:
                try:
                    rows = fetch_completed_games_for_day(day, season_year, session=session)
                except Exception as exc:
                    # Leave the day unlogged so the next run picks it up again.
                    logger.warning("Scoreboard fetch failed for %s: %s", day, exc)
                    continue
                games.extend(rows)
                conn.execute(
                    """
                    INSERT INTO season_fetch_log (game_date, season_year, games_found)
                    VALUES (?, ?, ?)
                    ON CONFLICT(game_date) DO UPDATE SET
                        games_found = excluded.games_found,
                        fetched_at = CURRENT_TIMESTAMP
                    """,
                    (day.isoformat(), season_year, len(rows)),
                )

            if games:
                game_ids = [game["game_id"] for game in games]
                placeholders = ",".join("?" * len(game_ids))
                for table in ("season_games", "season_player_stats", "season_shots"):
                    conn.execute(
                        f"DELETE FROM {table} WHERE game_id IN ({placeholders})",
                        game_ids,
                    )
                pd.DataFrame(games).to_sql("season_games", conn, if_exists="append", index=False)

            # Rows for every game in the batch were just cleared, so their
            # details are re-fetched (a batch is only as big as the days that
            # were not already logged).
            to_fetch = list(games)
            rookie_ids = _rookie_ids(season_year, conn)

            def details(game: dict) -> tuple[list[dict], list[dict]]:
                try:
                    return fetch_game_details(game, rookie_ids, session=session)
                except Exception as exc:
                    logger.warning("Summary fetch failed for %s: %s", game["game_id"], exc)
                    return [], []

            if to_fetch:
                with ThreadPoolExecutor(max_workers=8) as executor:
                    detail_rows = list(executor.map(details, to_fetch))

                player_rows = [row for pair in detail_rows for row in pair[0]]
                shot_rows = [row for pair in detail_rows for row in pair[1]]
                if player_rows:
                    pd.DataFrame(player_rows, columns=PLAYER_STAT_COLUMNS).to_sql(
                        "season_player_stats", conn, if_exists="append", index=False
                    )
                if shot_rows:
                    pd.DataFrame(shot_rows, columns=SHOT_COLUMNS).to_sql(
                        "season_shots", conn, if_exists="append", index=False
                    )

            _refresh_rookie_flags(conn, season_year, rookie_ids)

        summary = season_summary(db_path=db_path)
        logger.info(
            "Synced %s: %d games, %d player-games, %d shots",
            season_year,
            summary["games"],
            summary["player_games"],
            summary["shots"],
        )
        return summary
    finally:
        conn.close()


def season_summary(db_path: str | Path = DB_PATH) -> dict:
    """Counts used for the pipeline log line and the page footer."""
    conn = sqlite3.connect(db_path)
    try:
        games = conn.execute("SELECT COUNT(*) FROM season_games").fetchone()[0]
        player_games = conn.execute("SELECT COUNT(*) FROM season_player_stats").fetchone()[0]
        shots = conn.execute("SELECT COUNT(*) FROM season_shots").fetchone()[0]
        types = dict(
            conn.execute(
                "SELECT season_type, COUNT(*) FROM season_games GROUP BY season_type"
            ).fetchall()
        )
        return {
            "games": games,
            "player_games": player_games,
            "shots": shots,
            "games_by_type": types,
        }
    finally:
        conn.close()


# ── Loaders ──────────────────────────────────────────────────────────────────

def load_games(db_path: str | Path = DB_PATH) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    try:
        return pd.read_sql_query(
            "SELECT * FROM season_games ORDER BY game_date, game_id", conn
        )
    finally:
        conn.close()


def load_player_stats(db_path: str | Path = DB_PATH) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    try:
        return pd.read_sql_query(
            "SELECT * FROM season_player_stats ORDER BY game_date, player_name", conn
        )
    finally:
        conn.close()


def load_shots(db_path: str | Path = DB_PATH) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    try:
        return pd.read_sql_query(
            "SELECT * FROM season_shots ORDER BY game_date, player_name", conn
        )
    finally:
        conn.close()


def main(argv: Optional[Iterable[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Sync NBA season data from ESPN.")
    parser.add_argument("--season", type=int, default=None, help="Season end year (e.g. 2027).")
    parser.add_argument("--days", type=int, default=None, help="Only sync the last N days.")
    parser.add_argument("--force", action="store_true", help="Re-fetch days already in the log.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    today = date.today()
    season_year = args.season or default_nba_season_year(today)
    start = date(season_year - 1, 10, 1)
    if args.days:
        start = max(start, today - timedelta(days=args.days - 1))

    summary = sync_season(
        season_year=season_year,
        start=start,
        end=today,
        force_days=args.force,
    )
    print(f"Season {season_year}: {summary['games']} games tracked")
    for season_type, count in sorted(summary["games_by_type"].items()):
        print(f"  {season_type}: {count}")
    print(f"  player-game rows: {summary['player_games']}")
    print(f"  shots recorded:    {summary['shots']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    main()
