# nba-rook-trajectory

NBA rookie performance tracking, weekly shot charts, and an unofficial 2026-27 Rookie of the Year race.

## Rookie of the Year Race (Unofficial)

An unofficial, stats-based Rookie of the Year watchlist — not an award ballot
or prediction of actual votes. Candidates are ranked by the transparent
per-game impact score (`PTS + 1.2×REB + 1.5×AST + 2×STL + 2×BLK − TOV`).
Traditional box-score production, steals, blocks, shooting percentages, and
box-score efficiency (`PTS + REB + AST + STL + BLK − missed FG − missed FT −
TOV`) are shown to make the race easier to compare; efficiency is a separate
signal, not added to impact. The table uses regular-season and playoff games
as soon as they exist, falling back to preseason before opening night. Weekly
shot charts spotlight the same rookie class.
Auto-refreshed on every `python -m src.timeline` run — no manual editing.

<!-- TOP_PERFORMERS:START -->
_Updated 2026-11-25 · unofficial ROTY candidate ranking · 2026-27 regular season through 2026-11-24 · ranked by impact score · min 10 MPG_

| Rank | Rookie | Team | GP | MPG | PPG | RPG | APG | SPG | BPG | EFF | FG% | 3P% | Impact |
|------|--------|------|----|-----|-----|-----|-----|-----|-----|-----|-----|-----|--------|
| 1 | Darius Acuff Jr. | SAC | 17 | 36.6 | 24.6 | 3.4 | 7.2 | 0.8 | 0.2 | 18.5 | 40.3% | 32.1% | 37.7 |
| 2 | Cameron Boozer | MEM | 16 | 30.8 | 16.6 | 9.2 | 5.3 | 0.8 | 0.8 | 21.4 | 41.7% | 32.2% | 35.6 |
| 3 | Yaxel Lendeborg | GS | 17 | 31.7 | 19.2 | 7.4 | 3.6 | 1.0 | 0.8 | 19.6 | 45.2% | 36.7% | 34.0 |
| 4 | Caleb Wilson | CHI | 10 | 30.7 | 18.9 | 6.2 | 1.9 | 1.8 | 0.9 | 16.5 | 42.0% | 32.4% | 31.9 |
| 5 | AJ Dybantsa | WSH | 15 | 34.3 | 16.7 | 7.2 | 3.1 | 1.2 | 0.3 | 16.4 | 42.0% | 24.6% | 30.7 |
| 6 | Darryn Peterson | UTAH | 19 | 30.3 | 15.9 | 4.5 | 4.1 | 1.1 | 0.6 | 15.2 | 40.1% | 31.0% | 28.9 |
| 7 | Brayden Burries | MIL | 18 | 23.1 | 11.4 | 5.7 | 2.5 | 0.9 | 0.2 | 13.8 | 45.5% | 31.3% | 22.8 |
| 8 | Aday Mara | OKC | 18 | 19.9 | 8.9 | 6.3 | 1.7 | 0.1 | 1.5 | 14.1 | 64.9% | 100.0% | 20.5 |
| 9 | Keaton Wagler | LAC | 16 | 21.8 | 11.2 | 3.5 | 2.9 | 0.8 | 0.1 | 10.7 | 34.4% | 34.3% | 19.8 |
| 10 | Mikel Brown Jr. | BKN | 12 | 23.4 | 12.4 | 2.0 | 3.8 | 0.7 | 0.1 | 9.2 | 36.4% | 36.6% | 19.5 |
<!-- TOP_PERFORMERS:END -->

## Limited Sample

Rookies who haven't cleared the main ROTY race bar yet — **under 3 games or
under 10 minutes per game**. This catches small-sample heaters, cameos and
deep-bench minutes the main ranking can't judge yet. Players already shown
above are skipped, and the table refreshes with the same command.

<!-- LIMITED_SAMPLE:START -->
_Updated 2026-11-25 · 2026-27 regular season through 2026-11-24 · small sample · under 3 GP or under 10 MPG_

