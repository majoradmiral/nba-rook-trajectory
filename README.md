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
_Updated 2026-11-05 · unofficial ROTY candidate ranking · 2026-27 regular season through 2026-11-02 · ranked by impact score · min 10 MPG_

| Rank | Rookie | Team | GP | MPG | PPG | RPG | APG | SPG | BPG | EFF | FG% | 3P% | Impact |
|------|--------|------|----|-----|-----|-----|-----|-----|-----|-----|-----|-----|--------|
| 1 | Darius Acuff Jr. | SAC | 6 | 36.8 | 28.5 | 4.0 | 6.8 | 0.2 | 0.2 | 22.7 | 44.0% | 35.0% | 40.7 |
| 2 | Caleb Wilson | CHI | 7 | 34.0 | 21.6 | 6.7 | 2.7 | 2.0 | 1.3 | 19.9 | 43.2% | 32.1% | 37.6 |
| 3 | Cameron Boozer | MEM | 7 | 32.0 | 17.4 | 10.3 | 5.6 | 0.3 | 0.9 | 22.6 | 37.5% | 36.4% | 37.4 |
| 4 | Yaxel Lendeborg | GS | 7 | 32.3 | 22.9 | 7.6 | 4.1 | 0.9 | 0.6 | 23.6 | 50.5% | 41.3% | 37.2 |
| 5 | AJ Dybantsa | WSH | 3 | 30.0 | 19.0 | 4.7 | 1.7 | 1.3 | 0.0 | 18.0 | 50.0% | 27.3% | 28.1 |
| 6 | Darryn Peterson | UTAH | 7 | 30.3 | 13.4 | 4.3 | 3.3 | 1.3 | 0.7 | 13.3 | 36.3% | 37.5% | 26.4 |
| 7 | Keaton Wagler | LAC | 6 | 24.3 | 11.7 | 4.3 | 3.3 | 0.5 | 0.3 | 9.8 | 25.9% | 25.9% | 21.0 |
| 8 | Mikel Brown Jr. | BKN | 5 | 23.6 | 10.8 | 2.4 | 4.0 | 0.6 | 0.0 | 7.6 | 29.8% | 25.0% | 19.1 |
| 9 | Trevon Brazile | DEN | 5 | 22.8 | 9.2 | 5.2 | 0.4 | 1.0 | 0.8 | 12.6 | 64.3% | 46.2% | 18.6 |
| 10 | Aday Mara | OKC | 6 | 19.2 | 7.2 | 6.0 | 1.3 | 0.0 | 1.8 | 11.5 | 58.1% | — | 17.7 |
<!-- TOP_PERFORMERS:END -->

## Limited Sample

Rookies who haven't cleared the main ROTY race bar yet — **under 3 games or
under 10 minutes per game**. This catches small-sample heaters, cameos and
deep-bench minutes the main ranking can't judge yet. Players already shown
above are skipped, and the table refreshes with the same command.

<!-- LIMITED_SAMPLE:START -->
_Updated 2026-11-05 · 2026-27 regular season through 2026-11-02 · small sample · under 3 GP or under 10 MPG_

| Rank | Rookie | Team | GP | MPG | PPG | RPG | APG | SPG | BPG | EFF | FG% | 3P% | Impact |
|------|--------|------|----|-----|-----|-----|-----|-----|-----|-----|-----|-----|--------|
| 1 | Graham Ike | GS | 6 | 9.0 | 4.5 | 2.3 | 0.7 | 0.3 | 0.0 | 5.7 | 50.0% | 100.0% | 8.6 |
| 2 | Tobe Awaka | CHI | 6 | 6.7 | 1.3 | 3.5 | 0.5 | 0.3 | 0.5 | 5.0 | 75.0% | — | 7.6 |
| 3 | Baba Miller | LAC | 6 | 7.0 | 1.7 | 1.8 | 0.5 | 0.3 | 0.5 | 3.3 | 50.0% | 50.0% | 5.5 |
| 4 | Tarris Reed Jr. | SA | 7 | 2.9 | 1.4 | 2.1 | 0.0 | 0.0 | 0.1 | 3.0 | 80.0% | — | 3.7 |
| 5 | Nick Martinelli | LAC | 6 | 2.8 | 2.5 | 1.0 | 0.2 | 0.0 | 0.0 | 2.8 | 66.7% | 66.7% | 3.6 |
| 6 | Ryan Conwell | MIA | 7 | 3.6 | 2.0 | 0.3 | 0.4 | 0.3 | 0.0 | 2.0 | 45.5% | 42.9% | 3.6 |
| 7 | Jaden Bradley | TOR | 7 | 2.9 | 1.3 | 0.4 | 0.6 | 0.4 | 0.0 | 2.0 | 40.0% | — | 3.2 |
| 8 | Labaron Philon Jr. | PHI | 7 | 5.0 | 1.7 | 0.7 | 0.1 | 0.0 | 0.0 | 1.0 | 38.5% | 28.6% | 2.6 |
| 9 | Ja'Kobi Gillespie | SA | 2 | 2.0 | 2.5 | 0.0 | 0.0 | 0.0 | 0.0 | 1.5 | 50.0% | 33.3% | 2.5 |
| 10 | Zuby Ejiofor | ATL | 7 | 3.4 | 0.9 | 1.0 | 0.3 | 0.0 | 0.0 | 1.1 | 28.6% | 50.0% | 2.2 |
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
weekly refresh:

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
runs the ingestion and both page builders every Monday, caches the season
database between runs so only new days are fetched, commits the refreshed page
data, and deploys `site/` to GitHub Pages.

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
