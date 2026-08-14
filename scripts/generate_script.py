"""
Generates a podcast script using the Anthropic API.
Loads game stats, config files, and past episode context,
then writes the script to data/episodes/{game_id}/script.txt.
"""

import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import anthropic
from fetch_stats import get_game_stats
from season_stats import compute_season_stats, format_season_stats, compute_recent_form, format_recent_form
from relationship_log import (
    load_relationship_log,
    save_relationship_log,
    resolve_predictions,
    match_notable_moments,
    format_relationship_context,
    extract_relationship_tags,
)

# Paths relative to the scripts/ directory
ROOT = Path(__file__).parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"


def load_file(path):
    with open(path) as f:
        return f.read()


def load_past_episodes(season=None):
    """Load episode summaries from previously generated games in the same season only,
    so storylines don't carry over across a season reset."""
    schedule_path = DATA_DIR / "schedule.json"
    schedule = json.loads(load_file(schedule_path))
    past = []
    for game in schedule["games"]:
        if not game.get("episode_generated"):
            continue
        if season is not None and game.get("season") != season:
            continue
        summary_path = DATA_DIR / "episodes" / game["game_id"] / "summary.json"
        if summary_path.exists():
            summary = json.loads(load_file(summary_path))
            past.append(summary)
    return past


def load_schedule():
    schedule_path = DATA_DIR / "schedule.json"
    return json.loads(load_file(schedule_path))


def get_next_game(schedule, current_game_id):
    """Find the next game on the schedule after the current one, by date order.
    Scoped to games in the same season as the current game, so a season's final
    game doesn't preview next season's opener as if it's a continuation."""
    all_games = sorted(schedule["games"], key=lambda g: g["starts_at"])
    current = next((g for g in all_games if g["game_id"] == current_game_id), None)
    current_season = current.get("season") if current else None

    games = [g for g in all_games if g.get("season") == current_season]
    for i, g in enumerate(games):
        if g["game_id"] == current_game_id:
            if i + 1 < len(games):
                return games[i + 1]
            return None
    return None


def get_prior_meetings(schedule, opponent, before_game_id):
    """Find past, already-generated games against the same opponent, earlier in the
    SAME season — scoped so a rematch next season isn't reported as "already played
    this season" based on a previous season's meeting."""
    all_games = sorted(schedule["games"], key=lambda g: g["starts_at"])
    before_index = next((i for i, g in enumerate(all_games) if g["game_id"] == before_game_id), None)
    if before_index is None:
        return []

    current_season = all_games[before_index].get("season")

    prior = []
    for g in all_games[:before_index]:
        if g.get("season") != current_season:
            continue
        if g["opponent"] == opponent and g.get("episode_generated"):
            try:
                stats = get_game_stats(g["game_id"])
                prior.append(stats)
            except Exception as e:
                print(f"  Warning: couldn't load prior meeting stats for {g['game_id']}: {e}")
    return prior


def format_next_game_context(next_game, prior_meetings):
    if not next_game:
        return "## Next Game Preview\nThis is the last scheduled game of the season. Skip the next_game_preview segment entirely — do not include it in the script.\n"

    dt_utc = datetime.fromisoformat(next_game["starts_at"])
    dt = dt_utc.astimezone(ZoneInfo("America/Winnipeg"))
    date_str = dt.strftime("%A, %B %-d")
    time_str = dt.strftime("%-I:%M %p %Z")
    location = "at home" if next_game["home_or_away"] == "home" else "on the road"

    context = "## Next Game Preview\n"
    context += f"Next game: vs {next_game['opponent']}, {date_str} at {time_str}, {location}.\n\n"

    if prior_meetings:
        context += "We HAVE played this opponent before this season. Real data from the most recent meeting:\n"
        latest = prior_meetings[-1]
        context += f"- Result: {latest['result'].upper()} {latest['our_score']}-{latest['opp_score']}\n"
        if latest.get("their_goals"):
            scorers = [g["scorer"] for g in latest["their_goals"] if g.get("scorer")]
            if scorers:
                context += f"- Their goal scorers that game: {', '.join(scorers)}\n"
        context += (
            "Use this real data to recap the last meeting and/or note which of their "
            "players to watch for, based ONLY on the scorers listed above. "
            f"({len(prior_meetings)} prior meeting(s) this season.)\n"
        )
    else:
        context += (
            "We have NOT played this opponent yet this season — there is no prior meeting "
            "data and no data on their individual players. Do not invent or guess at their "
            "roster or best players. Keep the preview focused on the date/time/location and "
            "general anticipation instead.\n"
        )

    return context


