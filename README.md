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
_Updated 2026-11-11 · unofficial ROTY candidate ranking · 2026-27 regular season through 2026-11-10 · ranked by impact score · min 10 MPG_

| Rank | Rookie | Team | GP | MPG | PPG | RPG | APG | SPG | BPG | EFF | FG% | 3P% | Impact |
|------|--------|------|----|-----|-----|-----|-----|-----|-----|-----|-----|-----|--------|
| 1 | Darius Acuff Jr. | SAC | 10 | 37.5 | 27.6 | 3.9 | 7.7 | 0.8 | 0.1 | 23.3 | 44.1% | 35.4% | 42.0 |
| 2 | Yaxel Lendeborg | GS | 10 | 32.0 | 22.3 | 7.6 | 4.2 | 1.0 | 0.8 | 24.2 | 52.9% | 45.6% | 37.6 |
| 3 | Caleb Wilson | CHI | 8 | 33.8 | 21.1 | 6.5 | 2.4 | 2.0 | 1.1 | 18.8 | 42.7% | 32.3% | 36.0 |
| 4 | Cameron Boozer | MEM | 10 | 32.1 | 16.2 | 9.7 | 5.5 | 0.4 | 0.6 | 19.8 | 36.4% | 29.0% | 34.7 |
| 5 | Darryn Peterson | UTAH | 11 | 30.7 | 15.7 | 4.0 | 3.9 | 1.2 | 0.7 | 15.3 | 41.1% | 37.7% | 28.4 |
| 6 | AJ Dybantsa | WSH | 7 | 32.3 | 16.7 | 6.1 | 2.1 | 1.1 | 0.3 | 15.3 | 43.3% | 27.3% | 28.0 |
| 7 | Aday Mara | OKC | 10 | 21.1 | 8.9 | 6.6 | 1.5 | 0.0 | 1.9 | 14.2 | 62.9% | 100.0% | 21.3 |
| 8 | Mikel Brown Jr. | BKN | 7 | 23.3 | 12.9 | 2.1 | 3.9 | 0.7 | 0.1 | 9.3 | 34.6% | 31.1% | 20.8 |
| 9 | Keaton Wagler | LAC | 9 | 22.6 | 11.9 | 3.3 | 3.2 | 0.6 | 0.2 | 10.4 | 31.2% | 33.3% | 20.3 |
| 10 | Brayden Burries | MIL | 11 | 21.5 | 9.8 | 5.3 | 2.3 | 0.5 | 0.2 | 11.6 | 42.5% | 22.5% | 19.8 |
<!-- TOP_PERFORMERS:END -->

## Limited Sample

Rookies who haven't cleared the main ROTY race bar yet — **under 3 games or
under 10 minutes per game**. This catches small-sample heaters, cameos and
deep-bench minutes the main ranking can't judge yet. Players already shown
above are skipped, and the table refreshes with the same command.

<!-- LIMITED_SAMPLE:START -->
_Updated 2026-11-11 · 2026-27 regular season through 2026-11-10 · small sample · under 3 GP or under 10 MPG_

| Rank | Rookie | Team | GP | MPG | PPG | RPG | APG | SPG | BPG | EFF | FG% | 3P% | Impact |
|------|--------|------|----|-----|-----|-----|-----|-----|-----|-----|-----|-----|--------|
| 1 | Baba Miller | LAC | 9 | 9.3 | 4.1 | 2.3 | 0.9 | 0.6 | 0.8 | 6.6 | 55.0% | 40.0% | 10.1 |
| 2 | Graham Ike | GS | 8 | 8.4 | 3.9 | 2.5 | 0.8 | 0.2 | 0.1 | 5.5 | 50.0% | 75.0% | 8.4 |
| 3 | Zuby Ejiofor | ATL | 11 | 7.1 | 3.1 | 1.9 | 0.8 | 0.3 | 0.2 | 4.7 | 58.3% | 44.4% | 7.1 |
| 4 | Tobe Awaka | CHI | 7 | 5.7 | 1.1 | 3.0 | 0.4 | 0.3 | 0.4 | 4.3 | 75.0% | — | 6.5 |
| 5 | Hannes Steinbach | CHA | 11 | 5.7 | 1.3 | 1.9 | 0.2 | 0.0 | 0.3 | 2.4 | 43.8% | — | 4.0 |
| 6 | Tarris Reed Jr. | SA | 11 | 3.7 | 1.5 | 2.0 | 0.2 | 0.0 | 0.2 | 2.8 | 63.6% | — | 3.9 |
| 7 | Norchad Omier | CLE | 3 | 5.0 | 0.0 | 1.7 | 1.0 | 0.0 | 0.0 | 2.3 | 0.0% | 0.0% | 3.5 |
| 8 | Jaden Bradley | TOR | 10 | 4.1 | 1.4 | 0.5 | 0.8 | 0.4 | 0.0 | 2.1 | 42.9% | — | 3.5 |
| 9 | Nick Martinelli | LAC | 8 | 2.4 | 2.1 | 0.8 | 0.1 | 0.0 | 0.0 | 2.4 | 70.0% | 66.7% | 3.0 |
| 10 | Labaron Philon Jr. | PHI | 11 | 4.1 | 1.5 | 0.6 | 0.5 | 0.0 | 0.0 | 1.0 | 35.3% | 25.0% | 2.6 |
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
