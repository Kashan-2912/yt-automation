#!/usr/bin/env python3
"""
Auto-update FIFA World Cup 2026 data from the openfootball open-data project.

openfootball keeps worldcup.json updated with live scores in the same format
as the local 2026/ folder, so we just overwrite our local copy.

Usage:
    python scripts/update_wc_data.py

GitHub Actions step (add before video generation):
    - name: Update WC 2026 data
      run: python scripts/update_wc_data.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

DATA_DIR = REPO_ROOT / "2026"

# openfootball world-cup.json 2026 — same format as our local files
SOURCES = {
    "worldcup.json": (
        "https://raw.githubusercontent.com/openfootball/world-cup.json/master/2026/worldcup.json"
    ),
    "worldcup.groups.json": (
        "https://raw.githubusercontent.com/openfootball/world-cup.json/master/2026/worldcup.groups.json"
    ),
    "worldcup.teams.json": (
        "https://raw.githubusercontent.com/openfootball/world-cup.json/master/2026/worldcup.teams.json"
    ),
    "worldcup.squads.json": (
        "https://raw.githubusercontent.com/openfootball/world-cup.json/master/2026/worldcup.squads.json"
    ),
}


def fetch_and_save(filename: str, url: str) -> bool:
    """Fetch URL and save to 2026/{filename}. Returns True on success."""
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=15) as resp:
            raw = resp.read()
        # Validate it's real JSON
        data = json.loads(raw)
        out_path = DATA_DIR / filename
        out_path.write_bytes(raw)
        print(f"  [OK] {filename} — {len(data.get('matches', data.get('groups', data.get('teams', [])))) } entries")
        return True
    except Exception as e:
        print(f"  [SKIP] {filename} — {e}")
        return False


def count_completed(matches: list[dict]) -> int:
    return sum(1 for m in matches if m.get("score", {}).get("ft"))


def main() -> None:
    print("=== FIFA World Cup 2026 Data Update ===")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Show current state before update
    local_path = DATA_DIR / "worldcup.json"
    if local_path.exists():
        with open(local_path, encoding="utf-8") as f:
            local_data = json.load(f)
        local_matches = local_data.get("matches", [])
        print(f"Before: {count_completed(local_matches)}/{len(local_matches)} matches completed locally")

    # Fetch updates
    updated = 0
    for filename, url in SOURCES.items():
        if fetch_and_save(filename, url):
            updated += 1

    # Show state after update
    if local_path.exists():
        with open(local_path, encoding="utf-8") as f:
            new_data = json.load(f)
        new_matches = new_data.get("matches", [])
        print(f"After:  {count_completed(new_matches)}/{len(new_matches)} matches completed")

    print(f"\nUpdated {updated}/{len(SOURCES)} files. Data saved to {DATA_DIR}/")


if __name__ == "__main__":
    main()
