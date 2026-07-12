"""ESPN public API client for live NBA scores, game results, and Summer League data.

Uses ESPN's undocumented (but public) REST endpoints that power their frontend.
"""

import logging
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
