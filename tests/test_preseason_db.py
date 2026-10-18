"""Tests for preseason rookie box-score ingestion and summaries."""

from __future__ import annotations

import sqlite3
from datetime import date

import pandas as pd

from src import preseason_db
from src.espn_client import (
    _ROOKIE_BOXSCORE_COLUMNS,
    _scoreboard_rows_for_day,
    _summary_rookie_rows,
)


def sample_game() -> dict:
    return {
        "game_id": "game-1",
        "season_year": 2027,
        "game_date": date(2026, 10, 3),
    }


def sample_summary() -> dict:
    labels = [
        "MIN", "PTS", "FG", "3PT", "FT", "REB", "AST", "TO",
        "STL", "BLK", "OREB", "DREB", "PF", "+/-",
    ]
    keys = [
        "minutes", "points", "fieldGoalsMade-fieldGoalsAttempted",
        "threePointFieldGoalsMade-threePointFieldGoalsAttempted",
        "freeThrowsMade-freeThrowsAttempted", "rebounds", "assists",
        "turnovers", "steals", "blocks", "offensiveRebounds",
        "defensiveRebounds", "fouls", "plusMinus",
    ]
    return {
        "boxscore": {
            "players": [
                {
                    "team": {
                        "id": "1",
                        "displayName": "Atlanta Hawks",
                        "abbreviation": "ATL",
                    },
                    "statistics": [
                        {
                            "labels": labels,
                            "keys": keys,
                            "athletes": [
                                {
                                    "athlete": {
                                        "id": "rookie-1",
                                        "displayName": "Rookie One",
                                        "position": {"abbreviation": "G"},
                                    },
                                    "starter": True,
                                    "didNotPlay": False,
                                    "stats": [
                                        "30:30", "13", "4-8", "2-4", "3-3",
                                        "5", "4", "2", "1", "0", "1", "4",
                                        "3", "+7",
                                    ],
                                },
                                {
                                    "athlete": {
                                        "id": "veteran-1",
                                        "displayName": "Veteran",
                                    },
                                    "starter": True,
                                    "didNotPlay": False,
                                    "stats": [
                                        "30", "12", "5-10", "1-3", "1-2",
                                        "6", "3", "1", "0", "1", "2", "4",
                                        "2", "+2",
                                    ],
                                },
                            ],
                        }
                    ],
                }
            ]
        }
    }


def sample_games() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                **sample_game(),
                "home_team_id": "1",
                "home_team": "Atlanta Hawks",
                "home_abbr": "ATL",
                "home_score": 100,
                "away_team_id": "2",
                "away_team": "Boston Celtics",
                "away_abbr": "BOS",
                "away_score": 95,
                "status": "post",
                "detail": "Final",
                "source": "espn_scoreboard",
            }
        ]
    )


def sample_stats() -> pd.DataFrame:
    rows = _summary_rookie_rows(
        sample_game(),
        sample_summary(),
        {"rookie-1"},
    )
    return pd.DataFrame(rows, columns=_ROOKIE_BOXSCORE_COLUMNS)


def test_summary_parser_keeps_only_rookies_and_parses_boxscore_stats():
    stats = sample_stats()

    assert len(stats) == 1
    assert stats.loc[0, "player_id"] == "rookie-1"
    assert stats.loc[0, "minutes"] == 30.5
    assert stats.loc[0, "field_goals_made"] == 4
    assert stats.loc[0, "three_pointers_attempted"] == 4
    assert stats.loc[0, "plus_minus"] == 7


def test_scoreboard_game_date_uses_local_scoreboard_day(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "events": [
                    {
                        "id": "game-1",
                        "date": "2026-10-17T00:30:00Z",
                        "competitions": [
                            {
                                "id": "game-1",
                                "status": {"type": {"state": "post", "completed": True}},
                                "competitors": [
                                    {
                                        "homeAway": "home",
                                        "team": {"id": "1", "displayName": "Home"},
                                        "score": "100",
                                    },
                                    {
                                        "homeAway": "away",
                                        "team": {"id": "2", "displayName": "Away"},
                                        "score": "95",
                                    },
                                ],
                            }
                        ],
                    }
                ]
            }

    monkeypatch.setattr("src.espn_client.requests.get", lambda *_args, **_kwargs: FakeResponse())
    rows = _scoreboard_rows_for_day(date(2026, 10, 16), 2027)

    assert rows[0]["game_date"] == "2026-10-16"


def test_totals_include_counts_rates_and_shooting_percentages():
    stats = sample_stats()
    second_game = stats.iloc[0].copy()
    second_game["game_id"] = "game-2"
    second_game["points"] = 17
    second_game["field_goals_made"] = 5
    second_game["field_goals_attempted"] = 10
    stats = pd.concat([stats, second_game.to_frame().T], ignore_index=True)

    totals = preseason_db.build_preseason_rookie_totals(stats)

    assert len(totals) == 1
    assert totals.loc[0, "games_played"] == 2
    assert totals.loc[0, "total_points"] == 30
    assert totals.loc[0, "points_per_game"] == 15
    assert totals.loc[0, "field_goal_pct"] == 0.5


def test_sync_replaces_a_season_and_persists_rookie_only_tables(monkeypatch, tmp_path):
    db_path = tmp_path / "preseason.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE preseason_team_totals (team_name TEXT)")
    conn.execute("INSERT INTO preseason_team_totals VALUES ('stale')")
    conn.commit()
    conn.close()

    monkeypatch.setattr(preseason_db, "fetch_nba_preseason_games", lambda _year: sample_games())
    monkeypatch.setattr(
        preseason_db,
        "fetch_nba_rookie_roster",
        lambda _year: pd.DataFrame(
            [{"player_id": "rookie-1", "player_name": "Rookie One"}]
        ),
    )
    monkeypatch.setattr(
        preseason_db,
        "fetch_nba_preseason_rookie_stats",
        lambda _games, _rookies: sample_stats(),
    )

    for _ in range(2):
        stats, totals = preseason_db.sync_preseason_data(db_path, season_year=2027)
        assert len(stats) == 1
        assert len(totals) == 1

    conn = sqlite3.connect(db_path)
    try:
        table_names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert "preseason_team_totals" not in table_names
        assert "preseason_rookie_game_stats" in table_names
        assert "preseason_rookie_totals" in table_names
        assert conn.execute("SELECT COUNT(*) FROM preseason_games").fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM preseason_rookie_game_stats"
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT player_id FROM preseason_rookie_game_stats"
        ).fetchone()[0] == "rookie-1"
    finally:
        conn.close()
