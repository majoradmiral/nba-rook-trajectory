"""Tests for the README leaderboard auto-inject."""

from __future__ import annotations

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

    assert "| # | Player | Team | GP | MPG | PPG | RPG | APG | FG% | 3P% | +/- | Score |" in table
    assert "ranked by performance score" in table
    assert table.index("Volume Scorer") < table.index("High Impact")
    assert "+10.0" in table


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
    assert "## Top Performers" in text
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