def classify_game(stats):
    """Deterministically classify the game so the model gets a consistent structural cue."""
    diff = abs(stats["our_score"] - stats["opp_score"])
    result = stats["result"]

    if stats["opp_score"] == 0 and result == "win":
        return "SHUTOUT_WIN"
    if stats["our_score"] == 0 and result == "loss":
        return "SHUTOUT_LOSS"
    if stats.get("went_to_overtime") or diff <= 1:
        return "CLOSE_OR_OVERTIME"
    if diff >= 4:
        return "BLOWOUT_WIN" if result == "win" else "BLOWOUT_LOSS"
    return "NORMAL"


def build_prompt(stats, past_episodes, hosts, guidelines, segments, players, variety, next_game_context, game_type, bits, season_stats_context, relationship_context, recent_form_context):
    past_context = ""
    if past_episodes:
        past_context = "## Past Episode Summaries (for season storylines)\n\n"
        for ep in past_episodes:
            past_context += f"### Game vs {ep.get('opponent')} ({ep.get('date')})\n"
            past_context += f"Result: {ep.get('result_summary')}\n"
            past_context += f"Storylines: {ep.get('storylines')}\n\n"
    else:
        past_context = "## Past Episodes\nThis is the first episode of the season. No prior context.\n"

    recent_form_block = f"\n---\n\n{recent_form_context}\n" if recent_form_context else ""
    relationship_block = f"\n---\n\n{relationship_context}\n" if relationship_context else ""

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

Game Type for this episode: **{game_type}**
Apply the corresponding rules from the "Segment Structure by Game Type" section above.

---

## Recurring Bits
{bits}

---

{season_stats_context}
{recent_form_block}{relationship_block}
---

## Player Notes
{players}

---

## Script Variety Guidelines
{variety}

---

{next_game_context}

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
- Follow the exact segment order from the segments config (cold_open → game_recap → player_spotlight → gord_corner → season_storylines → closing_take → next_game_preview), including any active special segments
- Apply the Segment Structure by Game Type rule for **{game_type}** — flex segment length/emphasis as instructed, don't change the segment order itself
- Casey always opens the Cold Open — this does not change episode to episode
- The very first CASEY line of the whole script must be a short welcome to the show by name (e.g. "Welcome to Ice & Easy!") — vary the exact wording episode to episode, but it needs to work as a standalone opener since it plays under the tail of the intro music. Follow it immediately with Casey's reaction to the score.
- In game_recap, don't recite exact clock times or walk through every period mechanically by default. Only call out a specific time or period when it's genuinely part of the story — a late-game winner, a goal in the final minute, multiple goals in a short span, a third-period collapse. Otherwise keep the recap focused on what happened and who was involved, not when down to the minute.
- For season_storylines, lead with the real computed Season Stats above where they're genuinely interesting — a streak, a points leader, a frequent scoring connection, a penalty trend. Be creative in HOW you present a real stat (a nickname, a bit, a comparison) but never state a number or trend that isn't in the Season Stats data. If nothing there is interesting for tonight, fall back to carrying forward last episode's storyline instead of forcing a stat in.
- Apply the Script Variety Guidelines above: rotate phrasing for goals/assists/penalties, choose what the recap leads on based on what's distinctive in this game's data, vary reaction order within non-Cold-Open segments, call out multi-point games and assist chains where the data supports it, group penalties by period when there's a clear cluster, and use a quick-hits treatment for busy/low-impact events
- Work in 1, occasionally 2, Recurring Bits from the bank above if they genuinely fit this game's data — skip any that don't, and never repeat the same bit as the immediately preceding episode
- For next_game_preview: use the Next Game Preview section above. Always include the date, time, and opponent if a next game exists. Only mention specific opposing players if real prior-meeting data is provided — never invent or guess at an opponent's roster or standout players. If there's no next game, omit this segment entirely.
- Do not invent any detail not present in the game stats JSON or the Next Game Preview data
- If a Relationship Context section is present above, only use it if it genuinely fits — never force a callback or prediction check-in that doesn't naturally arise from tonight's episode
- Target 700-800 words total
- Use ONLY the exact format below — no stage directions, no headers, no segment labels:

