"""
Fetches the full division schedule from SportNinja and updates data/schedule.json
with any new Village People games not already tracked.
"""

import json
import os
import requests
from datetime import datetime, timezone

TEAM_ID = "Nz7BgbzbxfrhWtft"
SCHEDULE_ID = "wkh2BQJfxrHuziPq"
API_URL = f"https://canlan2-api.sportninja.net/v1/schedules/{SCHEDULE_ID}/games"
SCHEDULE_FILE = os.path.join(os.path.dirname(__file__), "../data/schedule.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}


def fetch_division_games():
    resp = requests.get(API_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()["data"]


def filter_village_people_games(games):
    return [
        g for g in games
        if g.get("homeTeam", {}).get("id") == TEAM_ID
        or g.get("visitingTeam", {}).get("id") == TEAM_ID
    ]


def load_schedule():
    with open(SCHEDULE_FILE) as f:
        return json.load(f)


def save_schedule(schedule):
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(schedule, f, indent=2)


def main():
    print("Fetching division schedule...")
    all_games = fetch_division_games()
    vp_games = filter_village_people_games(all_games)
    print(f"Found {len(vp_games)} Village People games in division schedule.")

    schedule = load_schedule()
    existing_ids = {g["game_id"] for g in schedule["games"]}

    new_games = []
    for g in vp_games:
        if g["id"] in existing_ids:
            continue
        is_home = g.get("homeTeam", {}).get("id") == TEAM_ID
        opponent = g["visitingTeam"]["name"] if is_home else g["homeTeam"]["name"]
        new_games.append({
            "game_id": g["id"],
            "starts_at": g["starts_at"],
            "opponent": opponent,
            "home_or_away": "home" if is_home else "away",
            "episode_generated": False,
            "special_guest": None,
            "milestones": []
        })

    if new_games:
        schedule["games"].extend(new_games)
        schedule["games"].sort(key=lambda g: g["starts_at"])
        save_schedule(schedule)
        print(f"Added {len(new_games)} new game(s) to schedule.json.")
        for g in new_games:
            print(f"  {g['starts_at'][:10]} vs {g['opponent']} ({g['home_or_away']})")
    else:
        print("No new games found.")


if __name__ == "__main__":
    main()
