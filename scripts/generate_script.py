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
    pending_callbacks,
    mark_surfaced,
    add_predictions,
    open_theories,
    can_add_theory,
    apply_theory_tags,
    match_notable_moments,
    format_relationship_context,
    extract_relationship_tags,
)
from guest_coach import (
    ENABLED as GUEST_COACH_ENABLED,
    load_guest_coach_log,
    save_guest_coach_log,
    should_trigger_this_episode,
    format_guest_coach_context,
    extract_guest_coach_tag,
    record_episode_result,
)
from milestones import compute_milestones, format_milestone_context, save_milestone_log
from opponent_stats import get_opponent_brief
from look_ahead import compute_look_ahead, format_look_ahead
from lenses import (
    eligible_lenses,
    pick_lenses,
    recent_lenses_used,
    load_lens_descriptions,
    format_featured_lenses,
)
from config_loader import load_rendered
from episode_memory import load_recent_scripts, format_recent_scripts

# Paths relative to the scripts/ directory
ROOT = Path(__file__).parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"

# When true, the script/audio still get generated for real (so you can actually
# listen to it), but nothing persistent gets touched: schedule.json's
# episode_generated flag, the guest-coach cadence log, the milestone cooldown
# log, and the relationship log (predictions/notable moments) are all left
# exactly as they were. This lets a test run happen without marking the game
# as done or advancing any cadence/cooldown state that a real episode would.
TEST_MODE = os.environ.get("TEST_MODE", "false").lower() == "true"


def load_file(path):
    with open(path) as f:
        return f.read()


def load_past_episodes(season=None):
    """Load episode summaries from previously generated games in the same season only,
    so storylines don't carry over across a season reset.
    If season is None (e.g. current game isn't in schedule.json yet), fail SAFE by
    returning no past episodes rather than skipping the filter — silently including
    every past episode regardless of season is worse than showing none."""
    if season is None:
        print("  Warning: current game's season is unknown — treating as no past episode context.")
        return []
    schedule_path = DATA_DIR / "schedule.json"
    schedule = json.loads(load_file(schedule_path))
    past = []
    for game in schedule["games"]:
        if not game.get("episode_generated"):
            continue
        if game.get("season") != season:
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


def format_next_game_context(next_game, prior_meetings, opponent_stats_context=""):
    if not next_game:
        return "## Next Game Preview\nThis is the last scheduled game of the season, so there is no next game. End the episode without a next-game preview.\n"

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
            "We have NOT played this opponent yet this season, so there is no prior-meeting "
            "data. Do not invent or guess at their roster or best players. The only real "
            "information about their players is the scouting report below (if present); if "
            "it is absent, name no opposing players and keep the preview focused on the "
            "date/time/location and what the season picture says about the matchup instead.\n"
        )

    if opponent_stats_context:
        context += "\n" + opponent_stats_context + "\n"

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


