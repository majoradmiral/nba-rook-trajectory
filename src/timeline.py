"""Build the weekly featured-player timeline that powers ``site/index.html``.

Every week of the season gets its own slice:

* the leaderboard as it stood at the end of that week (per-game performance
  score — the same metric as the README leaderboard),
* the top three players of that week,
* each of their shot attempts on a court fixture, taken from the ESPN shot
  coordinates stored by :mod:`src.season_tracker`.

The result is written to ``site/data/timeline.json`` (and a ``timeline.js``
wrapper so the page also works when opened straight from disk).

Usage:
    python -m src.timeline
    python -m src.timeline --sync        # refresh the source data first
    python -m src.timeline --per-week 5   # feature five players per week
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

logger = logging.getLogger(__name__)

SITE_DIR = ROOT / "site"
DATA_DIR = SITE_DIR / "data"

FEATURED_PER_WEEK = 3
MIN_GAMES = 1
MIN_MINUTES = 10.0
LEADERBOARD_SIZE = 10
RECENT_GAMES = 12

COMPETITIVE_TYPES = ("regular", "playoffs")
ALL_TYPES = ("preseason", "regular", "playoffs")

RIM_FEET = 8.0
MID_RANGE_FEET = 22.0
RIM_OFFSET = 1.575  # rim centre sits 1.575 ft inside the baseline

_STAT_COLUMNS = [
    "player_id", "player_name", "team_abbr", "position", "is_rookie",
    "games_played", "minutes_per_game", "points_per_game", "rebounds_per_game",
    "assists_per_game", "turnovers_per_game", "steals_per_game", "blocks_per_game",
    "field_goal_pct", "three_point_pct", "free_throw_pct",
    "plus_minus", "plus_minus_per_game", "performance_score",
]

PERFORMANCE_SCORE_NOTE = "performance score"
PERFORMANCE_SCORE_FORMULA = "PTS + 1.2×REB + 1.5×AST + 2×STL + 2×BLK − TOV"


# ── Helpers ──────────────────────────────────────────────────────────────────

def week_start(day: date) -> date:
    """Monday of the ISO week that ``day`` belongs to."""
    return day - timedelta(days=day.weekday())


def _safe_rate(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return round(numerator / denominator, 4)


def aggregate_stats(stats: pd.DataFrame) -> pd.DataFrame:
    """Aggregate player-game rows into per-player totals and per-game rates."""
    if stats.empty:
        return pd.DataFrame(columns=_STAT_COLUMNS)

    ordered = stats.sort_values(["game_date", "player_id"])
    grouped = ordered.groupby("player_id", as_index=False)

    agg = grouped.agg(
        player_name=("player_name", "last"),
        team_abbr=("team_abbr", "last"),
        position=("position", "last"),
        is_rookie=("is_rookie", "max"),
        games_played=("game_id", "nunique"),
        total_minutes=("minutes", "sum"),
        total_points=("points", "sum"),
        total_rebounds=("rebounds", "sum"),
        total_assists=("assists", "sum"),
        total_turnovers=("turnovers", "sum"),
        total_steals=("steals", "sum"),
        total_blocks=("blocks", "sum"),
        field_goals_made=("field_goals_made", "sum"),
        field_goals_attempted=("field_goals_attempted", "sum"),
        three_pointers_made=("three_pointers_made", "sum"),
        three_pointers_attempted=("three_pointers_attempted", "sum"),
        free_throws_made=("free_throws_made", "sum"),
        free_throws_attempted=("free_throws_attempted", "sum"),
        plus_minus=("plus_minus", "sum"),
    )

    games = agg["games_played"].replace(0, pd.NA)
    agg["minutes_per_game"] = (agg["total_minutes"] / games).fillna(0).astype(float).round(2)
    agg["points_per_game"] = (agg["total_points"] / games).fillna(0).astype(float).round(2)
    agg["rebounds_per_game"] = (agg["total_rebounds"] / games).fillna(0).astype(float).round(2)
    agg["assists_per_game"] = (agg["total_assists"] / games).fillna(0).astype(float).round(2)
    agg["turnovers_per_game"] = (agg["total_turnovers"] / games).fillna(0).astype(float).round(2)
    agg["steals_per_game"] = (agg["total_steals"] / games).fillna(0).astype(float).round(2)
    agg["blocks_per_game"] = (agg["total_blocks"] / games).fillna(0).astype(float).round(2)
    agg["plus_minus_per_game"] = (agg["plus_minus"] / games).fillna(0).astype(float).round(2)
    agg["field_goal_pct"] = [
        _safe_rate(m, a) for m, a in zip(agg["field_goals_made"], agg["field_goals_attempted"])
    ]
    agg["three_point_pct"] = [
        _safe_rate(m, a) for m, a in zip(agg["three_pointers_made"], agg["three_pointers_attempted"])
    ]
    agg["free_throw_pct"] = [
        _safe_rate(m, a) for m, a in zip(agg["free_throws_made"], agg["free_throws_attempted"])
    ]
    agg["performance_score"] = (
        agg["points_per_game"]
        + 1.2 * agg["rebounds_per_game"]
        + 1.5 * agg["assists_per_game"]
        + 2.0 * agg["steals_per_game"]
        + 2.0 * agg["blocks_per_game"]
        - agg["turnovers_per_game"]
    ).round(2)

    return agg[_STAT_COLUMNS].reset_index(drop=True)


def rank_players(
    agg: pd.DataFrame,
    rookies_only: bool = True,
    min_games: int = MIN_GAMES,
    min_minutes: float = 0.0,
) -> pd.DataFrame:
    """Rank players by per-game performance score, then plus/minus and points."""
    if agg.empty:
        return agg.assign(rank=pd.Series(dtype=int))

    frame = agg.copy()
    if rookies_only and "is_rookie" in frame.columns:
        frame = frame[frame["is_rookie"] == 1]
    frame = frame[frame["games_played"] >= min_games]
    if min_minutes and "minutes_per_game" in frame.columns:
        qualified = frame[frame["minutes_per_game"] >= min_minutes]
        if not qualified.empty:
            frame = qualified
    frame = frame.sort_values(
        ["performance_score", "plus_minus_per_game", "points_per_game", "player_name"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)
    frame["rank"] = frame.index + 1
    return frame


def _zone_counts(shots: pd.DataFrame) -> dict:
    """Made/attempted split for rim, mid-range, and three-point zones."""
    zones = {"rim": [0, 0], "mid": [0, 0], "three": [0, 0]}
    if shots.empty:
        return {name: {"made": 0, "attempts": 0} for name in zones}

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
            "pct": _safe_rate(made, attempts),
        }
        for name, (made, attempts) in zones.items()
    }


def _player_payload(
    player_id: str,
    week_stats: pd.DataFrame,
    season_stats: pd.DataFrame,
    shots: pd.DataFrame,
    rank: int,
    overall_rank: int,
) -> dict:
    """One featured player: identity, weekly line, season line, shot chart."""
    identity = {}
    for frame in (season_stats, week_stats):
        if not frame.empty and player_id in set(frame["player_id"]):
            row = frame[frame["player_id"] == player_id].iloc[0]
            identity = {
                "player_id": str(row["player_id"]),
                "name": row["player_name"],
                "team": row["team_abbr"],
                "position": row["position"],
                "is_rookie": int(row["is_rookie"]),
            }
            break

    def line(frame: pd.DataFrame) -> dict:
        if frame.empty or player_id not in set(frame["player_id"]):
            return {}
        row = frame[frame["player_id"] == player_id].iloc[0]
        return {
            "games": int(row["games_played"]),
            "minutes": float(row["minutes_per_game"]),
            "points": float(row["points_per_game"]),
            "rebounds": float(row["rebounds_per_game"]),
            "assists": float(row["assists_per_game"]),
            "steals": float(row["steals_per_game"]),
            "blocks": float(row["blocks_per_game"]),
            "turnovers": float(row["turnovers_per_game"]),
            "fg_pct": float(row["field_goal_pct"]),
            "three_pct": float(row["three_point_pct"]),
            "ft_pct": float(row["free_throw_pct"]),
            "plus_minus": float(row["plus_minus_per_game"]),
            "score": float(row["performance_score"]),
        }

    shot_rows = []
    for shot in shots.itertuples(index=False):
        shot_rows.append(
            {
                "x": round(float(shot.court_x), 2),
                "y": round(float(shot.court_y), 2),
                "made": int(shot.made),
                "three": int(shot.is_three),
                "distance": round(float(shot.distance), 1),
                "type": shot.shot_type,
                "game_id": shot.game_id,
                "date": shot.game_date,
            }
        )
    shot_rows.sort(key=lambda item: (item["date"], item["game_id"]))

    payload = {"rank": rank, "overall_rank": overall_rank, **identity}
    payload["played"] = bool(
        not week_stats.empty and player_id in set(week_stats["player_id"].astype(str))
    )
    payload["week"] = line(week_stats)
    payload["season"] = line(season_stats)
    payload["zones"] = _zone_counts(shots)
    payload["shots"] = shot_rows
    payload["shot_totals"] = {
        "made": sum(1 for shot in shot_rows if shot["made"]),
        "attempts": len(shot_rows),
    }
    return payload


def _label_for_week(start: date, end: date) -> str:
    same_month = start.month == end.month
    if same_month:
        return f"{start.strftime('%b %d')} – {end.strftime('%d, %Y')}"
    return f"{start.strftime('%b %d')} – {end.strftime('%b %d, %Y')}"


def _featured_ids(
    leaderboard: pd.DataFrame,
    week_stats: pd.DataFrame,
    per_week: int,
) -> list[str]:
    """Pick the players to spotlight for a week.

    The ranking is cumulative (season to date), but a player is only featured
    when they actually suited up that week — otherwise their card would be an
    empty shot chart. Weeks with fewer than ``per_week`` rookies simply show
    fewer cards.
    """
    if leaderboard.empty:
        return []

    played = set(week_stats["player_id"].astype(str)) if not week_stats.empty else set()
    ordered = leaderboard["player_id"].astype(str).tolist()
    return [player_id for player_id in ordered if player_id in played][:per_week]


# ── Timeline ─────────────────────────────────────────────────────────────────

def build_timeline(
    games: pd.DataFrame,
    stats: pd.DataFrame,
    shots: pd.DataFrame,
    per_week: int = FEATURED_PER_WEEK,
    rookies_only: bool = True,
    min_games: int = MIN_GAMES,
    leaderboard_size: int = LEADERBOARD_SIZE,
    recent_games: int = RECENT_GAMES,
    generated_at: Optional[datetime] = None,
) -> dict:
    """Assemble the full timeline payload from the season database tables."""
    generated_at = generated_at or datetime.now(timezone.utc)
    payload: dict = {
        "generated_at": generated_at.replace(microsecond=0).isoformat(),
        "season_year": int(games["season_year"].max()) if not games.empty else None,
        "season_label": "",
        "featured_per_week": per_week,
        "scope": "rookies" if rookies_only else "all",
        "ranking_metric": PERFORMANCE_SCORE_NOTE,
        "ranking_formula": PERFORMANCE_SCORE_FORMULA,
        "leaderboard": [],
        "weeks": [],
        "recent_games": [],
        "totals": {},
    }
    if games.empty or stats.empty:
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

    games = games.sort_values("game_date")
    week_map: dict[date, list[str]] = {}
    for game in games.itertuples(index=False):
        start = week_start(game.game_date)
        week_map.setdefault(start, []).append(game.game_id)
    weeks = sorted(week_map)

    leaderboard: pd.DataFrame = pd.DataFrame()
    week_payloads = []

    for index, start in enumerate(weeks, start=1):
        end = start + timedelta(days=6)
        week_games = games[
            (games["game_date"] >= start) & (games["game_date"] <= end)
        ]
        if week_games.empty:
            continue

        cumulative_stats = stats[stats["game_date"] <= end]
        week_stats_all = stats[
            (stats["game_date"] >= start) & (stats["game_date"] <= end)
        ]

        # Once the regular season starts, rank only on competitive games so the
        # featured shot charts match the README leaderboard. Preseason-only
        # weeks still rank on the preseason sample.
        week_types = {str(value) for value in week_games["season_type"].unique()}
        competitive_week = bool(week_types.intersection(COMPETITIVE_TYPES))
        ranking_stats = cumulative_stats
        if competitive_week:
            competitive_stats = cumulative_stats[
                cumulative_stats["season_type"].isin(COMPETITIVE_TYPES)
            ]
            if not competitive_stats.empty:
                ranking_stats = competitive_stats

        leaderboard = rank_players(
            aggregate_stats(ranking_stats),
            rookies_only=rookies_only,
            min_games=min_games,
        )
        if leaderboard.empty:
            continue

        featured_ids = _featured_ids(leaderboard, week_stats_all, per_week)
        week_stats = aggregate_stats(week_stats_all)
        week_shots = shots[
            (shots["game_date"] >= start) & (shots["game_date"] <= end)
        ]

        players = []
        for position, player_id in enumerate(featured_ids, start=1):
            player_shots = week_shots[week_shots["player_id"] == player_id]
            overall_rank = int(
                leaderboard[leaderboard["player_id"] == player_id].iloc[0]["rank"]
            )
            players.append(
                _player_payload(
                    str(player_id),
                    week_stats,
                    leaderboard,
                    player_shots,
                    position,
                    overall_rank,
                )
            )

        types = sorted({str(t) for t in week_games["season_type"].unique()})
        week_payloads.append(
            {
                "index": index,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "label": _label_for_week(start, end),
                "season_types": types,
                "games": int(len(week_games)),
                "featured": players,
                "headline": [player["name"] for player in players],
            }
        )

    payload["weeks"] = week_payloads

    final_stats = stats
    competitive_stats = stats[stats["season_type"].isin(COMPETITIVE_TYPES)]
    if not competitive_stats.empty:
        final_stats = competitive_stats
    final_leaderboard = rank_players(
        aggregate_stats(final_stats),
        rookies_only=rookies_only,
        min_games=min_games,
        min_minutes=MIN_MINUTES,
    )

    leaderboard_rows = []
    if not final_leaderboard.empty:
        for row in final_leaderboard.head(leaderboard_size).itertuples(index=False):
            leaderboard_rows.append(
                {
                    "rank": int(row.rank),
                    "player_id": str(row.player_id),
                    "name": row.player_name,
                    "team": row.team_abbr,
                    "position": row.position,
                    "is_rookie": int(row.is_rookie),
                    "games": int(row.games_played),
                    "minutes": float(row.minutes_per_game),
                    "points": float(row.points_per_game),
                    "rebounds": float(row.rebounds_per_game),
                    "assists": float(row.assists_per_game),
                    "plus_minus": float(row.plus_minus_per_game),
                    "fg_pct": float(row.field_goal_pct),
                    "three_pct": float(row.three_point_pct),
                    "score": float(row.performance_score),
                }
            )
    payload["leaderboard"] = leaderboard_rows

    tracked_ids = {row["player_id"] for row in leaderboard_rows}
    recent_payload = []
    for game in games.tail(recent_games).iloc[::-1].itertuples(index=False):
        lines = []
        game_stats = stats[
            (stats["game_id"] == game.game_id) & (stats["player_id"].isin(tracked_ids))
        ]
        for line_row in game_stats.itertuples(index=False):
            lines.append(
                {
                    "player_id": str(line_row.player_id),
                    "name": line_row.player_name,
                    "team": line_row.team_abbr,
                    "minutes": float(line_row.minutes),
                    "points": int(line_row.points),
                    "rebounds": int(line_row.rebounds),
                    "assists": int(line_row.assists),
                    "plus_minus": int(line_row.plus_minus),
                }
            )
        recent_payload.append(
            {
                "game_id": game.game_id,
                "date": game.game_date.isoformat(),
                "season_type": game.season_type,
                "away": {"abbr": game.away_abbr, "score": int(game.away_score)},
                "home": {"abbr": game.home_abbr, "score": int(game.home_score)},
                "lines": lines,
            }
        )
    payload["recent_games"] = recent_payload

    payload["totals"] = {
        "games": int(len(games)),
        "games_by_type": {
            str(key): int(value)
            for key, value in games["season_type"].value_counts().items()
        },
        "players": int(stats["player_id"].nunique()),
        "shots": int(len(shots)),
        "weeks": len(week_payloads),
    }
    return payload


def write_timeline(payload: dict, data_dir: str | Path = DATA_DIR) -> tuple[Path, Path]:
    """Write ``timeline.json`` plus a ``timeline.js`` wrapper for file:// use."""
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    json_path = data_dir / "timeline.json"
    js_path = data_dir / "timeline.js"

    json_text = json.dumps(payload, indent=2, default=str)
    json_path.write_text(json_text, encoding="utf-8")
    js_path.write_text(
        "window.TIMELINE_DATA = " + json.dumps(payload, separators=(",", ":"), default=str) + ";\n",
        encoding="utf-8",
    )
    logger.info("Wrote %s (%.1f KB)", json_path, len(json_text) / 1024)
    return json_path, js_path


