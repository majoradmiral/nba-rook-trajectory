# nba-rook-trajectory

Predicts second-year efficiency/minutes jump from rookie-year + Summer League stats. Regression + classification tiers.

## Timeline Review

Weekly sprint history is tracked via git commits. To review progress:

```bash
# Full commit log
git log --oneline --all

# This week's changes
git log --oneline --since="1 week ago"

# Detailed diff for a specific week
git log --since="1 week ago" --pretty=format:"%h %ad %s" --date=short

# See what files changed this week
git diff <last-week-hash>..HEAD --stat
```

### Current Status

| Date | Milestone | Commit |
|------|-----------|--------|
| Jul 5 | Initial commit — project scaffold | `325fe4b` |
| Jul 8 | SL scraper: NBA API + CDN + box scores | `31e4452` |
| Jul 12 | Config, pipeline, ESPN client, updater fix | `2542dfd` |

### How to Update Weekly

1. Run `python -m src.update_sl` to refresh Summer League data
2. Commit with a descriptive message: `git commit -m "week(N): <summary>"`
3. Update the table above with the new milestone

## Quick Start

```bash
pip install -r requirements.txt
python -m src.update_sl
```

## Project Structure

```
src/
├── config.py                 # Paths, SL schedule constants
├── pipeline.py               # Rookie stats + inference builder
├── espn_client.py            # ESPN scoreboard API
├── summer_league_scraper.py  # Multi-source SL scraper
└── update_sl.py              # Automated daily updater
data/
├── raw/                      # Raw parquet + HTML
└── processed/                # Training + inference frames
```
