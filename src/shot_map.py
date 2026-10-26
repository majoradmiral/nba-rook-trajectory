"""Build the all-rookie shot map that powers ``site/shots.html``.

Where :mod:`src.timeline` spotlights three players a week, this module ships
*every* shot a rookie took, together with enough context to answer "whose shot
is whose" on the page: a player index, a game index and one entry per attempt.

The result is written to ``site/data/shots.json`` (plus a ``shots.js`` wrapper
so the page also works when opened straight from disk).

Usage:
    python -m src.shot_map
    python -m src.shot_map --sync         # refresh the source data first
    python -m src.shot_map --all-players  # include veterans too
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

from src.config import ROOT
from src.season_tracker import DB_PATH, load_games, load_player_stats, load_shots
from src.timeline import (
    MID_RANGE_FEET,
    RIM_FEET,
    RIM_OFFSET,
    aggregate_stats,
    rank_players,
    week_start,
)

logger = logging.getLogger(__name__)

SITE_DIR = ROOT / "site"
DATA_DIR = SITE_DIR / "data"

SHOT_MAP_JS_NAME = "shots.js"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _rate(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return round(numerator / denominator, 4)


def _zone_counts(shots: pd.DataFrame) -> dict:
    """Made/attempted split for rim, mid-range and three-point zones."""
    zones = {"rim": [0, 0], "mid": [0, 0], "three": [0, 0]}
    if shots.empty:
        return {
            name: {"made": 0, "attempts": 0, "pct": 0.0}
            for name in zones
        }

    for shot in shots.itertuples(index=False):
        distance = float(shot.distance)
        if getattr(shot, "is_three", 0) or distance >= MID_RANGE_FEET:
            key = "three"
        elif distance <= RIM_FEET:
            key = "rim"
        else:
            key = "mid"
        zones[key][1] += 1
        if shot.made:
            zones[key][0] += 1

    return {
        name: {
            "made": made,
            "attempts": attempts,
            "pct": _rate(made, attempts),
        }
        for name, (made, attempts) in zones.items()
    }


def _week_label(start: date, end: date) -> str:
    if start.month == end.month:
        return f"{start.strftime('%b %d')} – {end.strftime('%d, %Y')}"
    return f"{start.strftime('%b %d')} – {end.strftime('%b %d, %Y')}"


# ── Builder ──────────────────────────────────────────────────────────────────

def build_shot_map(
    games: pd.DataFrame,
    stats: pd.DataFrame,
    shots: pd.DataFrame,
    rookies_only: bool = True,
    generated_at: Optional[datetime] = None,
) -> dict:
    """Assemble the shot-map payload from the season database tables."""
    generated_at = generated_at or datetime.now(timezone.utc)
    payload: dict = {
        "generated_at": generated_at.replace(microsecond=0).isoformat(),
        "season_year": int(games["season_year"].max()) if not games.empty else None,
        "season_label": "",
        "scope": "rookies" if rookies_only else "all",
        "totals": {},
        "weeks": [],
        "games": [],
        "players": [],
        "shots": [],
    }
    if games.empty or stats.empty or shots.empty:
        return payload

    season_year = payload["season_year"]
    payload["season_label"] = f"{season_year - 1}-{str(season_year)[-2:]}"
    games = games[games["season_year"] == season_year].copy()
    stats = stats[stats["season_year"] == season_year].copy()
    shots = shots[shots["season_year"] == season_year].copy()

    games["game_date"] = pd.to_datetime(games["game_date"]).dt.date
    stats["game_date"] = pd.to_datetime(stats["game_date"]).dt.date
    shots["game_date"] = pd.to_datetime(shots["game_date"]).dt.date

    # Distances are measured from the rim centre, not the baseline.
    if not shots.empty:
        shots = shots.copy()
        shots["distance"] = (
            shots["court_x"].pow(2) + (shots["court_y"] - RIM_OFFSET).pow(2)
        ).pow(0.5).round(2)

    tracked_ids = set(stats["player_id"].astype(str))
    rookie_ids = set(
        stats.loc[stats["is_rookie"] == 1, "player_id"].astype(str)
    )
    if rookies_only:
        tracked_ids = rookie_ids & tracked_ids
    shots = shots[shots["player_id"].astype(str).isin(tracked_ids)].copy()

    games = games.sort_values(["game_date", "game_id"])
    shots = shots.sort_values(["game_date", "game_id", "player_name"])

    # ── Weeks ───────────────────────────────────────────────────────────────
    week_map: dict[date, list[str]] = {}
    for game in games.itertuples(index=False):
        week_map.setdefault(week_start(game.game_date), []).append(game.game_id)

    week_payloads = []
    for index, start in enumerate(sorted(week_map), start=1):
        end = start + timedelta(days=6)
        week_games = games[
            (games["game_date"] >= start) & (games["game_date"] <= end)
        ]
        if week_games.empty:
            continue
        week_shots = shots[
            (shots["game_date"] >= start) & (shots["game_date"] <= end)
        ]
        week_payloads.append(
            {
                "index": index,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "label": _week_label(start, end),
                "season_types": sorted({str(t) for t in week_games["season_type"].unique()}),
                "games": int(len(week_games)),
                "shots": int(len(week_shots)),
                "players": int(week_shots["player_id"].nunique()) if not week_shots.empty else 0,
            }
        )
    payload["weeks"] = week_payloads

    # ── Games ───────────────────────────────────────────────────────────────
    game_payloads = []
    game_shot_counts: dict[str, int] = {}
    game_player_counts: dict[str, int] = {}
    if not shots.empty:
        counts = shots.groupby("game_id")
        game_shot_counts = {str(k): int(v) for k, v in counts.size().items()}
        game_player_counts = {
            str(k): int(v) for k, v in counts["player_id"].nunique().items()
        }

    for game in games.itertuples(index=False):
        game_id = str(game.game_id)
        game_payloads.append(
            {
                "game_id": game_id,
                "date": game.game_date.isoformat(),
                "season_type": game.season_type,
                "away": {"abbr": game.away_abbr, "score": int(game.away_score)},
                "home": {"abbr": game.home_abbr, "score": int(game.home_score)},
                "shots": game_shot_counts.get(game_id, 0),
                "players": game_player_counts.get(game_id, 0),
            }
        )
    payload["games"] = game_payloads

    # ── Players ─────────────────────────────────────────────────────────────
    player_stats = aggregate_stats(stats[stats["player_id"].astype(str).isin(tracked_ids)])
    leaderboard = rank_players(player_stats, rookies_only=False, min_games=1)

    player_rows = []
    for row in leaderboard.itertuples(index=False):
        player_id = str(row.player_id)
        player_shots = shots[shots["player_id"].astype(str) == player_id]
        player_rows.append(
            {
                "player_id": player_id,
                "name": row.player_name,
                "team": row.team_abbr,
                "position": row.position,
                "is_rookie": int(row.is_rookie),
                "rank": int(row.rank),
                "games": int(row.games_played),
                "minutes": float(row.minutes_per_game),
                "points": float(row.points_per_game),
                "rebounds": float(row.rebounds_per_game),
                "assists": float(row.assists_per_game),
                "plus_minus": float(row.plus_minus_per_game),
                "shots": int(len(player_shots)),
                "made": int(player_shots["made"].sum()) if not player_shots.empty else 0,
                "zones": _zone_counts(player_shots),
            }
        )
    payload["players"] = player_rows

    # ── Shots ───────────────────────────────────────────────────────────────
    shot_rows = []
    for shot in shots.itertuples(index=False):
        shot_rows.append(
            {
                "player_id": str(shot.player_id),
                "game_id": str(shot.game_id),
                "date": shot.game_date.isoformat(),
                "x": round(float(shot.court_x), 2),
                "y": round(float(shot.court_y), 2),
                "made": int(shot.made),
                "three": int(shot.is_three),
                "distance": round(float(shot.distance), 1),
                "type": shot.shot_type,
                "period": int(shot.period) if shot.period is not None else 0,
                "clock": str(shot.clock or ""),
                "description": str(shot.description or ""),
            }
        )
    payload["shots"] = shot_rows

    payload["totals"] = {
        "games": int(len(game_payloads)),
        "games_with_shots": int(len(game_shot_counts)),
        "players": len(player_rows),
        "players_with_shots": int(shots["player_id"].nunique()) if not shots.empty else 0,
        "shots": len(shot_rows),
        "made": sum(1 for shot in shot_rows if shot["made"]),
        "weeks": len(week_payloads),
    }
    return payload


def write_shot_map(payload: dict, data_dir: str | Path = DATA_DIR) -> tuple[Path, Path]:
    """Write ``shots.json`` plus a ``shots.js`` wrapper for file:// use."""
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    json_path = data_dir / "shots.json"
    js_path = data_dir / SHOT_MAP_JS_NAME

    json_text = json.dumps(payload, indent=2, default=str)
    json_path.write_text(json_text, encoding="utf-8")
    js_path.write_text(
        "window.SHOTS_DATA = " + json.dumps(payload, separators=(",", ":"), default=str) + ";\n",
        encoding="utf-8",
    )
    logger.info("Wrote %s (%.1f KB)", json_path, len(json_text) / 1024)
    return json_path, js_path


