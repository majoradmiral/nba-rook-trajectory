# nba-rook-trajectory

Predicts second-year efficiency/minutes jump from rookie-year + Summer League stats. Regression + classification tiers.

## Top Performers

The best-performing rookies so far, ranked by a per-game performance score
(`PTS + 1.2×REB + 1.5×AST + 2×STL + 2×BLK − TOV`). The table uses regular-season
and playoff games as soon as they exist, falling back to preseason before
opening night. The weekly shot charts below spotlight the same ranking.
Auto-refreshed on every `python -m src.timeline` run — no manual editing.

<!-- TOP_PERFORMERS:START -->
_Updated 2026-10-29 · 2026-27 regular season through 2026-10-25 · ranked by performance score · min 10 MPG_

| # | Player | Team | GP | MPG | PPG | RPG | APG | FG% | 3P% | +/- | Score |
|---|--------|------|----|-----|-----|-----|-----|-----|-----|-----|-------|
| 1 | Yaxel Lendeborg | GS | 2 | 36.5 | 22.0 | 11.0 | 5.5 | 43.3% | 50.0% | -2.0 | 43.5 |
| 2 | Darius Acuff Jr. | SAC | 2 | 36.5 | 27.5 | 2.5 | 5.5 | 38.8% | 20.0% | -5.0 | 37.8 |
| 3 | Cameron Boozer | MEM | 3 | 33.7 | 16.0 | 11.7 | 5.0 | 28.6% | 30.0% | +15.0 | 37.5 |
| 4 | Caleb Wilson | CHI | 3 | 34.3 | 22.3 | 8.0 | 1.3 | 40.7% | 17.4% | -11.3 | 36.6 |
| 5 | Trevon Brazile | DEN | 1 | 28.0 | 17.0 | 9.0 | 0.0 | 54.5% | 42.9% | +10.0 | 31.8 |
| 6 | Graham Ike | GS | 2 | 19.0 | 11.0 | 6.0 | 1.5 | 45.0% | 100.0% | -11.0 | 21.9 |
| 7 | Keaton Wagler | LAC | 2 | 25.0 | 12.0 | 4.0 | 3.5 | 26.7% | 33.3% | -1.0 | 20.1 |
| 8 | Darryn Peterson | UTAH | 3 | 30.3 | 10.7 | 3.3 | 2.0 | 40.6% | 14.3% | -5.3 | 19.7 |
| 9 | Allen Graves | TOR | 3 | 15.0 | 6.0 | 4.3 | 1.3 | 61.5% | 20.0% | +2.7 | 17.9 |
| 10 | Mikel Brown Jr. | BKN | 2 | 20.0 | 7.0 | 2.5 | 4.0 | 27.8% | 33.3% | -4.5 | 16.5 |
<!-- TOP_PERFORMERS:END -->

## Limited Sample

Rookies who haven't cleared the Top Performers bar yet — **under 3 games or
under 10 minutes per game**. This catches small-sample heaters, cameos and
deep-bench minutes the main ranking can't judge yet. Players already shown
above are skipped, and the table refreshes with the same command.

<!-- LIMITED_SAMPLE:START -->
_Updated 2026-10-29 · 2026-27 regular season through 2026-10-25 · small sample · under 3 GP or under 10 MPG_

| # | Player | Team | GP | MPG | PPG | RPG | APG | FG% | 3P% | +/- | Score |
|---|--------|------|----|-----|-----|-----|-----|-----|-----|-----|-------|
| 1 | Aday Mara | OKC | 2 | 13.0 | 4.5 | 2.5 | 1.0 | 57.1% | — | +6.0 | 9.5 |
| 2 | Bryce Hopkins | DEN | 1 | 19.0 | 2.0 | 2.0 | 1.0 | 50.0% | 0.0% | -9.0 | 5.9 |
| 3 | Emanuel Sharp | SAC | 2 | 14.0 | 4.0 | 0.5 | 0.5 | 37.5% | 50.0% | +2.5 | 5.8 |
| 4 | Tobe Awaka | CHI | 3 | 4.7 | 0.7 | 2.3 | 0.7 | 100.0% | — | -2.0 | 5.8 |
| 5 | Hannes Steinbach | CHA | 3 | 4.0 | 2.0 | 1.7 | 0.0 | 60.0% | — | -4.0 | 4.0 |
| 6 | Tobi Lawal | DAL | 3 | 1.7 | 1.7 | 0.3 | 0.3 | 50.0% | 50.0% | +2.0 | 3.2 |
| 7 | Ryan Conwell | MIA | 3 | 3.3 | 1.7 | 0.3 | 0.7 | 40.0% | 33.3% | -0.7 | 3.1 |
| 8 | Labaron Philon Jr. | PHI | 3 | 5.7 | 1.7 | 0.7 | 0.3 | 40.0% | 33.3% | +3.3 | 3.0 |
| 9 | Bennett Stirtz | OKC | 2 | 6.0 | 1.0 | 0.5 | 0.0 | 33.3% | 0.0% | -3.5 | 2.6 |
| 10 | Jaden Bradley | TOR | 3 | 3.7 | 2.0 | 0.3 | 0.3 | 50.0% | — | +3.0 | 2.6 |
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
**Top Performers** table above (`python -m src.readme_leaderboard` updates just
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
