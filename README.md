# nba-rook-trajectory

Predicts second-year efficiency/minutes jump from rookie-year + Summer League stats. Regression + classification tiers.

## Top Performers

Preseason rookies ranked by plus/minus per game (team impact), then points.
Auto-refreshed on every `python -m src.preseason_db` run — no manual editing.

<!-- TOP_PERFORMERS:START -->
_Updated 2026-10-19 · ranked by +/- per game · min 3 games_

| # | Player | Team | PPG | APG | RPG | +/- |
|---|--------|------|-----|-----|-----|-----|
| 1 | Yaxel Lendeborg | GS | 15.6 | 4.0 | 7.4 | +8.6 |
| 2 | Sergio de Larrea | DAL | 9.5 | 5.0 | 3.5 | +6.2 |
| 3 | Aday Mara | OKC | 13.4 | 2.8 | 7.6 | +6.0 |
| 4 | Cameron Boozer | MEM | 14.0 | 3.0 | 5.5 | +5.5 |
| 5 | Kingston Flemings | ATL | 10.2 | 4.2 | 2.0 | +4.8 |
| 6 | Dillon Mitchell | BOS | 5.8 | 2.5 | 5.2 | +4.8 |
| 7 | Baba Miller | LAC | 11.3 | 0.7 | 5.0 | +3.7 |
| 8 | Felix Okpara | WSH | 4.8 | 0.8 | 3.5 | +3.5 |
| 9 | Alpha Diallo | DEN | 4.2 | 1.2 | 3.0 | +3.0 |
| 10 | Braden Smith | IND | 3.0 | 5.5 | 2.8 | +2.2 |
<!-- TOP_PERFORMERS:END -->

## Quick Start

```bash
pip install -r requirements.txt
python -m src.update_sl
python -m src.preseason_db
```

`src.preseason_db` refreshes `data/processed/nba_preseason.db` from ESPN's completed
NBA preseason games. It identifies first-year players from the season's team
rosters (`experience.years == 0`) and stores only their player box scores in
`preseason_rookie_game_stats`; `preseason_rookie_totals` contains season totals,
per-game rates, and shooting percentages. Game metadata is stored separately in
`preseason_games`. After the refresh the CLI prints a points leaderboard and
rewrites the **Top Performers** table above (`python -m src.readme_leaderboard`
does the README step on its own).

## Project Structure

```
src/
├── config.py                 # Paths, SL schedule constants
├── pipeline.py               # Rookie stats + inference builder
├── espn_client.py            # ESPN scoreboard API
├── preseason_db.py           # Preseason rookie box-score SQLite tables
├── readme_leaderboard.py     # Auto-injects Top Performers table into README
├── summer_league_scraper.py  # Multi-source SL scraper
└── update_sl.py              # Automated daily updater
data/
├── raw/                      # Raw parquet + HTML
└── processed/                # Training + inference frames
```
