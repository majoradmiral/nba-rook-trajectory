"""Check NBA Summer League CDN for live data.

Standalone script — called by the check_sl_data workflow.
Returns exit code 0 if data was saved, 1 if CDN is not live.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.summer_league_scraper import fetch_from_cdn


def main() -> int:
    df = fetch_from_cdn(2026)
    if df.empty:
        print("Not live")
        return 1

    out = ROOT / "data" / "raw" / "sl_players.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_json(out, orient="records")
    print(f"LIVE - saved {len(df)} players")
    return 0


if __name__ == "__main__":
    sys.exit(main())
