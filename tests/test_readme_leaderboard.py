"""Tests for the README leaderboard auto-inject."""

from __future__ import annotations

import sqlite3

import pandas as pd

from src import readme_leaderboard


def sample_totals() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "player_name": "High Impact",
                "team_abbr": "AAA",
                "games_played": 4,
                "minutes_per_game": 32.0,
                "points_per_game": 10.0,
                "assists_per_game": 4.0,
                "rebounds_per_game": 5.0,
                "plus_minus": 40,
            },
            {
                "player_name": "Volume Scorer",
                "team_abbr": "BBB",
                "games_played": 5,
                "minutes_per_game": 30.0,
                "points_per_game": 20.0,
                "assists_per_game": 1.0,
                "rebounds_per_game": 2.0,
                "plus_minus": 5,
            },
            {
                "player_name": "Tiny Sample",
                "team_abbr": "CCC",
                "games_played": 1,
                "minutes_per_game": 12.0,
                "points_per_game": 30.0,
                "assists_per_game": 3.0,
                "rebounds_per_game": 3.0,
                "plus_minus": 99,
            },
        ]
    )


def test_leaderboard_ranks_by_performance_score():
    table = readme_leaderboard.build_leaderboard(sample_totals(), min_games=3)

    assert "| Rank | Rookie | Team | GP | MPG | PPG | RPG | APG | SPG | BPG | EFF | FG% | 3P% | Impact |" in table
    assert "unofficial ROTY candidate ranking" in table
    assert "ranked by impact score" in table
    assert table.index("Volume Scorer") < table.index("High Impact")
    assert "23.0" in table


def test_leaderboard_includes_box_score_efficiency():
    totals = pd.DataFrame(
        [
            {
                "player_name": "Efficient Rookie",
                "team_abbr": "AAA",
                "games_played": 1,
                "minutes_per_game": 30.0,
                "points_per_game": 20.0,
                "rebounds_per_game": 5.0,
                "assists_per_game": 4.0,
                "steals_per_game": 1.0,
                "blocks_per_game": 1.0,
                "turnovers_per_game": 2.0,
                "field_goals_made": 8,
                "field_goals_attempted": 16,
                "free_throws_made": 2,
                "free_throws_attempted": 3,
                "plus_minus": 9,
            }
        ]
    )

    table = readme_leaderboard.build_leaderboard(totals, min_games=1)

    assert "| 1 | Efficient Rookie | AAA | 1 | 30.0 | 20.0 | 5.0 | 4.0 | 1.0 | 1.0 | 20.0 |" in table


def test_season_totals_include_free_throws_in_efficiency(tmp_path):
    db_path = tmp_path / "season.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE season_player_stats ("
        "game_id TEXT, season_year INTEGER, game_date TEXT, season_type TEXT, "
        "player_id TEXT, player_name TEXT, team_abbr TEXT, is_rookie INTEGER, "
        "minutes REAL, points INTEGER, rebounds INTEGER, assists INTEGER, "
        "steals INTEGER, blocks INTEGER, turnovers INTEGER, "
        "field_goals_made INTEGER, field_goals_attempted INTEGER, "
        "free_throws_made INTEGER, free_throws_attempted INTEGER, "
        "three_pointers_made INTEGER, three_pointers_attempted INTEGER, plus_minus INTEGER)"
    )
    conn.execute(
        "INSERT INTO season_player_stats VALUES "
        "('g1', 2027, '2026-10-25', 'regular', 'p1', 'Rookie', 'AAA', 1, "
        "30, 20, 5, 4, 1, 1, 2, 8, 16, 2, 3, 2, 5, 9)"
    )
    conn.commit()
    conn.close()

    totals = readme_leaderboard.load_season_totals(db_path)
    efficiency = readme_leaderboard._add_performance_score(totals).iloc[0][
        "efficiency_per_game"
    ]

    assert efficiency == 20.0


def test_leaderboard_excludes_small_samples_but_falls_back():
    qualified = readme_leaderboard.build_leaderboard(sample_totals(), min_games=3)
    assert "Tiny Sample" not in qualified

    fallback = readme_leaderboard.build_leaderboard(sample_totals(), min_games=10)
    assert "Tiny Sample" in fallback