| Rank | Rookie | Team | GP | MPG | PPG | RPG | APG | SPG | BPG | EFF | FG% | 3P% | Impact |
|------|--------|------|----|-----|-----|-----|-----|-----|-----|-----|-----|-----|--------|
| 1 | Graham Ike | GS | 15 | 8.2 | 3.9 | 2.1 | 0.9 | 0.3 | 0.4 | 5.3 | 45.5% | 45.5% | 8.7 |
| 2 | Norchad Omier | CLE | 10 | 8.5 | 2.3 | 3.1 | 0.9 | 0.4 | 0.2 | 6.2 | 62.5% | 25.0% | 8.5 |
| 3 | Zuby Ejiofor | ATL | 16 | 8.4 | 3.1 | 2.1 | 0.8 | 0.2 | 0.2 | 4.4 | 48.8% | 37.5% | 7.2 |
| 4 | Jaylin Sellers | CHI | 10 | 6.9 | 3.5 | 0.6 | 1.2 | 0.4 | 0.1 | 3.7 | 42.9% | 42.1% | 6.6 |
| 5 | Baba Miller | LAC | 16 | 6.7 | 2.9 | 1.5 | 0.6 | 0.3 | 0.4 | 4.1 | 55.6% | 37.5% | 6.5 |
| 6 | Ja'Kobi Gillespie | SA | 3 | 6.3 | 2.7 | 0.7 | 1.3 | 0.3 | 0.0 | 3.7 | 42.9% | 33.3% | 6.1 |
| 7 | Tobe Awaka | CHI | 9 | 4.4 | 0.9 | 2.3 | 0.3 | 0.1 | 0.3 | 3.2 | 75.0% | — | 4.9 |
| 8 | Bryce Hopkins | DEN | 13 | 8.0 | 2.9 | 1.2 | 0.2 | 0.2 | 0.0 | 3.1 | 58.3% | 40.0% | 4.6 |
| 9 | Tarris Reed Jr. | SA | 18 | 4.2 | 1.4 | 2.1 | 0.2 | 0.1 | 0.2 | 2.9 | 56.2% | 0.0% | 4.4 |
| 10 | Hannes Steinbach | CHA | 13 | 5.2 | 1.3 | 1.7 | 0.2 | 0.1 | 0.2 | 2.2 | 44.4% | — | 3.9 |
<!-- LIMITED_SAMPLE:END -->

## Quick Start

```bash
pip install -r requirements.txt
python -m src.update_sl
python -m src.season_tracker   # pull every completed game so far
python -m src.timeline          # rebuild shot charts + README leaderboard
```

`src.season_tracker` refreshes `data/processed/nba_season.db` from ESPN's
completed preseason, regular-season and playoff games. It identifies first-year
players from the season's team rosters (`experience.years == 0`) and stores every
player box score plus every located shot. Only new days are fetched, so reruns are
quick. `src.timeline` then rebuilds the weekly shot charts and rewrites the
**ROTY Race** table above (`python -m src.readme_leaderboard` updates just
the README).

Before the regular season starts, the same commands fall back to preseason data:

```bash
python -m src.preseason_db
python -m src.readme_leaderboard --preseason
```

## Live Site

The pages are generated locally — no GitHub Pages deployment.

To view locally:
```bash
python -m http.server 8777 --directory site   # then open http://localhost:8777
```

GitHub Pages automation removed. Re-enable after playoffs if desired.

## Shot Timeline

`site/index.html` is a vanilla-JS page (no build step) that shows a weekly
timeline of the **best-performing** rookies with their shot attempts plotted on
a court fixture.

- One row per week of the season, newest week selected on open.
- **Three featured players per week** — the highest-ranked rookies who actually
  suited up that week, using the same performance score as the README table
  (cumulative regular season + playoffs once the season starts).
- Every card carries the player's shot chart (made = green, missed = red X),
  rim / mid-range / three splits, and their week and season lines.
- Recent games panel with the latest completed NBA matches and tracked rookies'
  box-score lines.
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
inside the baseline). Only new games are re-fetched, so daily runs are quick.

`src.timeline` buckets the games into weeks, ranks the rookies as of each week,
and writes `site/data/timeline.json` (plus a `timeline.js` wrapper so the page
also works when opened straight from disk). The **Daily NBA Timeline Refresh** workflow
runs the ingestion and both page builders every day, caches the season database
between runs so only new days are fetched, and commits the refreshed page data.

## All Rookie Shots

`site/shots.html` is the companion view: instead of spotlighting three players a
week, it plots **every shot every rookie has taken** and lets you work out whose
shot is whose. By default the court is split into two lanes — **Scored** and
**Missed** — so made-shot locations stay readable instead of being buried under
X marks. The `Separate misses` toggle restores the single overlaid court.

- Each rookie owns a colour (assigned in the sidebar) — made = filled dot,
  missed = hollow X in the shooter's colour. Locations are preserved in both
  lanes, and the toggle state is stored in the URL (`?split=0` for the overlay).
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
a game index and one row per attempt.

## Project Structure

```
.github/
└── workflows/
    └── weekly_timeline.yml   # Daily refresh, cache, commit
src/
├── config.py                 # Paths, SL schedule constants
├── pipeline.py               # Rookie stats + inference builder
├── espn_client.py            # ESPN scoreboard API
├── preseason_db.py           # Preseason rookie box-score SQLite tables
├── season_tracker.py         # Full-season games, box scores and shot charts
├── timeline.py               # Weekly top-3 timeline builder for the site
├── shot_map.py               # All-rookie shot map builder for the site
├── readme_leaderboard.py     # Auto-injects the unofficial ROTY race into README
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