def main(argv: Optional[Iterable[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Build the all-rookie shot map.")
    parser.add_argument("--db", default=str(DB_PATH), help="Season database path.")
    parser.add_argument("--all-players", action="store_true", help="Include veterans too.")
    parser.add_argument("--sync", action="store_true", help="Refresh the source data first.")
    parser.add_argument("--force", action="store_true", help="Re-fetch every day during sync.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.sync:
        from src.season_tracker import sync_season

        sync_season(force_days=args.force)

    games = load_games(args.db)
    stats = load_player_stats(args.db)
    shots = load_shots(args.db)
    payload = build_shot_map(
        games,
        stats,
        shots,
        rookies_only=not args.all_players,
    )
    write_shot_map(payload)

    totals = payload["totals"]
    print(f"Season {payload.get('season_label') or payload.get('season_year')}")
    print(f"  scope: {payload['scope']}")
    print(f"  games: {totals.get('games', 0)} ({totals.get('games_with_shots', 0)} with shots)")
    print(f"  players: {totals.get('players', 0)} ({totals.get('players_with_shots', 0)} with shots)")
    print(f"  shots: {totals.get('shots', 0)} ({totals.get('made', 0)} made)")
    print(f"  weeks: {totals.get('weeks', 0)}")
    if payload["shots"]:
        top = max(
            payload["players"],
            key=lambda player: player["shots"],
        )
        print(f"  most shots: {top['name']} ({top['shots']})")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    main()
