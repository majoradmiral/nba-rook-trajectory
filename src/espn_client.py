"""ESPN public API client for live NBA scores, game results, and Summer League data.

Uses ESPN's undocumented (but public) REST endpoints that power their frontend.
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from typing import Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball"

SL_DATE_RANGE = (date(2026, 7, 3), date(2026, 7, 19))

SL_LEAGUES = {
    "California Classic": "nba-summer-california",
    "Salt Lake City SL": "nba-summer-utah",
    "Las Vegas SL": "nba-summer-las-vegas",
}

NBA_TEAM_ABBR_MAP = {
    "ATLANTA": "ATL", "BOSTON": "BOS", "BROOKLYN": "BKN", "CHARLOTTE": "CHA",
    "CHICAGO": "CHI", "CLEVELAND": "CLE", "DALLAS": "DAL", "DENVER": "DEN",
    "DETROIT": "DET", "GOLDEN STATE": "GSW", "HOUSTON": "HOU", "INDIANA": "IND",
    "LA CLIPPERS": "LAC", "LA LAKERS": "LAL", "MEMPHIS": "MEM", "MIAMI": "MIA",
    "MILWAUKEE": "MIL", "MINNESOTA": "MIN", "NEW ORLEANS": "NOP", "NEW YORK": "NYK",
    "OKLAHOMA CITY": "OKC", "ORLANDO": "ORL", "PHILADELPHIA": "PHI", "PHOENIX": "PHX",
    "PORTLAND": "POR", "SACRAMENTO": "SAC", "SAN ANTONIO": "SAS", "TORONTO": "TOR",
    "UTAH": "UTA", "WASHINGTON": "WAS",
}


def _team_abbr(full_name: str) -> str:
    clean = full_name.strip().upper()
    for long_name, abbr in NBA_TEAM_ABBR_MAP.items():
        if long_name in clean or clean.startswith(long_name):
            return abbr
    parts = clean.split()
    return parts[-1] if parts else clean[:3]


def fetch_scoreboard(
    league: str = "nba",
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> pd.DataFrame:
    """Fetch scoreboard data from ESPN for a date range.

    Parameters
    ----------
    league : str
        League path (``nba`` for regular season, ``nba-summer-league`` for SL).
    date_from, date_to : date, optional
        Date range. Defaults to today.

    Returns
    -------
    DataFrame with columns: game_id, game_date, home_team, away_team,
    home_score, away_score, status, period.
    """
    if date_from is None:
        date_from = date.today()
    if date_to is None:
        date_to = date_from

    date_param = f"{date_from.strftime('%Y%m%d')}-{date_to.strftime('%Y%m%d')}"
    url = f"{BASE_URL}/{league}/scoreboard"
    params = {"dates": date_param}

    logger.info(f"Fetching ESPN scoreboard: {url}?dates={date_param}")
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"ESPN scoreboard fetch failed: {e}")
        return pd.DataFrame()

    events = data.get("events", [])
    if not events:
        logger.info(f"No events found for {date_param}")
        return pd.DataFrame()

    rows = []
    for ev in events:
        edate = ev.get("date", "")[:10]
        comps = ev.get("competitions", [])
        for comp in comps:
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue
            teams = {}
            for c in competitors:
                is_home = c.get("homeAway") == "home"
                team_name = c["team"].get("displayName", c["team"].get("abbreviation", ""))
                score = c.get("score", "0")
                teams["home" if is_home else "away"] = {
                    "name": team_name,
                    "abbr": c["team"].get("abbreviation", _team_abbr(team_name)),
                    "score": int(float(score)) if score and score != "" else 0,
                    "logo": c["team"].get("logo", ""),
                }
            if "home" not in teams or "away" not in teams:
                continue

            status = comp.get("status", {})
            state = status.get("type", {}).get("state", "")
            detail = status.get("type", {}).get("detail", "")
            period = status.get("period", 0)

            rows.append({
                "game_id": comp.get("id", ev.get("id", "")),
                "game_date": edate,
                "home_team": teams["home"]["name"],
                "home_abbr": teams["home"]["abbr"],
                "home_score": teams["home"]["score"],
                "home_logo": teams["home"]["logo"],
                "away_team": teams["away"]["name"],
                "away_abbr": teams["away"]["abbr"],
                "away_score": teams["away"]["score"],
                "away_logo": teams["away"]["logo"],
                "status": state,
                "detail": detail,
                "period": period,
            })

    df = pd.DataFrame(rows)
    if not df.empty:
        df["game_date"] = pd.to_datetime(df["game_date"]).dt.date
    logger.info(f"Fetched {len(df)} games from ESPN")
    return df


def fetch_summer_league_games(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> pd.DataFrame:
    """Fetch Summer League game results from all known ESPN SL endpoints.

    Tries each Summer League venue (California Classic, Utah, Las Vegas)
    and aggregates results.
    """
    if date_from is None:
        date_from = SL_DATE_RANGE[0]
    if date_to is None:
        date_to = SL_DATE_RANGE[1]

    all_frames = []
    for event_name, league_path in SL_LEAGUES.items():
        df = fetch_scoreboard(league_path, date_from, date_to)
        if not df.empty:
            df["sl_event"] = event_name
            all_frames.append(df)

    if all_frames:
        combined = pd.concat(all_frames, ignore_index=True)
        combined = combined.drop_duplicates("game_id")
        return combined

    return pd.DataFrame()


def fetch_recent_summer_league_results(days_back: int = 7) -> pd.DataFrame:
    """Fetch SL game results from today going backwards."""
    today = date.today()
    from_date = today - timedelta(days=days_back)
    df = fetch_summer_league_games(from_date, today)
    if df.empty:
        return df
    return df.sort_values("game_date", ascending=False).reset_index(drop=True)


_PRESEASON_GAME_COLUMNS = [
    "game_id", "season_year", "game_date",
    "home_team_id", "home_team", "home_abbr", "home_score",
    "away_team_id", "away_team", "away_abbr", "away_score",
    "status", "detail", "source",
]

_ROOKIE_BOXSCORE_COLUMNS = [
    "game_id", "season_year", "game_date", "player_id", "player_name",
    "team_id", "team_name", "team_abbr", "position", "starter",
    "minutes", "points", "field_goals_made", "field_goals_attempted",
    "three_pointers_made", "three_pointers_attempted",
    "free_throws_made", "free_throws_attempted", "rebounds",
    "assists", "turnovers", "steals", "blocks", "offensive_rebounds",
    "defensive_rebounds", "personal_fouls", "plus_minus",
]


def default_nba_season_year(today: date) -> int:
    """Return the NBA season's end year (e.g. 2027 for 2026-27)."""
    return today.year + 1 if today.month >= 7 else today.year


