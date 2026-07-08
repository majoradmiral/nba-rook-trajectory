"""NBA Summer League scraper.

Data sources tried (in order):
  1. stats.nba.com `leaguegamelog` + box scores — works for past seasons
  2. nba.com/summer-league/ HTML page — data is JS-rendered, no server-side tables
  3. cdn.nba.com/static/json/summerLeague/ — 403 (protected CDN)
  4. ESPN stats page — JS-rendered, no server-side tables
  5. Basketball-Reference — blocks scraping (403/429)
  6. RealGM — blocks scraping (403)

Fallback: manual CSV import via `load_csv()`.
"""

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

CURRENT_YEAR = datetime.now().year


def _fetch_box_scores(game_ids: list) -> pd.DataFrame:
    """Fetch box scores for a list of game IDs using V3 (fallback V2)."""
    all_players = []
    for gid in sorted(game_ids)[:60]:
        df = None
        try:
            from nba_api.stats.endpoints import boxscoretraditionalv3
            box = boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=gid)
            v3 = box.get_data_frames()[0]
            rename_v3 = {
                "personId": "PLAYER_ID",
                "firstName": "first_name",
                "familyName": "family_name",
                "minutes": "MIN",
                "fieldGoalsMade": "FGM",
                "fieldGoalsAttempted": "FGA",
                "fieldGoalsPercentage": "FG_PCT",
                "threePointersMade": "FG3M",
                "threePointersAttempted": "FG3A",
                "threePointersPercentage": "FG3_PCT",
                "freeThrowsMade": "FTM",
                "freeThrowsAttempted": "FTA",
                "freeThrowsPercentage": "FT_PCT",
                "reboundsOffensive": "OREB",
                "reboundsDefensive": "DREB",
                "reboundsTotal": "REB",
                "assists": "AST",
                "steals": "STL",
                "blocks": "BLK",
                "turnovers": "TOV",
                "foulsPersonal": "PF",
                "points": "PTS",
                "plusMinusPoints": "PLUS_MINUS",
            }
            avail = {k: v for k, v in rename_v3.items() if k in v3.columns}
            v3 = v3.rename(columns=avail)
            v3["PLAYER_NAME"] = v3["first_name"] + " " + v3["family_name"]
            df = v3[[c for c in rename_v3.values() if c in v3.columns] + ["PLAYER_NAME"]]
        except Exception:
            pass
        if df is None or df.empty:
            try:
                from nba_api.stats.endpoints import boxscoretraditionalv2
                box = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=gid)
                df = box.get_data_frames()[0]
            except Exception:
                continue
        if df is not None and not df.empty:
            df["_game_id"] = gid
            all_players.append(df)
    if not all_players:
        return pd.DataFrame()
    return pd.concat(all_players, ignore_index=True)


def scrape_from_nba_api(year: int = CURRENT_YEAR) -> pd.DataFrame:
    """Find SL games via leaguegamelog date filter, aggregate box scores."""
    from nba_api.stats.endpoints import leaguegamelog

    season_str = f"{year}-{str(year + 1)[2:]}"
    game_ids = set()

    for stype in ["Regular Season"]:
        for df, dt in [(f"{year}-07-01", f"{year}-07-20"),
                        (f"{year}-07-05", f"{year}-07-25")]:
            try:
                gl = leaguegamelog.LeagueGameLog(
                    league_id="00",
                    season=season_str,
                    season_type_all_star=stype,
                    date_from_nullable=df,
                    date_to_nullable=dt,
                )
                gdf = gl.get_data_frames()[0]
                for gid in gdf["GAME_ID"].unique():
                    game_ids.add(gid)
            except Exception:
                continue

    if not game_ids:
        return pd.DataFrame()

    logger.info(f"Found {len(game_ids)} SL games via NBA API")

    full = _fetch_box_scores(sorted(game_ids))
    if full.empty:
        return pd.DataFrame()
    return _aggregate_box_scores(full, year)


def _aggregate_box_scores(full: pd.DataFrame, year: int) -> pd.DataFrame:
    """Aggregate per-player stats from box score data."""
    def parse_min(m):
        if pd.isna(m) or m == "" or m is None:
            return 0.0
        m = str(m)
        if ":" in m:
            parts = m.split(":")
            try:
                return int(parts[0]) + int(parts[1]) / 60.0
            except (ValueError, IndexError):
                return 0.0
        try:
            return float(m)
        except ValueError:
            return 0.0

    if "MIN" in full.columns:
        full["_MIN"] = full["MIN"].apply(parse_min)
    else:
        full["_MIN"] = 0.0

    agg_cols = {
        "_MIN": "sum",
        "FGM": "sum", "FGA": "sum",
        "FG3M": "sum", "FG3A": "sum",
        "FTM": "sum", "FTA": "sum",
        "OREB": "sum", "DREB": "sum",
        "REB": "sum", "AST": "sum",
        "STL": "sum", "BLK": "sum",
        "TOV": "sum", "PTS": "sum",
        "PLUS_MINUS": "sum",
    }
    existing_agg = {k: v for k, v in agg_cols.items() if k in full.columns}

    gp_count = full.groupby("PLAYER_ID").size().rename("GP")
    grouped = full.groupby("PLAYER_ID", as_index=False).agg(existing_agg)
    grouped = grouped.merge(gp_count, on="PLAYER_ID")
    grouped = grouped.rename(columns={"_MIN": "MIN"})

    gp = grouped["GP"].clip(lower=1)
    for col in ["MIN", "PTS", "REB", "AST", "STL", "BLK", "TOV", "FGM", "FGA",
                "FG3M", "FG3A", "FTM", "FTA"]:
        if col in grouped.columns:
            grouped[col] = grouped[col] / gp

    if "FGM" in grouped.columns and "FGA" in grouped.columns:
        grouped["FG_PCT"] = grouped["FGM"] / grouped["FGA"].clip(lower=1)
    if "FG3M" in grouped.columns and "FG3A" in grouped.columns:
        grouped["FG3_PCT"] = grouped["FG3M"] / grouped["FG3A"].clip(lower=1)
    if "FTM" in grouped.columns and "FTA" in grouped.columns:
        grouped["FT_PCT"] = grouped["FTM"] / grouped["FTA"].clip(lower=1)

    name_map = full[["PLAYER_ID", "PLAYER_NAME"]].drop_duplicates("PLAYER_ID")
    grouped = grouped.merge(name_map, on="PLAYER_ID", how="left")

    grouped["sl_year"] = year
    grouped["source"] = "nba_api"
    return grouped


