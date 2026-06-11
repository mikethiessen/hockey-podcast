"""
Generates a podcast script using the Anthropic API.
Loads game stats, config files, and past episode context,
then writes the script to data/episodes/{game_id}/script.txt.
"""

import json
import os
import sys
from pathlib import Path
import anthropic
from fetch_stats import get_game_stats

# Paths relative to the scripts/ directory
ROOT = Path(__file__).parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"


def load_file(path):
    with open(path) as f:
        return f.read()


def load_past_episodes():
    """Load episode summaries from previously generated games."""
    schedule_path = DATA_DIR / "schedule.json"
    schedule = json.loads(load_file(schedule_path))
    past = []
    for game in schedule["games"]:
        if not game.get("episode_generated"):
            continue
        summary_path = DATA_DIR / "episodes" / game["game_id"] / "summary.json"
        if summary_path.exists():
            summary = json.loads(load_file(summary_path))
            past.append(summary)
    return past


def build_prompt(stats, past_episodes, hosts, guidelines, segments, players):
    past_context = ""
    if past_episodes:
        past_context = "## Past Episode Summaries (for season storylines)\n\n"
        for ep in past_episodes:
            past_context += f"### Game vs {ep.get('opponent')} ({ep.get('date')})\n"
            past_context += f"Result: {ep.get('result_summary')}\n"
            past_context += f"Storylines: {ep.get('storylines')}\n\n"
    else:
        past_context = "## Past Episodes\nThis is the first episode of the season. No prior context.\n"

    return f"""You are writing a podcast script for "Ice & Easy: The Village People Hockey Podcast."

---

## Host Profiles
{hosts}

---

## Podcast Guidelines
{guidelines}

---

## Segment Structure
{segments}

---

## Player Notes
{players}

---

{past_context}

---

## Game Stats (JSON)
```json
{json.dumps(stats, indent=2)}
```

---

## Your Task

Write a complete podcast script for this game following all guidelines above.

Requirements:
- Follow the exact segment order from the segments config (cold_open → game_recap → player_spotlight → gord_corner → season_storylines → closing_take), including any active special segments
- Target 700-800 words total
- Use ONLY the exact format below — no stage directions, no headers, no segment labels:

CASEY: [dialogue]

GORD: [dialogue]

Do not include anything before the first CASEY: line or after the last line of dialogue.
"""


def generate_script(game_id):
    print(f"Generating script for game {game_id}...")

    # Load game stats
    stats = get_game_stats(game_id)
    print(f"  Game: {stats['our_team']} vs {stats['opponent']} — {stats['result'].upper()} {stats['our_score']}-{stats['opp_score']}")

    # Load config files
    hosts = load_file(CONFIG_DIR / "hosts.md")
    guidelines = load_file(CONFIG_DIR / "podcast-guidelines.md")
    segments = load_file(CONFIG_DIR / "segments.md")
    players = load_file(CONFIG_DIR / "players.md")

    # Load past episode context
    past_episodes = load_past_episodes()
    print(f"  Loaded {len(past_episodes)} past episode(s) for context.")

    # Build prompt and call API
    prompt = build_prompt(stats, past_episodes, hosts, guidelines, segments, players)

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    print("  Calling Anthropic API...")
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    script = message.content[0].text.strip()

    # Save script
    episode_dir = DATA_DIR / "episodes" / game_id
    episode_dir.mkdir(parents=True, exist_ok=True)
    script_path = episode_dir / "script.txt"
    script_path.write_text(script)
    print(f"  Script saved to {script_path}")

    # Save a summary JSON for future season context
    summary = {
        "game_id": game_id,
        "date": stats["date"],
        "opponent": stats["opponent"],
        "result_summary": f"{stats['result'].upper()} {stats['our_score']}-{stats['opp_score']}",
        "storylines": extract_storylines(script)
    }
    summary_path = episode_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"  Summary saved to {summary_path}")

    # Mark episode as generated in schedule.json
    schedule_path = DATA_DIR / "schedule.json"
    schedule = json.loads(load_file(schedule_path))
    for game in schedule["games"]:
        if game["game_id"] == game_id:
            game["episode_generated"] = True
            break
    schedule_path.write_text(json.dumps(schedule, indent=2))
    print("  schedule.json updated.")

    return str(script_path)


def extract_storylines(script):
    """Pull the last few lines of the script as a rough storyline summary for future episodes."""
    lines = [l.strip() for l in script.strip().splitlines() if l.strip()]
    closing = lines[-4:] if len(lines) >= 4 else lines
    return " ".join(closing)


if __name__ == "__main__":
    game_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not game_id:
        print("Usage: python generate_script.py <game_id>")
        sys.exit(1)
    generate_script(game_id)