def _scoreboard_rows_for_day(day: date, season_year: int) -> list[dict]:
    url = f"{BASE_URL}/nba/scoreboard"
    response = requests.get(
        url,
        params={
            "dates": day.strftime("%Y%m%d"),
            "seasontype": 1,
            "season": season_year,
        },
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    rows = []

    for event in data.get("events", []):
        for competition in event.get("competitions", []):
            status = competition.get("status", {}).get("type", {})
            if not status.get("completed") and status.get("state") != "post":
                continue

            teams = {}
            for competitor in competition.get("competitors", []):
                side = competitor.get("homeAway")
                team = competitor.get("team", {})
                name = team.get("displayName") or team.get("name") or ""
                if side not in {"home", "away"} or not name:
                    continue
                teams[side] = {
                    "id": team.get("id"),
                    "name": name,
                    "abbr": team.get("abbreviation", ""),
                    "score": int(float(competitor.get("score", 0) or 0)),
                }

            if "home" not in teams or "away" not in teams:
                continue

            rows.append({
                "game_id": str(competition.get("id") or event.get("id", "")),
                "season_year": season_year,
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
                "detail": status.get("detail", ""),
                "source": "espn_scoreboard",
            })
    return rows


def fetch_nba_preseason_games(
    season_year: int | None = None,
    today: date | None = None,
) -> pd.DataFrame:
    """Fetch completed NBA preseason games for one season from ESPN."""
    today = today or date.today()
    season_year = season_year or default_nba_season_year(today)
    first_day = date(season_year - 1, 10, 1)
    last_day = min(date(season_year - 1, 10, 31), today)
    if last_day < first_day:
        return pd.DataFrame(columns=_PRESEASON_GAME_COLUMNS)

    days = [first_day + timedelta(days=offset) for offset in range((last_day - first_day).days + 1)]
    with ThreadPoolExecutor(max_workers=6) as executor:
        day_rows = executor.map(
            lambda day: _scoreboard_rows_for_day(day, season_year),
            days,
        )

    rows_by_game = {
        row["game_id"]: row
        for rows in day_rows
        for row in rows
    }
    games = pd.DataFrame(rows_by_game.values(), columns=_PRESEASON_GAME_COLUMNS)
    if not games.empty:
        games["game_date"] = pd.to_datetime(games["game_date"]).dt.date
        games = games.sort_values(["game_date", "game_id"]).reset_index(drop=True)
    logger.info("Fetched %d completed %d preseason games from ESPN", len(games), season_year)
    return games


def fetch_nba_rookie_roster(season_year: int) -> pd.DataFrame:
    """Return ESPN roster entries with zero prior NBA seasons for the season."""
    teams_url = f"{BASE_URL}/nba/teams"
    response = requests.get(teams_url, params={"limit": 100}, timeout=20)
    response.raise_for_status()
    data = response.json()
    teams = data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
    if not teams:
        raise ValueError("ESPN returned no NBA teams while loading preseason rookie rosters")

    def load_team_rookies(team_entry: dict) -> list[dict]:
        team = team_entry.get("team", team_entry)
        team_id = str(team.get("id", ""))
        if not team_id:
            return []
        roster_response = requests.get(
            f"{BASE_URL}/nba/teams/{team_id}/roster",
            params={"season": season_year},
            timeout=20,
        )
        roster_response.raise_for_status()
        roster_data = roster_response.json()
        rookies = []
        for athlete in roster_data.get("athletes", []):
            experience = athlete.get("experience", {}).get("years")
            if experience not in (0, "0"):
                continue
            rookies.append({
                "player_id": str(athlete.get("id", "")),
                "player_name": athlete.get("displayName", ""),
                "team_id": team_id,
                "team_name": team.get("displayName", ""),
                "position": athlete.get("position", {}).get("abbreviation", ""),
                "experience_years": 0,
            })
        return [rookie for rookie in rookies if rookie["player_id"]]

    with ThreadPoolExecutor(max_workers=6) as executor:
        roster_rows = executor.map(load_team_rookies, teams)
    rookies = pd.DataFrame(
        [row for team_rows in roster_rows for row in team_rows],
        columns=[
            "player_id", "player_name", "team_id", "team_name",
            "position", "experience_years",
        ],
    )
    if rookies.empty:
        raise ValueError(f"ESPN returned no zero-experience NBA players for season {season_year}")
    rookies = rookies.drop_duplicates("player_id").reset_index(drop=True)
    logger.info("Identified %d first-year NBA players for season %d", len(rookies), season_year)
    return rookies


def _parse_stat_number(value: object) -> float:
    if value is None or value == "" or value == "--":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _parse_minutes(value: object) -> float:
    text = str(value or "").strip()
    if ":" in text:
        minutes, seconds = text.split(":", maxsplit=1)
        try:
            return int(minutes) + int(seconds) / 60
        except ValueError:
            return 0.0
    return _parse_stat_number(text)


def _parse_made_attempted(value: object) -> tuple[int, int]:
    parts = str(value or "").split("-", maxsplit=1)
    if len(parts) != 2:
        return 0, 0
    return int(_parse_stat_number(parts[0])), int(_parse_stat_number(parts[1]))


def _summary_rookie_rows(
    game: dict,
    summary: dict,
    rookie_ids: set[str],
) -> list[dict]:
    rows = []
    for team_group in summary.get("boxscore", {}).get("players", []):
        team = team_group.get("team", {})
        for stat_group in team_group.get("statistics", []):
            labels = stat_group.get("labels") or stat_group.get("names") or []
            keys = stat_group.get("keys", [])
            for player in stat_group.get("athletes", []):
                athlete = player.get("athlete", {})
                player_id = str(athlete.get("id", ""))
                if player_id not in rookie_ids or player.get("didNotPlay"):
                    continue

                values = player.get("stats", [])
                stat_values = dict(zip(labels, values))
                stat_values.update(dict(zip(keys, values)))

                def stat(label: str, key: str) -> object:
                    return stat_values.get(label, stat_values.get(key, 0))

                fgm, fga = _parse_made_attempted(
                    stat("FG", "fieldGoalsMade-fieldGoalsAttempted")
                )
                three_pm, three_pa = _parse_made_attempted(
                    stat("3PT", "threePointFieldGoalsMade-threePointFieldGoalsAttempted")
                )
                ftm, fta = _parse_made_attempted(
                    stat("FT", "freeThrowsMade-freeThrowsAttempted")
                )
                rows.append({
                    "game_id": str(game["game_id"]),
                    "season_year": int(game["season_year"]),
                    "game_date": game["game_date"].isoformat()
                    if hasattr(game["game_date"], "isoformat") else str(game["game_date"]),
                    "player_id": player_id,
                    "player_name": athlete.get("displayName", ""),
                    "team_id": str(team.get("id", "")),
                    "team_name": team.get("displayName", ""),
                    "team_abbr": team.get("abbreviation", ""),
                    "position": athlete.get("position", {}).get("abbreviation", ""),
                    "starter": int(bool(player.get("starter", False))),
                    "minutes": _parse_minutes(stat("MIN", "minutes")),
                    "points": int(_parse_stat_number(stat("PTS", "points"))),
                    "field_goals_made": fgm,
                    "field_goals_attempted": fga,
                    "three_pointers_made": three_pm,
                    "three_pointers_attempted": three_pa,
                    "free_throws_made": ftm,
                    "free_throws_attempted": fta,
                    "rebounds": int(_parse_stat_number(stat("REB", "rebounds"))),
                    "assists": int(_parse_stat_number(stat("AST", "assists"))),
                    "turnovers": int(_parse_stat_number(stat("TO", "turnovers"))),
                    "steals": int(_parse_stat_number(stat("STL", "steals"))),
                    "blocks": int(_parse_stat_number(stat("BLK", "blocks"))),
                    "offensive_rebounds": int(_parse_stat_number(stat("OREB", "offensiveRebounds"))),
                    "defensive_rebounds": int(_parse_stat_number(stat("DREB", "defensiveRebounds"))),
                    "personal_fouls": int(_parse_stat_number(stat("PF", "fouls"))),
                    "plus_minus": int(_parse_stat_number(stat("+/-", "plusMinus"))),
                })
    return rows


def fetch_nba_preseason_rookie_stats(
    games: pd.DataFrame,
    rookie_roster: pd.DataFrame,
) -> pd.DataFrame:
    """Fetch per-game box scores for roster-identified rookies only."""
    if games.empty or rookie_roster.empty:
        return pd.DataFrame(columns=_ROOKIE_BOXSCORE_COLUMNS)
    rookie_ids = set(rookie_roster["player_id"].astype(str))

    def fetch_summary(game: dict) -> list[dict]:
        response = requests.get(
            f"{BASE_URL}/nba/summary",
            params={"event": str(game["game_id"])},
            timeout=30,
        )
        response.raise_for_status()
        return _summary_rookie_rows(game, response.json(), rookie_ids)

    game_records = games.to_dict(orient="records")
    with ThreadPoolExecutor(max_workers=6) as executor:
        stat_rows = executor.map(fetch_summary, game_records)
    stats = pd.DataFrame(
        [row for game_rows in stat_rows for row in game_rows],
        columns=_ROOKIE_BOXSCORE_COLUMNS,
    )
    if not stats.empty:
        stats = stats.drop_duplicates(["game_id", "player_id"]).sort_values(
            ["game_date", "player_name", "game_id"]
        ).reset_index(drop=True)
    logger.info("Fetched %d rookie player-game box-score rows", len(stats))
    return stats