def build_prompt(stats, past_episodes, hosts, core_rules, content_bank, players, script_construction, next_game_context, game_type, season_stats_context, relationship_context, recent_form_context, guest_coach_context, milestone_context, opponent_stats_context="", recent_scripts_context="", look_ahead_context="", featured_lenses=""):
    past_context = ""
    if past_episodes:
        past_context = "## Past Episode Summaries (for season storylines)\n\n"
        for ep in past_episodes:
            past_context += f"### Game vs {ep.get('opponent')} ({ep.get('date')})\n"
            past_context += f"Result: {ep.get('result_summary')}\n"
            past_context += f"Storylines: {ep.get('storylines')}\n\n"
    else:
        past_context = (
            "## Past Episodes\n"
            "This is the FIRST episode of a BRAND NEW season. There is no prior context.\n"
            "This is a hard constraint, not a style note:\n"
            "- Do NOT invent, imply, or reference any past games, opponents, scores, or "
            "months (no \"last season\", \"in the summer\", \"since May\", \"last June\", etc.)\n"
            "- Do NOT name any opponent other than tonight's — inventing one (or reusing a "
            "real name from outside tonight's data) is equally forbidden.\n"
            "- Season storylines and closing takes must be built ONLY from tonight's game. "
            "It is completely normal and expected for a season-opener episode to have no "
            "season-long storyline yet — say so plainly rather than fabricating one.\n"
        )

    recent_form_block = f"\n---\n\n{recent_form_context}\n" if recent_form_context else ""
    relationship_block = f"\n---\n\n{relationship_context}\n" if relationship_context else ""
    guest_coach_block = f"\n---\n\n{guest_coach_context}\n" if guest_coach_context else ""
    milestone_block = f"\n---\n\n{milestone_context}\n" if milestone_context else ""
    opponent_recap_block = f"{opponent_stats_context}\n\n---\n\n" if opponent_stats_context else ""
    recent_scripts_block = f"{recent_scripts_context}\n---\n\n" if recent_scripts_context else ""
    look_ahead_block = f"\n---\n\n{look_ahead_context}\n" if look_ahead_context else ""

    # The per-run task brief lives in config/episode-brief.md so it can be edited
    # without touching Python. It fails loudly if the file or a placeholder is missing.
    brief = load_rendered(
        "episode-brief.md",
        {"game_type": game_type, "featured_lenses": featured_lenses},
    )

    return f"""You are writing a podcast script for "Ice & Easy: The Village People Hockey Podcast."

---

## Host Profiles
{hosts}

---

## Core Rules
{core_rules}

---

## Script Construction
{script_construction}
{guest_coach_block}
---

## Content Bank
{content_bank}

---

{season_stats_context}
{recent_form_block}{relationship_block}{milestone_block}{look_ahead_block}
---

## Player Notes
{players}

---

{next_game_context}

---

{opponent_recap_block}{past_context}

---

{recent_scripts_block}## Game Stats (JSON)
```json
{json.dumps(stats, indent=2)}
```

The `game_timeline` field is the authoritative order events happened in — it already
merges both teams' goals and penalties into one chronological sequence, sorted by
period and time. Use it (not `our_goals`/`their_goals`/`penalties` individually) for
anything about *when* something happened relative to anything else — who scored
first, what a team's goals looked like clustered together or spread out, what
happened right before or after something else, or how the game opened or closed.
Don't reconstruct the order yourself from the separate lists; `game_timeline` is
already correct. Each entry's `time_remaining` is how much time was left in the
period at that moment — treat a low `time_remaining` value as late in the period
(a last-minute or last-seconds event) without needing to calculate anything.

---

{brief}
- Use ONLY the exact format below — no stage directions, no headers, no segment labels:

CASEY: [dialogue]

GORD: [dialogue]

Do not include anything before the first CASEY: line or after the last line of dialogue, EXCEPT for the optional tags described below.

## Optional trailing tags (never spoken, not part of the script)

After the last line of dialogue, you may add any of the following, each on its own line, but only for something a host actually says on air in this script. These are never read aloud; they're stripped before the audio is generated and only used to track the hosts' relationship across the season.

**PREDICTION** — only if a host makes a real, specific, checkable prediction in this episode (not vague hype) and the real data genuinely supports it:
`PREDICTION: <casey|gord> | <type> | <details>`
Valid types:
- `team_result_streak | wins|losses | <window_games e.g. 3>` — e.g. a host predicts the team wins its next 3
- `player_goal_count | <exact player name from this game's data> | <threshold>` — a host predicts a specific player reaches a goal total this season
- `player_points_streak | <exact player name> | <threshold>` — a host predicts a player's point streak reaches N games
- `penalty_trend | <exact player name> | <threshold>` — a host predicts a player's season penalty count reaches N
- `next_game_result | win|loss|tie` — a host calls the result of the next game
- `next_game_goals_for | <N>` — a host says the team scores at least N goals in the next game
- `next_game_goals_against | <N>` — a host says the team holds the next opponent to N goals or fewer
- `next_game_player_point | <exact player name>` — a host says a named player records at least a point in the next game
- `next_game_player_goal | <exact player name>` — a host says a named player scores in the next game

**THEORY** — only if a host floats a new season-long theory in this episode, framed as what he believes:
`THEORY: <casey|gord> | <one-sentence thesis, no invented numbers>`

**THEORY_UPDATE** — only if a host revisits an open theory listed in the Relationship Context section above. Use the theory's id:
`THEORY_UPDATE: <theory id, e.g. T1> | <supports|complicates|dropped> | <one sentence on what tonight showed>`

**MOMENT** — only if something distinct enough happened this episode that a future episode might genuinely want to reference it:
`MOMENT: <casey|gord> | <one-sentence real summary of what they said, no invented detail> | <{game_type}>`

Leave out any tag that nothing in this episode genuinely earns. Never add a tag for something that wasn't said on air.
"""


