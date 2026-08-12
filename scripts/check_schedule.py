"""
Checks if a Village People game ended within the last 20 minutes
and hasn't had an episode generated yet.

Returns the game_id if found, exits with code 1 if not.
Used by the GitHub Actions workflow to decide whether to run the pipeline.
"""

import json
import os
import sys
import requests
from datetime import datetime, timezone, timedelta

TEAM_ID = "Nz7BgbzbxfrhWtft"
SCHEDULE_ID = "NC9xfp7yJc3Vm4Ul"  # NOTE: this ID changes when Canlan starts a new
# schedule/season instance (confirmed Aug 2026 — regular season used wkh2BQJfxrHuziPq,
# this new one covers playoffs). No auto-discovery endpoint found yet; update manually
# by grabbing the sn_schedule value from https://canlanstats.sportninja.com/team/{TEAM_ID}
API_URL = f"https://canlan2-api.sportninja.net/v1/schedules/{SCHEDULE_ID}/games"
SCHEDULE_FILE = os.path.join(os.path.dirname(__file__), "../data/schedule.json")
WINDOW_MINUTES = 10  # now that an external poller (cron-job.org) triggers this every
                      # 1-2 min via workflow_dispatch, a short window keeps detection tight
                      # while still covering brief network/API hiccups

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}


def load_schedule():
    with open(SCHEDULE_FILE) as f:
        return json.load(f)


def fetch_division_games():
    params = {
        "page": 1,
        "order": "asc",
        "exclude_cancelled_games": 1,
        "team_id": TEAM_ID,
    }
    resp = requests.get(API_URL, headers=HEADERS, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()["data"]


def main():
    schedule = load_schedule()
    processed_ids = {g["game_id"] for g in schedule["games"] if g.get("episode_generated")}

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=WINDOW_MINUTES)

    print(f"Checking for completed Village People games between {cutoff.isoformat()} and {now.isoformat()}")

    games = fetch_division_games()

    for g in games:
        home_id = g.get("homeTeam", {}).get("id")
        away_id = g.get("visitingTeam", {}).get("id")
        if TEAM_ID not in (home_id, away_id):
            continue

        game_id = g["id"]
        if game_id in processed_ids:
            continue

        # game_status_id 9 = final
        if g.get("game_status_id") != 9:
            continue

        ended_at_str = g.get("ended_at")
        if not ended_at_str:
            continue

        ended_at = datetime.fromisoformat(ended_at_str.replace("Z", "+00:00"))
        if cutoff <= ended_at <= now:
            print(f"Found eligible game: {game_id} (ended {ended_at.isoformat()})")
            print(f"GAME_ID={game_id}")
            # Write to GitHub Actions output if available
            github_output = os.environ.get("GITHUB_OUTPUT")
            if github_output:
                with open(github_output, "a") as f:
                    f.write(f"game_id={game_id}\n")
                    f.write(f"found=true\n")
            sys.exit(0)

    print("No eligible game found in window.")
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write("found=false\n")
    sys.exit(1)


if __name__ == "__main__":
    main()
