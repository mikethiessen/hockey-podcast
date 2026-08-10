"""
Fetches and aggregates full-season stats for the Village People from any
SportNinja schedule (past season or current), by schedule_id.

Pulls every completed Village People game on the given schedule, fetches
full game data via fetch_stats.get_game_stats(), and rolls it up into:
  - per-player totals: games played, goals, assists, points, penalty minutes
  - team totals: record (W-L-T), goals for/against

Raw per-game data is cached to data/season_stats/<season_label>.json so
re-running doesn't re-hit the API for games already fetched. The aggregated
result is written to data/season_stats/<season_label>-summary.json.

Usage:
    python scripts/season_stats.py <schedule_id> <season_label>

Example:
    python scripts/season_stats.py wkh2BQJfxrHuziPq 2025-winter

Finding a past season's schedule_id: it's the same kind of ID used for
SCHEDULE_ID in sync_schedule.py / check_schedule.py, just for a different
season. It shows up in the URL when browsing that season's schedule/
standings page on the league site, or in the SportNinja API response for
the team/division if you fetch that endpoint directly.
"""

import json
import os
import sys
import time
import requests

from fetch_stats import get_game_stats, TEAM_ID, HEADERS

SCRIPT_DIR = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "../data/season_stats")

# Rough penalty minutes by severity name. SportNinja's exact severity labels
# weren't verified against a live prior-season response (network access to
# canlan2-api.sportninja.net isn't available in the dev sandbox this script
# was written in) — check these against a real `severity` value in a cached
# game file and adjust if needed.
SEVERITY_MINUTES = {
    "minor": 2,
    "double minor": 4,
    "major": 5,
    "misconduct": 10,
    "match": 5,
}


def fetch_schedule_games(schedule_id):
    url = f"https://canlan2-api.sportninja.net/v1/schedules/{schedule_id}/games"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()["data"]


def filter_our_games(games):
    return [
        g for g in games
        if g.get("homeTeam", {}).get("id") == TEAM_ID
        or g.get("visitingTeam", {}).get("id") == TEAM_ID
    ]


def only_final_games(games):
    # game_status_id 9 = final (same convention as check_schedule.py)
    return [g for g in games if g.get("game_status_id") == 9]


def load_cache(season_label):
    path = os.path.join(OUTPUT_DIR, f"{season_label}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"season": season_label, "schedule_id": None, "games": {}}


def save_cache(season_label, cache):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"{season_label}.json")
    with open(path, "w") as f:
        json.dump(cache, f, indent=2)
    return path


def aggregate(games_stats):
    players = {}
    team_totals = {
        "games_played": 0,
        "wins": 0,
        "losses": 0,
        "ties": 0,
        "goals_for": 0,
        "goals_against": 0,
    }

    def ensure_player(name):
        if name not in players:
            players[name] = {
                "games_played": 0,
                "goals": 0,
                "assists": 0,
                "points": 0,
                "penalty_minutes": 0,
                "penalty_count": 0,
            }
        return players[name]

    for g in games_stats:
        team_totals["games_played"] += 1
        team_totals["goals_for"] += g["our_score"]
        team_totals["goals_against"] += g["opp_score"]
        if g["result"] == "win":
            team_totals["wins"] += 1
        elif g["result"] == "loss":
            team_totals["losses"] += 1
        else:
            team_totals["ties"] += 1

        for name in set(g.get("players_present", [])):
            ensure_player(name)["games_played"] += 1

        for goal in g.get("our_goals", []):
            scorer = goal.get("scorer")
            if scorer and scorer != "Unknown":
                p = ensure_player(scorer)
                p["goals"] += 1
                p["points"] += 1
            for assist in goal.get("assists", []):
                name = assist.get("name", "").strip()
                if name and name != "Unknown Unknown":
                    p = ensure_player(name)
                    p["assists"] += 1
                    p["points"] += 1

        for pen in g.get("penalties", []):
            if pen.get("team") != "us":
                continue
            name = pen.get("player")
            if not name or name == "Unknown":
                continue
            p = ensure_player(name)
            p["penalty_count"] += 1
            severity = (pen.get("severity") or "").strip().lower()
            p["penalty_minutes"] += SEVERITY_MINUTES.get(severity, 2)

    leaderboard = sorted(
        [{"name": n, **stats} for n, stats in players.items()],
        key=lambda x: (-x["points"], -x["goals"]),
    )

    return team_totals, leaderboard


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/season_stats.py <schedule_id> <season_label>")
        print("Example: python scripts/season_stats.py wkh2BQJfxrHuziPq 2025-winter")
        sys.exit(1)

    schedule_id = sys.argv[1]
    season_label = sys.argv[2]

    cache = load_cache(season_label)
    cache["schedule_id"] = schedule_id

    print(f"Fetching schedule {schedule_id} for season '{season_label}'...")
    all_games = fetch_schedule_games(schedule_id)
    our_games = filter_our_games(all_games)
    final_games = only_final_games(our_games)
    print(f"Found {len(final_games)} completed Village People game(s) on this schedule.")

    games_stats = []
    for g in final_games:
        game_id = g["id"]
        if game_id in cache["games"]:
            games_stats.append(cache["games"][game_id])
            continue
        print(f"  Fetching game {game_id}...")
        try:
            stats = get_game_stats(game_id)
        except Exception as e:
            print(f"    Failed to fetch {game_id}: {e}")
            continue
        cache["games"][game_id] = stats
        games_stats.append(stats)
        time.sleep(0.3)  # be polite to the API

    save_cache(season_label, cache)

    team_totals, leaderboard = aggregate(games_stats)

    summary = {
        "season": season_label,
        "schedule_id": schedule_id,
        "team_totals": team_totals,
        "leaderboard": leaderboard,
    }

    summary_path = os.path.join(OUTPUT_DIR, f"{season_label}-summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nSaved raw game cache to data/season_stats/{season_label}.json")
    print(f"Saved aggregated summary to data/season_stats/{season_label}-summary.json")
    print(
        f"\nRecord: {team_totals['wins']}-{team_totals['losses']}-{team_totals['ties']}  "
        f"GF {team_totals['goals_for']} / GA {team_totals['goals_against']}"
    )
    print("\nTop scorers:")
    for p in leaderboard[:10]:
        print(
            f"  {p['name']:<20} GP {p['games_played']:<3} "
            f"G {p['goals']:<3} A {p['assists']:<3} P {p['points']:<3}"
        )


if __name__ == "__main__":
    main()