def main(argv: Optional[Iterable[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Build the weekly shot-chart timeline.")
    parser.add_argument("--db", default=str(DB_PATH), help="Season database path.")
    parser.add_argument("--per-week", type=int, default=FEATURED_PER_WEEK)
    parser.add_argument("--all-players", action="store_true", help="Rank every player, not just rookies.")
    parser.add_argument("--sync", action="store_true", help="Refresh the source data first.")
    parser.add_argument("--force", action="store_true", help="Re-fetch every day during sync.")
    parser.add_argument(
        "--no-readme",
        action="store_true",
        help="Do not refresh the README leaderboard table.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.sync:
        from src.season_tracker import sync_season

        sync_season(force_days=args.force)

    games = load_games(args.db)
    stats = load_player_stats(args.db)
    shots = load_shots(args.db)
    payload = build_timeline(
        games,
        stats,
        shots,
        per_week=args.per_week,
        rookies_only=not args.all_players,
    )
    write_timeline(payload)

    print(f"Season {payload.get('season_label') or payload.get('season_year')}")
    print(f"  weeks: {len(payload['weeks'])}")
    print(f"  featured per week: {payload['featured_per_week']}")
    print(f"  leaderboard size: {len(payload['leaderboard'])}")
    print(f"  recent games: {len(payload['recent_games'])}")
    if payload["weeks"]:
        latest = payload["weeks"][-1]
        print(f"  latest week: {latest['label']} -> {', '.join(latest['headline'])}")

    if not args.no_readme:
        from src.readme_leaderboard import update_readme_from_season

        if update_readme_from_season():
            print("README leaderboard refreshed from regular season + playoffs.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    main()
