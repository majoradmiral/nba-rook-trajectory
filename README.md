# nba-rook-trajectory

Predicts second-year efficiency/minutes jump from rookie-year + Summer League stats. Regression + classification tiers.

## Top Performers

Rookies ranked by plus/minus per game (team impact), then points — regular season
and playoffs first, preseason as the fallback. Auto-refreshed on every
`python -m src.timeline` run — no manual editing.

<!-- TOP_PERFORMERS:START -->
_Updated 2026-10-24 · ranked by +/- per game · min 3 games_

| # | Player | Team | PPG | APG | RPG | +/- |
|---|--------|------|-----|-----|-----|-----|
| 1 | Cameron Boozer | MEM | 7.0 | 5.0 | 11.0 | +32.0 |
| 2 | Aday Mara | OKC | 7.0 | 1.0 | 2.0 | +9.0 |
| 3 | Allen Graves | TOR | 5.0 | 0.0 | 5.0 | +8.0 |
| 4 | Christian Anderson | CHA | 0.0 | 2.0 | 2.0 | +5.0 |
| 5 | Ryan Conwell | MIA | 0.0 | 2.0 | 0.0 | +4.0 |
| 6 | Jaden Bradley | TOR | 0.0 | 0.0 | 0.0 | +1.0 |
| 7 | Ja'Kobi Gillespie | SA | 2.0 | 0.0 | 0.0 | +0.0 |
| 8 | Labaron Philon Jr. | PHI | 0.0 | 0.0 | 0.0 | +0.0 |
| 9 | Maliq Brown | SA | 0.0 | 1.0 | 0.0 | +0.0 |
| 10 | Tarris Reed Jr. | SA | 0.0 | 0.0 | 0.0 | +0.0 |
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

## Shot Timeline

`site/index.html` is a vanilla-JS page (no build step) that shows a weekly
timeline of the **top-ranked** rookies with their shot attempts plotted on a
court fixture.

- One row per week of the season, newest week selected on open.
- **Three featured players per week** — the highest-ranked rookies who actually
  suited up that week, ranked by +/- per game (cumulative season to date).
- Every card carries the player's shot chart (made = green, missed = red X),
  rim / mid-range / three splits, and their week and season lines.
- Recent games panel with the tracked players' box-score lines.
- The page polls `site/data/timeline.json` every minute, so it updates itself
  without a reload; arrow keys step through the weeks and the play button
  auto-advances week by week.
- Links are shareable — `?phase=all&week=3` opens a specific week of any phase.

```bash
python -m src.season_tracker     # pull games, box scores and shot charts
python -m src.timeline           # rebuild site/data/timeline.json
python -m http.server 8777 --directory site   # then open http://localhost:8777
```

`src.season_tracker` ingests every completed game — preseason, regular season and
playoffs — into `data/processed/nba_season.db`: one row per game, one row per
player per game, and one row per shot with court coordinates (ESPN reports x
across the 50 ft width of the floor and y from the baseline; the rim sits 1.575 ft
inside the baseline). Only new games are re-fetched, so weekly runs are quick.

`src.timeline` buckets the games into weeks, ranks the rookies as of each week,
and writes `site/data/timeline.json` (plus a `timeline.js` wrapper so the page
also works when opened straight from disk). The **Weekly Shot Timeline** workflow
runs the ingestion and both page builders every Monday and commits the refreshed
page data, so the published timeline stays current without any manual step.

## All Rookie Shots

`site/shots.html` is the companion view: instead of spotlighting three players a
week, it plots **every shot every rookie has taken** on one half court and lets
you work out whose shot is whose.

- Each rookie owns a colour (assigned in the sidebar) — made = filled dot,
  missed = hollow X in the shooter's colour.
- Hover a shot for the shooter, shot type, distance, result, date and clock;
  click it to pin a detail card with the player's season line and zone splits.
- Click a rookie in the rail to isolate their attempts (everything else dims);
  the search box narrows the list by name or team.
- Scope the court to the full season, one week or a single game from the week
  rail and game list — arrow keys step through the weeks, `Esc` clears the
  selection and `/` jumps to the search box.
- Links are shareable — `?week=2&player=4432737` reopens the same view.

```bash
python -m src.shot_map     # rebuild site/data/shots.json from nba_season.db
python -m http.server 8777 --directory site   # then open http://localhost:8777/shots.html
```

`src.shot_map` reuses the season database written by `src.season_tracker`,
filters the shots down to rookies (`is_rookie = 1`), and ships a player index,
a game index and one row per attempt. It runs automatically alongside
`src.timeline` in the weekly workflow.

## Project Structure

```
src/
├── config.py                 # Paths, SL schedule constants
├── pipeline.py               # Rookie stats + inference builder
├── espn_client.py            # ESPN scoreboard API
├── preseason_db.py           # Preseason rookie box-score SQLite tables
├── season_tracker.py         # Full-season games, box scores and shot charts
├── timeline.py               # Weekly top-3 timeline builder for the site
├── shot_map.py               # All-rookie shot map builder for the site
├── readme_leaderboard.py     # Auto-injects Top Performers table into README
├── summer_league_scraper.py  # Multi-source SL scraper
└── update_sl.py              # Automated daily updater
site/
├── index.html                # Weekly shot timeline page
├── shots.html                # All-rookie shot map page
├── app.js                    # Timeline, court renderer, auto-refresh
├── shots.js                  # Shot map: colours, isolation, scopes
├── court.js                  # Shared half-court fixture + shot renderer
├── styles.css
└── data/                     # Generated payloads the pages read
    ├── timeline.json
    └── shots.json
data/
├── raw/                      # Raw parquet + HTML
└── processed/                # Training + inference frames, season database
```