def test_leaderboard_filters_by_minutes():
    table = readme_leaderboard.build_leaderboard(
        sample_totals(), min_games=1, min_minutes=25
    )
    assert "Tiny Sample" not in table
    assert "High Impact" in table
    assert "min 25 MPG" in table


def limited_totals() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "player_id": "p1",
                "player_name": "Qualified Starter",
                "team_abbr": "AAA",
                "games_played": 5,
                "minutes_per_game": 30.0,
                "points_per_game": 15.0,
                "rebounds_per_game": 5.0,
                "assists_per_game": 3.0,
                "plus_minus": 20,
            },
            {
                "player_id": "p2",
                "player_name": "Two-Game Heater",
                "team_abbr": "BBB",
                "games_played": 2,
                "minutes_per_game": 28.0,
                "points_per_game": 24.0,
                "rebounds_per_game": 4.0,
                "assists_per_game": 2.0,
                "plus_minus": 12,
            },
            {
                "player_id": "p3",
                "player_name": "Deep Bench",
                "team_abbr": "CCC",
                "games_played": 5,
                "minutes_per_game": 4.0,
                "points_per_game": 2.0,
                "rebounds_per_game": 1.0,
                "assists_per_game": 0.0,
                "plus_minus": -3,
            },
        ]
    )


def test_limited_table_lists_small_samples_outside_main_table():
    table = readme_leaderboard.build_limited_table(
        limited_totals(), main_min_games=1, main_min_minutes=10
    )

    assert "small sample" in table
    assert "under 3 GP or under 10 MPG" in table
    assert "Deep Bench" in table
    assert "Qualified Starter" not in table
    assert "Two-Game Heater" not in table


def test_limited_table_returns_note_when_everyone_qualifies():
    only_starter = limited_totals().iloc[[0]]
    table = readme_leaderboard.build_limited_table(
        only_starter, main_min_games=1, main_min_minutes=10
    )
    assert "No limited-sample rookies" in table


def test_update_readme_replaces_marked_block(monkeypatch, tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Title\n\n"
        f"{readme_leaderboard.START_MARKER}\nold table\n{readme_leaderboard.END_MARKER}\n"
        "\n## Quick Start\nkeep me\n",
        encoding="utf-8",
    )
    db = tmp_path / "preseason.db"
    db.write_bytes(b"")
    monkeypatch.setattr(
        readme_leaderboard, "load_preseason_rookie_totals", lambda _path: sample_totals()
    )

    assert readme_leaderboard.update_readme(db_path=db, readme_path=readme) is True

    text = readme.read_text(encoding="utf-8")
    assert "old table" not in text
    assert "High Impact" in text
    assert "## Quick Start\nkeep me" in text
    assert text.count(readme_leaderboard.START_MARKER) == 1


def test_update_readme_appends_section_when_markers_missing(monkeypatch, tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# Title\n", encoding="utf-8")
    db = tmp_path / "preseason.db"
    db.write_bytes(b"")
    monkeypatch.setattr(
        readme_leaderboard, "load_preseason_rookie_totals", lambda _path: sample_totals()
    )

    assert readme_leaderboard.update_readme(db_path=db, readme_path=readme) is True

    text = readme.read_text(encoding="utf-8")
    assert "## Rookie of the Year Race (Unofficial)" in text
    assert readme_leaderboard.START_MARKER in text


def test_update_readme_from_season_labels_the_phase(monkeypatch, tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# Title\n", encoding="utf-8")
    totals = sample_totals().assign(
        season_year=2027,
        last_game_date="2026-10-25",
        has_playoffs=0,
    )
    monkeypatch.setattr(
        readme_leaderboard, "load_season_totals", lambda _path: totals
    )

    assert (
        readme_leaderboard.update_readme_from_season(
            db_path=tmp_path / "season.db", readme_path=readme
        )
        is True
    )

    text = readme.read_text(encoding="utf-8")
    assert "2026-27 regular season through 2026-10-25" in text
    assert "min 10 MPG" in text


def test_update_readme_skips_missing_database(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# Title\n", encoding="utf-8")

    assert (
        readme_leaderboard.update_readme(
            db_path=tmp_path / "missing.db", readme_path=readme
        )
        is False
    )
    assert readme.read_text(encoding="utf-8") == "# Title\n"
