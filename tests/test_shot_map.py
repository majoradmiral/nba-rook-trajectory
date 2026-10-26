"""Tests for the all-rookie shot map builder."""

from __future__ import annotations

import json

import pandas as pd

from src import shot_map
from tests.test_timeline import sample_frames


def test_build_shot_map_keeps_only_rookies():
    games, stats, shots = sample_frames()
    payload = shot_map.build_shot_map(games, stats, shots, rookies_only=True)

    shooter_ids = {shot["player_id"] for shot in payload["shots"]}
    assert shooter_ids == {"p1"}

    player_ids = {player["player_id"] for player in payload["players"]}
    assert player_ids == {"p1", "p2"}


def test_build_shot_map_can_include_everyone():
    games, stats, shots = sample_frames()
    payload = shot_map.build_shot_map(games, stats, shots, rookies_only=False)

    player_ids = {player["player_id"] for player in payload["players"]}
    assert player_ids == {"p1", "p2", "p3"}
    assert payload["scope"] == "all"


def test_build_shot_map_totals_and_lines():
    games, stats, shots = sample_frames()
    payload = shot_map.build_shot_map(games, stats, shots)

    totals = payload["totals"]
    assert payload["season_year"] == 2027
    assert payload["season_label"] == "2026-27"
    assert totals["games"] == 3
    assert totals["games_with_shots"] == 2
    assert totals["players"] == 2
    assert totals["players_with_shots"] == 1
    assert totals["shots"] == 3
    assert totals["made"] == 2

    alpha = next(player for player in payload["players"] if player["player_id"] == "p1")
    assert alpha["name"] == "Alpha Rookie"
    assert alpha["games"] == 2
    assert alpha["shots"] == 3
    assert alpha["made"] == 2
    assert alpha["points"] == 22.0
    assert alpha["zones"]["rim"]["attempts"] == 1
    assert alpha["zones"]["mid"]["attempts"] == 1
    assert alpha["zones"]["three"]["attempts"] == 1


def test_build_shot_map_shot_rows_carry_ownership():
    games, stats, shots = sample_frames()
    payload = shot_map.build_shot_map(games, stats, shots)

    shot = payload["shots"][0]
    assert set(shot) >= {
        "player_id", "game_id", "date", "x", "y", "made", "three",
        "distance", "type", "period", "clock",
    }
    assert shot["player_id"] == "p1"
    assert shot["game_id"] == "g1"
    assert shot["date"] == "2026-10-20"
    assert shot["made"] == 1
    assert shot["three"] == 0


def test_build_shot_map_weeks_and_game_index():
    games, stats, shots = sample_frames()
    payload = shot_map.build_shot_map(games, stats, shots)

    assert len(payload["weeks"]) == 2
    first_week = payload["weeks"][0]
    assert first_week["start"] == "2026-10-19"
    assert first_week["games"] == 2
    assert first_week["shots"] == 3

    second_week = payload["weeks"][1]
    assert second_week["start"] == "2026-10-26"
    assert second_week["games"] == 1
    assert second_week["shots"] == 0

    game_ids = [game["game_id"] for game in payload["games"]]
    assert game_ids == ["g1", "g2", "g3"]

    g1 = next(game for game in payload["games"] if game["game_id"] == "g1")
    assert g1["shots"] == 2
    assert g1["players"] == 1
    assert g1["home"]["abbr"] == "HOM"


def test_build_shot_map_handles_empty_input():
    payload = shot_map.build_shot_map(pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    assert payload["season_year"] is None
    assert payload["weeks"] == []
    assert payload["players"] == []
    assert payload["shots"] == []
    assert payload["totals"] == {}


def test_write_shot_map_writes_json_and_js(tmp_path):
    games, stats, shots = sample_frames()
    payload = shot_map.build_shot_map(games, stats, shots)

    json_path, js_path = shot_map.write_shot_map(payload, tmp_path)

    assert json.loads(json_path.read_text(encoding="utf-8"))["totals"]["shots"] == 3
    wrapper = js_path.read_text(encoding="utf-8")
    assert wrapper.startswith("window.SHOTS_DATA = ")
    assert json.loads(wrapper[len("window.SHOTS_DATA = "):].rstrip().rstrip(";"))["totals"]["shots"] == 3
