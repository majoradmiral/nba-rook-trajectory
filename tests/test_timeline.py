"""Tests for the weekly featured-player timeline builder."""

from __future__ import annotations

from datetime import date

import pandas as pd

from src import timeline


def _stats_row(game_id: str, game_date: str, player_id: str, name: str, **overrides) -> dict:
    row = {
        "game_id": game_id,
        "season_year": 2027,
        "season_type": "regular",
        "game_date": game_date,
        "player_id": player_id,
        "player_name": name,
        "team_id": "1",
        "team_abbr": "AAA",
        "position": "G",
        "starter": 1,
        "minutes": 30.0,
        "points": 20,
        "field_goals_made": 8,
        "field_goals_attempted": 16,
        "three_pointers_made": 2,
        "three_pointers_attempted": 5,
        "free_throws_made": 2,
        "free_throws_attempted": 3,
        "rebounds": 5,
        "assists": 4,
        "turnovers": 2,
        "steals": 1,
        "blocks": 0,
        "offensive_rebounds": 1,
        "defensive_rebounds": 4,
        "personal_fouls": 2,
        "plus_minus": 9,
        "is_rookie": 1,
    }
    row.update(overrides)
    return row


def _shot_row(game_id: str, game_date: str, player_id: str, name: str, **overrides) -> dict:
    row = {
        "game_id": game_id,
        "season_year": 2027,
        "season_type": "regular",
        "game_date": game_date,
        "player_id": player_id,
        "player_name": name,
        "team_abbr": "AAA",
        "court_x": 0.0,
        "court_y": 1.5,
        "made": 1,
        "is_three": 0,
        "distance": 0.6,
        "shot_type": "dunk",
        "period": 1,
        "clock": "11:30",
        "description": "Player makes 1-foot dunk",
    }
    row.update(overrides)
    return row


def _game_row(game_id: str, game_date: str) -> dict:
    return {
        "game_id": game_id,
        "season_year": 2027,
        "season_type": "regular",
        "game_date": game_date,
        "home_team": "Home",
        "home_abbr": "HOM",
        "home_score": 110,
        "away_team": "Away",
        "away_abbr": "AWY",
        "away_score": 100,
        "status": "post",
        "source": "espn_scoreboard",
    }


def sample_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    games = pd.DataFrame([
        _game_row("g1", "2026-10-20"),
        _game_row("g2", "2026-10-22"),
        _game_row("g3", "2026-10-27"),
    ])
    stats = pd.DataFrame([
        _stats_row("g1", "2026-10-20", "p1", "Alpha Rookie", plus_minus=20, points=24),
        _stats_row("g1", "2026-10-20", "p2", "Beta Rookie", plus_minus=10, points=18),
        _stats_row("g1", "2026-10-20", "p3", "Gamma Vet", plus_minus=30, points=30, is_rookie=0),
        _stats_row("g2", "2026-10-22", "p1", "Alpha Rookie", plus_minus=12, points=20),
        _stats_row("g2", "2026-10-22", "p2", "Beta Rookie", plus_minus=4, points=9),
        _stats_row("g3", "2026-10-27", "p3", "Gamma Vet", plus_minus=25, points=28, is_rookie=0),
    ])
    shots = pd.DataFrame([
        _shot_row("g1", "2026-10-20", "p1", "Alpha Rookie"),
        _shot_row("g1", "2026-10-20", "p1", "Alpha Rookie", court_x=-20.0, court_y=24.0,
                  made=0, is_three=1, distance=25.6, shot_type="jumper"),
        _shot_row("g2", "2026-10-22", "p1", "Alpha Rookie", court_x=5.0, court_y=8.0,
                  distance=8.4, shot_type="jump shot"),
    ])
    return games, stats, shots


def test_week_start_is_monday():
    assert timeline.week_start(date(2026, 10, 21)) == date(2026, 10, 19)
    assert timeline.week_start(date(2026, 10, 19)) == date(2026, 10, 19)