CASEY: [dialogue]

GORD: [dialogue]

Do not include anything before the first CASEY: line or after the last line of dialogue, EXCEPT for the optional tags described below.

## Optional trailing tags (never spoken, not part of the script)

After the last line of dialogue, you may — only if genuinely earned by this episode, never required — add one or both of the following on their own lines. These are never read aloud; they're stripped before the audio is generated and only used to track the hosts' relationship across the season.

**PREDICTION** — only if a host makes a real, specific, checkable prediction in this episode (not vague hype):
`PREDICTION: <casey|gord> | <type> | <details>`
Valid types:
- `team_result_streak | wins|losses | <window_games e.g. 3>` — e.g. a host predicts the team wins its next 3
- `player_goal_count | <exact player name from this game's data> | <threshold>` — a host predicts a specific player reaches a goal total this season
- `player_points_streak | <exact player name> | <threshold>` — a host predicts a player's point streak reaches N games
- `penalty_trend | <exact player name> | <threshold>` — a host predicts a player's season penalty count reaches N

**MOMENT** — only if something distinct enough happened this episode that a future episode might genuinely want to reference it:
`MOMENT: <casey|gord> | <one-sentence real summary of what they said, no invented detail> | <{game_type}>`

Omit both entirely if nothing this episode genuinely earns them — this should be rare, not automatic.
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
    variety = load_file(CONFIG_DIR / "variety-guidelines.md")
    bits = load_file(CONFIG_DIR / "recurring-bits.md")

    game_type = classify_game(stats)
    print(f"  Game type: {game_type}")

    # Load next game preview context
    schedule = load_schedule()
    current_entry = next((g for g in schedule["games"] if g["game_id"] == game_id), None)
    current_season = current_entry.get("season") if current_entry else None

    # Load past episode context (same season only)
    past_episodes = load_past_episodes(season=current_season)
    print(f"  Loaded {len(past_episodes)} past episode(s) for context.")

    next_game = get_next_game(schedule, game_id)
    prior_meetings = get_prior_meetings(schedule, next_game["opponent"], game_id) if next_game else []
    next_game_context = format_next_game_context(next_game, prior_meetings)
    if next_game:
        print(f"  Next game: vs {next_game['opponent']} ({len(prior_meetings)} prior meeting(s) this season).")
    else:
        print("  No next game scheduled — skipping next_game_preview.")

    # Compute real season stats (streaks, points leaders, assist pairs, penalty trends)
    season_stats = compute_season_stats(schedule, game_id)
    season_stats_context = format_season_stats(season_stats)
    if season_stats:
        print(f"  Season stats computed from {season_stats['games_counted']} game(s).")

    # Recent form (real results only) — drives the slow host-dynamic dial
    recent_form = compute_recent_form(schedule, game_id)
    recent_form_context = format_recent_form(recent_form)
    if recent_form:
        print(f"  Recent form signal: {recent_form['signal']}")

    # Relationship log: resolve any real predictions that can now be checked,
    # and find any real prior moments relevant to tonight's opponent/result type
    relationship_log = load_relationship_log(current_season)
    newly_resolved = resolve_predictions(relationship_log, schedule, get_game_stats, compute_season_stats, game_id)
    moment_matches = match_notable_moments(relationship_log, stats["opponent"], game_type, game_id)
    relationship_context = format_relationship_context(newly_resolved, moment_matches)
    if newly_resolved:
        print(f"  {len(newly_resolved)} prediction(s) newly resolved this episode.")
    if moment_matches:
        print(f"  {len(moment_matches)} prior moment(s) matched to tonight's game.")

    # Build prompt and call API
    prompt = build_prompt(stats, past_episodes, hosts, guidelines, segments, players, variety, next_game_context, game_type, bits, season_stats_context, relationship_context, recent_form_context)

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    print("  Calling Anthropic API...")
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw_script = message.content[0].text.strip()

    # Strip any optional PREDICTION:/MOMENT: tags (never spoken) and log them
    script, new_predictions, new_moments = extract_relationship_tags(raw_script, game_id)
    if new_predictions:
        relationship_log["predictions"].extend(new_predictions)
        print(f"  Logged {len(new_predictions)} new checkable prediction(s).")
    if new_moments:
        relationship_log["notable_moments"].extend(new_moments)
        print(f"  Logged {len(new_moments)} new notable moment(s).")
    save_relationship_log(relationship_log)

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