def load_csv(path: str = "data/raw/summer_league.csv") -> pd.DataFrame:
    """Load Summer League stats from a manually curated CSV.

    Expected columns: PLAYER_NAME, GP, MIN, PTS, REB, AST, FG_PCT, 3P_PCT, FT_PCT
    (case-insensitive).
    """
    path = Path(path)
    if not path.exists():
        logger.warning(f"CSV not found: {path}")
        return pd.DataFrame()

    df = pd.read_csv(path)
    cols = {c.upper(): c for c in df.columns}
    rename = {}
    for src, dst in [("PLAYER_NAME", "PLAYER_NAME"), ("PLAYER", "PLAYER_NAME"),
                     ("GP", "GP"), ("MIN", "MIN"), ("PTS", "PTS"),
                     ("REB", "REB"), ("AST", "AST"), ("FG_PCT", "FG_PCT"),
                     ("3P_PCT", "3P_PCT"), ("FT_PCT", "FT_PCT")]:
        if src in cols:
            rename[cols[src]] = dst
    df = df.rename(columns=rename)
    df["sl_year"] = CURRENT_YEAR
    df["source"] = "csv"
    logger.info(f"Loaded {len(df)} rows from CSV")
    return df


def fetch_from_cdn(year: int = CURRENT_YEAR) -> pd.DataFrame:
    """Try the NBA CDN endpoint for Summer League player stats."""
    url = f"https://cdn.nba.com/static/json/summerLeague/sl_players.json"
    try:
        r = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.nba.com/summer-league/',
            'Accept': 'application/json',
        }, timeout=10)
        if r.status_code != 200:
            logger.warning(f"CDN returned {r.status_code}")
            return pd.DataFrame()
        data = r.json()
        players = data.get("players", data.get("resultSets", []))
        if isinstance(players, list) and players:
            df = pd.DataFrame(players)
            df["sl_year"] = year
            df["source"] = "cdn"
            logger.info(f"CDN returned {len(df)} players")
            return df
        # Try nested structure
        for key in data:
            if isinstance(data[key], list) and len(data[key]) > 0:
                df = pd.DataFrame(data[key])
                df["sl_year"] = year
                df["source"] = "cdn"
                logger.info(f"CDN returned {len(df)} players (key={key})")
                return df
    except Exception as e:
        logger.warning(f"CDN fetch failed: {e}")
    return pd.DataFrame()


def scrape_summer_league(year: int = CURRENT_YEAR) -> pd.DataFrame:
    """Main entry: scrape Summer League stats from best available source."""
    logger.info(f"Scraping Summer League {year}")

    # 1. Try NBA API (game log + box scores)
    df = scrape_from_nba_api(year)
    if not df.empty:
        return df

    # 2. Try CDN endpoint (may be blocked locally, works on GitHub Actions)
    df = fetch_from_cdn(year)
    if not df.empty:
        return df

    # 3. Try Playwright/ZenRows fallback if available
    try:
        from src.scrape.summer_league_playwright import scrape_table
        df = scrape_table(year)
        if not df.empty:
            df["source"] = "playwright"
            return df
    except Exception as e:
        logger.warning(f"Playwright fallback failed: {e}")

    # 4. Try manual CSV import
    df = load_csv()
    if not df.empty:
        return df

    logger.warning(
        f"No Summer League data found for {year}. "
        f"To add manually, save a CSV to data/raw/summer_league.csv "
        f"with columns: PLAYER_NAME, GP, MIN, PTS, REB, AST, FG_PCT"
    )
    return pd.DataFrame()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    df = scrape_summer_league()
    if not df.empty:
        cols = [c for c in ["PLAYER_NAME", "GP", "MIN", "PTS", "REB", "AST", "FG_PCT", "source"]
                if c in df.columns]
        print(df[cols].head(15))
        df.to_parquet("data/raw/summer_league.parquet", index=False)
        print(f"Saved {len(df)} rows")
    else:
        print("No data available.")
        print("To add Summer League data manually:")
        print("  1. Find stats on NBA.com Summer League page")
        print("  2. Save as data/raw/summer_league.csv with columns:")
        print("     PLAYER_NAME,GP,MIN,PTS,REB,AST,FG_PCT,3P_PCT,FT_PCT")
