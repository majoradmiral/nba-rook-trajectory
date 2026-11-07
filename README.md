# nba-rook-trajectory

Predicts second-year efficiency/minutes jump from rookie-year + Summer League stats. Regression + classification tiers.

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
_Updated 2026-11-07 · unofficial ROTY candidate ranking · 2026-27 regular season through 2026-11-06 · ranked by impact score · min 10 MPG_

| Rank | Rookie | Team | GP | MPG | PPG | RPG | APG | SPG | BPG | EFF | FG% | 3P% | Impact |
|------|--------|------|----|-----|-----|-----|-----|-----|-----|-----|-----|-----|--------|
| 1 | Darius Acuff Jr. | SAC | 9 | 36.8 | 25.2 | 3.7 | 7.1 | 0.9 | 0.1 | 18.9 | 40.2% | 31.0% | 38.8 |
| 2 | Yaxel Lendeborg | GS | 9 | 31.7 | 21.0 | 7.1 | 4.1 | 1.1 | 0.6 | 22.0 | 49.2% | 39.6% | 35.8 |
| 3 | Cameron Boozer | MEM | 9 | 32.0 | 15.6 | 10.0 | 5.2 | 0.3 | 0.7 | 19.3 | 33.9% | 31.6% | 34.3 |
| 4 | Caleb Wilson | CHI | 8 | 32.5 | 19.5 | 6.5 | 2.4 | 1.9 | 1.1 | 17.1 | 40.9% | 30.2% | 34.1 |
| 5 | AJ Dybantsa | WSH | 5 | 31.6 | 15.4 | 5.8 | 2.2 | 1.6 | 0.0 | 15.2 | 41.5% | 30.8% | 27.5 |
| 6 | Darryn Peterson | UTAH | 9 | 30.2 | 13.6 | 3.8 | 3.9 | 1.2 | 0.9 | 13.9 | 36.9% | 34.1% | 26.8 |
| 7 | Keaton Wagler | LAC | 8 | 23.9 | 12.0 | 4.1 | 3.2 | 0.6 | 0.2 | 11.5 | 30.9% | 35.1% | 21.6 |
| 8 | Mikel Brown Jr. | BKN | 6 | 23.0 | 12.0 | 2.3 | 4.0 | 0.7 | 0.2 | 9.0 | 33.8% | 29.7% | 20.3 |
| 9 | Brayden Burries | MIL | 9 | 20.1 | 10.2 | 5.2 | 2.0 | 0.6 | 0.1 | 11.7 | 44.3% | 21.9% | 19.7 |
| 10 | Trevon Brazile | DEN | 7 | 22.1 | 8.0 | 6.4 | 0.4 | 0.9 | 0.6 | 12.1 | 55.0% | 31.6% | 18.4 |
<!-- TOP_PERFORMERS:END -->

## Limited Sample

Rookies who haven't cleared the main ROTY race bar yet — **under 3 games or
under 10 minutes per game**. This catches small-sample heaters, cameos and
deep-bench minutes the main ranking can't judge yet. Players already shown
above are skipped, and the table refreshes with the same command.

<!-- LIMITED_SAMPLE:START -->
_Updated 2026-11-07 · 2026-27 regular season through 2026-11-06 · small sample · under 3 GP or under 10 MPG_

| Rank | Rookie | Team | GP | MPG | PPG | RPG | APG | SPG | BPG | EFF | FG% | 3P% | Impact |
|------|--------|------|----|-----|-----|-----|-----|-----|-----|-----|-----|-----|--------|
| 1 | Graham Ike | GS | 8 | 8.4 | 4.4 | 2.1 | 0.6 | 0.4 | 0.1 | 5.8 | 52.0% | 100.0% | 8.6 |
| 2 | Tobe Awaka | CHI | 6 | 6.7 | 1.3 | 3.5 | 0.5 | 0.2 | 0.5 | 4.8 | 75.0% | — | 7.3 |
| 3 | Zuby Ejiofor | ATL | 9 | 6.2 | 3.0 | 1.7 | 1.0 | 0.3 | 0.0 | 4.4 | 57.9% | 42.9% | 6.7 |
| 4 | Baba Miller | LAC | 8 | 7.1 | 2.0 | 1.9 | 0.6 | 0.4 | 0.5 | 4.0 | 66.7% | 50.0% | 6.1 |
| 5 | Ryan Conwell | MIA | 9 | 8.0 | 3.0 | 0.6 | 0.8 | 0.6 | 0.0 | 3.1 | 39.1% | 40.0% | 5.8 |
| 6 | Jaylin Sellers | CHI | 8 | 5.6 | 2.9 | 0.5 | 0.6 | 0.2 | 0.1 | 2.0 | 33.3% | 37.5% | 4.7 |
| 7 | Hannes Steinbach | CHA | 10 | 5.0 | 1.2 | 1.8 | 0.2 | 0.0 | 0.3 | 2.4 | 46.2% | — | 4.0 |
| 8 | Norchad Omier | CLE | 1 | 3.0 | 0.0 | 2.0 | 1.0 | 0.0 | 0.0 | 3.0 | — | — | 3.9 |
| 9 | Jaden Bradley | TOR | 9 | 3.6 | 1.6 | 0.4 | 0.6 | 0.4 | 0.0 | 2.1 | 42.9% | — | 3.5 |
| 10 | Nick Martinelli | LAC | 8 | 2.4 | 1.9 | 0.9 | 0.2 | 0.0 | 0.0 | 2.2 | 60.0% | 66.7% | 3.0 |
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

The pages deploy to **GitHub Pages** on every change under `site/` and after each
daily refresh:

https://majoradmiral.github.io/nba-rook-trajectory/

One-time setup: open **Settings → Pages**, set **Source** to **GitHub Actions**,
then run **Deploy Site** once from the Actions tab. The workflow can't enable
Pages for you because `GITHUB_TOKEN` isn't allowed to change repository settings.

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
between runs so only new days are fetched, commits the refreshed page data, and
deploys `site/` to GitHub Pages.

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
.github/
└── workflows/
    ├── weekly_timeline.yml   # Monday refresh, cache, commit and deploy
    └── deploy_pages.yml      # Deploy site/ when it changes
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
