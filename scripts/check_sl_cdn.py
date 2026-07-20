"""Check NBA Summer League CDN for live data.

Standalone script — called by the check_sl_data workflow.
Always exits 0 (CDN being down is expected outside summer league).
Only writes sl_players.json when data is actually available.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.summer_league_scraper import fetch_from_cdn


def main() -> None:
    df = fetch_from_cdn(2026)
    if df.empty:
        print("CDN not live — no data to save")
        return

    out = ROOT / "data" / "raw" / "sl_players.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_json(out, orient="records")
    print(f"LIVE - saved {len(df)} players to {out}")


if __name__ == "__main__":
    main()