def generate_script(game_id):
    print(f"Generating script for game {game_id}...")

    # Load game stats
    stats = get_game_stats(game_id)
    print(f"  Game: {stats['our_team']} vs {stats['opponent']} — {stats['result'].upper()} {stats['our_score']}-{stats['opp_score']}")

    # Load config files
    hosts = load_file(CONFIG_DIR / "hosts.md")
    core_rules = load_file(CONFIG_DIR / "core-rules.md")
    content_bank = load_file(CONFIG_DIR / "content-bank.md")
    players = load_file(CONFIG_DIR / "players.md")
    script_construction = load_file(CONFIG_DIR / "script-construction.md")

    game_type = classify_game(stats)
    print(f"  Game type: {game_type}")

    # Load next game preview context
    schedule = load_schedule()
    current_entry = next((g for g in schedule["games"] if g["game_id"] == game_id), None)
    current_season = current_entry.get("season") if current_entry else None

    # Load past episode context (same season only)
    past_episodes = load_past_episodes(season=current_season)
    print(f"  Loaded {len(past_episodes)} past episode(s) for context.")

    # Full text of the last few episodes, so the model can steer away from
    # reusing their jokes, bits, and structure (it has no other memory of them).
    recent_scripts = load_recent_scripts(schedule, game_id, current_season)
    recent_scripts_context = format_recent_scripts(recent_scripts)
    print(f"  Loaded {len(recent_scripts)} recent script(s) for avoid-reuse context.")

    next_game = get_next_game(schedule, game_id)
    prior_meetings = get_prior_meetings(schedule, next_game["opponent"], game_id) if next_game else []
    next_opp_brief = get_opponent_brief(next_game["opponent"], "preview") if next_game else None
    next_opp_stats_context = next_opp_brief["text"] if next_opp_brief else ""
    next_game_context = format_next_game_context(next_game, prior_meetings, next_opp_stats_context)
    if next_game:
        print(f"  Next game: vs {next_game['opponent']} ({len(prior_meetings)} prior meeting(s) this season).")
    else:
        print("  No next game scheduled — ending without a next-game preview.")

    # Compute real season stats (streaks, points leaders, assist pairs, penalty trends)
    season_stats = compute_season_stats(schedule, game_id)
    season_stats_context = format_season_stats(season_stats)
    if season_stats:
        print(f"  Season stats computed from {season_stats['games_counted']} game(s).")

    # Forward-looking context (record, schedule, pace, next opponent) for predictions/speculation
    look_ahead = compute_look_ahead(
        schedule, game_id, season_stats,
        next_opp_brief["record"] if next_opp_brief else None,
    )
    look_ahead_context = format_look_ahead(look_ahead)

    # Recent form (real results only) — drives the slow host-dynamic dial
    recent_form = compute_recent_form(schedule, game_id)
    recent_form_context = format_recent_form(recent_form)
    if recent_form:
        print(f"  Recent form signal: {recent_form['signal']}")

    # Relationship log: resolve any real predictions that can now be checked,
    # and find any real prior moments relevant to tonight's opponent/result type
    relationship_log = load_relationship_log(current_season)
    newly_resolved = resolve_predictions(relationship_log, schedule, get_game_stats, compute_season_stats, game_id)
    # Settled predictions stay queued until an episode containing them is published,
    # so one the model skipped isn't lost.
    callbacks = pending_callbacks(relationship_log)
    theories_open = open_theories(relationship_log)
    moment_matches = match_notable_moments(relationship_log, stats["opponent"], game_type, game_id)
    relationship_context = format_relationship_context(callbacks, moment_matches, theories_open)
    if newly_resolved:
        print(f"  {len(newly_resolved)} prediction(s) newly resolved this episode.")
    if callbacks:
        print(f"  {len(callbacks)} settled prediction(s) to raise on air.")
    if theories_open:
        print(f"  {len(theories_open)} open theory(ies) on the books.")
    if moment_matches:
        print(f"  {len(moment_matches)} prior moment(s) matched to tonight's game.")

    # Lenses: the few angles on the season that tonight's middle is built around. Code
    # picks only ones with real data behind them and rotates away from recent ones.
    lens_ctx = {
        "season_stats": season_stats,
        "look_ahead": look_ahead,
        "has_next_game": next_game is not None,
        "prior_meetings": prior_meetings,
        "pending_callbacks": callbacks,
        "open_theories": theories_open,
        "can_add_theory": can_add_theory(relationship_log),
    }
    lenses_chosen = pick_lenses(eligible_lenses(lens_ctx), recent_lenses_used(past_episodes), game_id)
    featured_lenses = format_featured_lenses(lenses_chosen, load_lens_descriptions())
    print(f"  Featured lenses: {', '.join(lenses_chosen)}")

    # Guest coach: automatic cadence, no manual config edits required.
    # Currently disabled via guest_coach.ENABLED — when off, skip entirely and
    # leave the cadence log untouched so it resumes cleanly once re-enabled.
    guest_coach_triggered = False
    guest_coach_context = ""
    guest_coach_log = None
    if GUEST_COACH_ENABLED:
        guest_coach_log = load_guest_coach_log()
        guest_coach_triggered = should_trigger_this_episode(guest_coach_log)
        guest_coach_context = format_guest_coach_context(guest_coach_log)
        if guest_coach_triggered:
            print("  Guest coach segment triggered for this episode.")

    # Milestone watch: automatic leader-change + goal-streak detection, real data only
    milestones, milestone_log = compute_milestones(schedule, game_id)
    milestone_context = format_milestone_context(milestones)
    if milestones:
        print(f"  Milestone(s) detected: {milestones}")

    # Build prompt and call API
    # Real season leaders for tonight's opponent (totals include tonight's game)
    recap_opp_stats_context = get_opponent_brief(stats["opponent"], "recap")["text"]

    prompt = build_prompt(stats, past_episodes, hosts, core_rules, content_bank, players, script_construction, next_game_context, game_type, season_stats_context, relationship_context, recent_form_context, guest_coach_context, milestone_context, recap_opp_stats_context, recent_scripts_context,
                          look_ahead_context=look_ahead_context, featured_lenses=featured_lenses)

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    print("  Calling Anthropic API...")
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw_script = message.content[0].text.strip()

    # Strip the optional GUEST_COACH: tag (never spoken) and log the invented character
    if GUEST_COACH_ENABLED:
        raw_script, guest_entry = extract_guest_coach_tag(raw_script)
        guest_coach_log = record_episode_result(guest_coach_log, guest_coach_triggered, guest_entry)
        if not TEST_MODE:
            save_guest_coach_log(guest_coach_log)
        else:
            print("  TEST MODE: guest coach cadence log not saved.")
        if guest_coach_triggered and guest_entry:
            print(f"  Guest coach this episode: {guest_entry['name']} ({guest_entry['personality']})")
        elif guest_coach_triggered:
            print("  Warning: guest coach was triggered but no GUEST_COACH: tag was found in the script.")
    else:
        guest_entry = None

    if not TEST_MODE:
        save_milestone_log(milestone_log)
    else:
        print("  TEST MODE: milestone cooldown log not saved.")

    # Strip any optional PREDICTION:/MOMENT:/THEORY:/THEORY_UPDATE: tags (never spoken) and log them
    script, new_predictions, new_moments, new_theories, theory_updates = extract_relationship_tags(
        raw_script, game_id, context={"date": stats["date"], "opponent": stats["opponent"]}
    )
    if new_predictions:
        add_predictions(relationship_log, new_predictions)
        print(f"  Logged {len(new_predictions)} new checkable prediction(s).")
    if new_moments:
        relationship_log["notable_moments"].extend(new_moments)
        print(f"  Logged {len(new_moments)} new notable moment(s).")
    if new_theories or theory_updates:
        added, updated = apply_theory_tags(relationship_log, new_theories, theory_updates, game_id)
        print(f"  Theories: {added} new, {updated} updated.")
    # The settled predictions we put in front of the model have now been offered in a
    # published episode, so they leave the queue (test runs never save the log).
    mark_surfaced(relationship_log, [p["id"] for p in callbacks])
    if not TEST_MODE:
        save_relationship_log(relationship_log)
    else:
        print("  TEST MODE: relationship log not saved.")

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
        "storylines": extract_storylines(script),
        "game_type": game_type,
        "lenses": lenses_chosen,
    }
    summary_path = episode_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"  Summary saved to {summary_path}")

    # Mark episode as generated in schedule.json
    if not TEST_MODE:
        schedule_path = DATA_DIR / "schedule.json"
        schedule = json.loads(load_file(schedule_path))
        marked = False
        for game in schedule["games"]:
            if game["game_id"] == game_id:
                game["episode_generated"] = True
                if guest_coach_triggered and guest_entry:
                    game["special_guest"] = f"{guest_entry['name']} — {guest_entry['personality']}"
                if milestones:
                    game["milestones"] = milestones
                marked = True
                break

        if not marked:
            # The game_id isn't in schedule.json at all. This used to fail silently:
            # the loop found nothing, the file was rewritten unchanged, and the commit
            # step saw no diff — so episode_generated never landed and the NEXT run
            # regenerated a duplicate episode. It happens on the auto-detect path,
            # where check_schedule.py finds a game from the API that the local
            # schedule.json may not contain yet. Add the entry rather than lose the
            # flag, and say so loudly.
            print(f"  WARNING: game {game_id} was not in schedule.json — adding it now "
                  "so episode_generated is recorded and no duplicate is generated.")
            entry = {
                "game_id": game_id,
                "starts_at": stats.get("date") or "",
                "opponent": stats.get("opponent") or "",
                "home_or_away": stats.get("home_or_away") or "",
                "episode_generated": True,
                "special_guest": None,
                "season": schedule.get("season"),
            }
            if guest_coach_triggered and guest_entry:
                entry["special_guest"] = f"{guest_entry['name']} — {guest_entry['personality']}"
            if milestones:
                entry["milestones"] = milestones
            schedule["games"].append(entry)

        schedule_path.write_text(json.dumps(schedule, indent=2))
        print("  schedule.json updated.")
    else:
        print("  TEST MODE: schedule.json not updated — this game remains eligible for a real run.")

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