def test_aggregate_stats_computes_rates():
    games, stats, _ = sample_frames()
    agg = timeline.aggregate_stats(stats[stats["player_id"] == "p1"])
    row = agg.iloc[0]
    assert row["games_played"] == 2
    assert row["points_per_game"] == 22.0
    assert row["plus_minus_per_game"] == 16.0
    assert row["field_goal_pct"] == 0.5
    assert row["three_point_pct"] == 0.4


def test_rank_players_orders_by_plus_minus_per_game():
    games, stats, _ = sample_frames()
    ranked = timeline.rank_players(timeline.aggregate_stats(stats), rookies_only=True)
    assert list(ranked["player_name"]) == ["Alpha Rookie", "Beta Rookie"]
    assert list(ranked["rank"]) == [1, 2]

    everyone = timeline.rank_players(timeline.aggregate_stats(stats), rookies_only=False)
    assert everyone.iloc[0]["player_name"] == "Gamma Vet"


def test_featured_ids_prefer_players_who_played_that_week():
    games, stats, _ = sample_frames()
    leaderboard = timeline.rank_players(timeline.aggregate_stats(stats), rookies_only=False)
    week_stats = timeline.aggregate_stats(stats[stats["game_id"] == "g2"])
    featured = timeline._featured_ids(leaderboard, week_stats, 3)
    assert "p1" in featured and "p2" in featured
    assert "p3" not in featured


def test_build_timeline_groups_weeks_and_features_three_players():
    games, stats, shots = sample_frames()
    payload = timeline.build_timeline(games, stats, shots, per_week=3)

    assert payload["season_year"] == 2027
    assert payload["season_label"] == "2026-27"
    assert len(payload["weeks"]) == 2

    first_week = payload["weeks"][0]
    assert first_week["start"] == "2026-10-19"
    assert first_week["games"] == 2
    assert len(first_week["featured"]) == 2

    alpha = first_week["featured"][0]
    assert alpha["name"] == "Alpha Rookie"
    assert alpha["rank"] == 1
    assert alpha["overall_rank"] == 1
    assert alpha["played"] is True
    assert len(alpha["shots"]) == 3
    assert alpha["zones"]["rim"]["attempts"] == 1
    assert alpha["zones"]["mid"]["attempts"] == 1
    assert alpha["zones"]["three"]["attempts"] == 1
    assert alpha["week"]["points"] == 22.0

    assert payload["leaderboard"][0]["name"] == "Alpha Rookie"
    assert payload["recent_games"][0]["game_id"] == "g3"
    assert payload["totals"]["shots"] == 3


def test_build_timeline_ranks_regular_season_weeks_on_regular_games_only():
    games = pd.DataFrame([
        _game_row("g0", "2026-10-01"),
        _game_row("g1", "2026-10-20"),
    ])
    stats = pd.DataFrame([
        _stats_row(
            "g0", "2026-10-01", "p0", "Preseason Star",
            season_type="preseason", points=40, plus_minus=40,
        ),
        _stats_row("g1", "2026-10-20", "p1", "Regular Rookie", points=12),
    ])
    shots = pd.DataFrame(
        columns=[
            "game_id", "season_year", "season_type", "game_date", "player_id",
            "player_name", "team_abbr", "court_x", "court_y", "made", "is_three",
            "distance", "shot_type", "period", "clock", "description",
        ]
    )

    payload = timeline.build_timeline(games, stats, shots, per_week=3)

    regular_week = next(
        week for week in payload["weeks"] if week["start"] == "2026-10-19"
    )
    assert regular_week["headline"] == ["Regular Rookie"]
    assert [row["name"] for row in payload["leaderboard"]] == ["Regular Rookie"]


def test_build_timeline_handles_empty_input():
    payload = timeline.build_timeline(pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    assert payload["weeks"] == []
    assert payload["leaderboard"] == []
    assert payload["season_year"] is None
