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
                "points_per_game": 10.0,
                "assists_per_game": 4.0,
                "rebounds_per_game": 5.0,
                "plus_minus": 40,
            },
            {
                "player_name": "Volume Scorer",
                "team_abbr": "BBB",
                "games_played": 5,
                "points_per_game": 20.0,
                "assists_per_game": 1.0,
                "rebounds_per_game": 2.0,
                "plus_minus": 5,
            },
            {
                "player_name": "Tiny Sample",
                "team_abbr": "CCC",
                "games_played": 1,
                "points_per_game": 30.0,
                "assists_per_game": 3.0,
                "rebounds_per_game": 3.0,
                "plus_minus": 99,
            },
        ]
    )


def test_leaderboard_ranks_by_plus_minus_per_game():
    table = readme_leaderboard.build_leaderboard(sample_totals(), min_games=3)

    assert "| # | Player | Team | PPG | APG | RPG | +/- |" in table
    assert table.index("High Impact") < table.index("Volume Scorer")
    assert "+10.0" in table


def test_leaderboard_excludes_small_samples_but_falls_back():
    qualified = readme_leaderboard.build_leaderboard(sample_totals(), min_games=3)
    assert "Tiny Sample" not in qualified

    fallback = readme_leaderboard.build_leaderboard(sample_totals(), min_games=10)
    assert "Tiny Sample" in fallback


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
