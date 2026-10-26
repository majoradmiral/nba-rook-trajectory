"""Tests for the ESPN season ingestion helpers."""

from __future__ import annotations

import sqlite3

from src import season_tracker


def test_refresh_rookie_flags_backfills_new_rows():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE season_player_stats ("
        "player_id TEXT, season_year INTEGER, is_rookie INTEGER)"
    )
    conn.executemany(
        "INSERT INTO season_player_stats VALUES (?, ?, ?)",
        [("rookie", 2027, 0), ("veteran", 2027, 0), ("old-rookie", 2026, 1)],
    )

    season_tracker._refresh_rookie_flags(conn, 2027, {"rookie"})

    flags = dict(
        conn.execute(
            "SELECT player_id, is_rookie FROM season_player_stats"
        ).fetchall()
    )
    assert flags["rookie"] == 1
    assert flags["veteran"] == 0
    assert flags["old-rookie"] == 1


def test_court_coordinates_center_on_the_rim():
    # A layup two feet in front of the rim on the left block.
    x, y = season_tracker.court_coordinates({"x": 22, "y": 2})
    assert x == -3.0
    assert y == 2.0


def test_court_coordinates_skip_sentinel_values():
    # Free throws carry ESPN's sentinel coordinate.
    assert season_tracker.court_coordinates({"x": -214748340, "y": -214748365}) is None
    assert season_tracker.court_coordinates({}) is None
    assert season_tracker.court_coordinates({"x": None, "y": 3}) is None


def test_three_pointer_detection():
    assert season_tracker.is_three_pointer("Player makes 24-foot three point jumper")
    assert season_tracker.is_three_pointer("Player makes 26-foot three pointer")
    assert not season_tracker.is_three_pointer("Player makes 10-foot driving layup")


def test_shot_type_parsing():
    assert season_tracker.parse_shot_type("Player makes 1-foot dunk") == "dunk"
    assert season_tracker.parse_shot_type("Player makes 5-foot driving floating jump") == "floater"
    assert season_tracker.parse_shot_type("Player makes 24-foot step back jumper") == "jumper"
    assert season_tracker.parse_shot_type("Player makes 8-foot hook shot") == "hook shot"


def test_reported_distance_parsing():
    assert season_tracker.parse_reported_distance("Player misses 24-foot three point jumper") == 24.0
    assert season_tracker.parse_reported_distance("Player makes layup") is None


def test_game_rows_include_season_type_and_scores():
    game = {
        "game_id": "401909834",
        "season_year": 2027,
        "season_type": "regular",
        "game_date": "2026-10-21",
        "home_team_id": "1",
        "home_team": "Atlanta Hawks",
        "home_abbr": "ATL",
        "home_score": 132,
        "away_team_id": "23",
        "away_team": "Orlando Magic",
        "away_abbr": "ORL",
        "away_score": 125,
        "status": "post",
        "source": "espn_scoreboard",
    }
    assert season_tracker.SEASON_TYPES[2] == "regular"
    assert game["season_type"] == "regular"
    assert game["home_score"] > game["away_score"]
