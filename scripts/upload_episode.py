"""
Uploads a generated episode to Buzzsprout.
Reads the script for a description, then POSTs the mp3
to the Buzzsprout API.
"""

import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime
from fetch_stats import get_game_stats

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"


def load_schedule():
    with open(DATA_DIR / "schedule.json") as f:
        return json.load(f)


def get_episode_description(script_path):
    """Pull the first CASEY line as a short description fallback."""
    try:
        with open(script_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("CASEY:"):
                    text = line[len("CASEY:"):].strip()
                    # Truncate to ~200 chars for description
                    return text[:200] + ("..." if len(text) > 200 else "")
    except Exception:
        pass
    return "A new episode of Ice & Easy: The Village People Hockey Podcast."


def format_episode_title(opponent, date_str):
    """Format: 'vs. Dusters — June 10'"""
    try:
        dt = datetime.fromisoformat(date_str)
        formatted_date = dt.strftime("%B %-d")
    except Exception:
        formatted_date = date_str[:10]
    return f"vs. {opponent} — {formatted_date}"


def upload_episode(game_id):
    print(f"Uploading episode for game {game_id} to Buzzsprout...")

    api_token = os.environ["BUZZSPROUT_API_TOKEN"]
    podcast_id = os.environ["BUZZSPROUT_PODCAST_ID"]

    episode_dir = DATA_DIR / "episodes" / game_id
    mp3_path = episode_dir / "episode.mp3"
    script_path = episode_dir / "script.txt"

    if not mp3_path.exists():
        print(f"ERROR: Audio file not found at {mp3_path}")
        sys.exit(1)

    # Find game details from schedule — fall back to a live API fetch if this
    # game hasn't been synced into schedule.json yet (e.g. manual game_id runs
    # skip the sync step, or a newly-added game hasn't been picked up yet)
    schedule = load_schedule()
    game = next((g for g in schedule["games"] if g["game_id"] == game_id), None)
    if game:
        opponent = game["opponent"]
        starts_at = game["starts_at"]
    else:
        print(f"  Note: game_id {game_id} not in schedule.json — fetching details live instead.")
        stats = get_game_stats(game_id)
        opponent = stats["opponent"]
        starts_at = stats["date"]
        home_or_away = stats["home_or_away"]

    title = format_episode_title(opponent, starts_at)
    description = get_episode_description(script_path)

    print(f"  Title: {title}")
    print(f"  Description: {description[:80]}...")
    print(f"  Audio: {mp3_path}")

    url = f"https://www.buzzsprout.com/api/{podcast_id}/episodes.json"
    headers = {
        "Authorization": f"Token token={api_token}",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    with open(mp3_path, "rb") as audio_file:
        files = {
            "audio_file": (f"{game_id}.mp3", audio_file, "audio/mpeg")
        }
        data = {
            "title": title,
            "description": description,
            "private": "false"
        }
        resp = requests.post(url, headers=headers, files=files, data=data, timeout=120)

    if not resp.ok:
        print(f"  Buzzsprout error {resp.status_code}: {resp.text}")
        resp.raise_for_status()
    episode_data = resp.json()
    episode_url = episode_data.get("url") or episode_data.get("share_url") or "(check Buzzsprout dashboard)"
    print(f"  Upload successful!")
    print(f"  Episode URL: {episode_url}")

    # Save upload result
    result_path = episode_dir / "upload_result.json"
    result_path.write_text(json.dumps(episode_data, indent=2))
    print(f"  Result saved to {result_path}")

    # If this game wasn't in schedule.json (e.g. manual game_id run skipped sync),
    # add it now so future episodes get correct past-episode/season context.
    if not game:
        schedule["games"].append({
            "game_id": game_id,
            "starts_at": starts_at,
            "opponent": opponent,
            "home_or_away": home_or_away,
            "episode_generated": True,
            "special_guest": None,
            "milestones": [],
            "season": schedule.get("season")
        })
        schedule["games"].sort(key=lambda g: g["starts_at"])
        (DATA_DIR / "schedule.json").write_text(json.dumps(schedule, indent=2))
        print(f"  Added {game_id} to schedule.json (was missing) and marked episode_generated.")

    return episode_url


if __name__ == "__main__":
    game_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not game_id:
        print("Usage: python upload_episode.py <game_id>")
        sys.exit(1)
    upload_episode(game_id)
