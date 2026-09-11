"""
Maintains data/guest_coach_log.json — tracks the automatic cadence for the
guest_coach special segment and a short history of previously invented guest
characters (so the model can avoid inventing something too similar back to
back).

Nothing here is manually edited. generate_script.py calls
should_trigger_this_episode() before building the prompt, and
record_episode_result() after the script is generated, to advance the
cadence and log whatever character the model actually invented.
"""

import json
import random
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
LOG_PATH = DATA_DIR / "guest_coach_log.json"

MIN_GAP = 3
MAX_GAP = 6
HISTORY_CONTEXT_SIZE = 5  # how many recent guests to show the model, to avoid repeats


def _new_log():
    return {
        "episodes_since_last": 0,
        "gap_target": random.randint(MIN_GAP, MAX_GAP),
        "history": [],
    }


def load_guest_coach_log():
    if LOG_PATH.exists():
        return json.loads(LOG_PATH.read_text())
    return _new_log()


def save_guest_coach_log(log):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(log, indent=2))


def should_trigger_this_episode(log):
    """Deterministic check against real counters — never guessed by the model."""
    return log["episodes_since_last"] >= log["gap_target"]


def format_guest_coach_context(log):
    """Builds the optional prompt section instructing the model to invent a
    fresh guest coach character for this episode. Returns "" if this episode
    isn't a guest-coach episode."""
    if not should_trigger_this_episode(log):
        return ""

    recent = log["history"][-HISTORY_CONTEXT_SIZE:]

    lines = ["## Special Segment: Guest Coach (this episode only)"]
    lines.append(
        "This episode gets a one-off guest coach segment, replacing gord_corner "
        "for this episode only. Invent a brand new character for tonight:\n"
        "- Give them a name and a distinct personality/voice, clearly different "
        "from both Casey and Gord (a different energy, vocabulary, and way of "
        "reacting — not a third variation on either existing host).\n"
        "- They follow the exact same fact rules as Casey and Gord: they can "
        "react to, analyze, and have opinions about tonight's real game events, "
        "but must NEVER invent scores, goals, assists, penalties, or plays that "
        "aren't in the game stats JSON.\n"
        "- Give them a short introduction (who they are, why they're on the "
        "show tonight) before they weigh in on the game."
    )

    if recent:
        lines.append("\nGuest coaches from recent episodes (invent someone clearly "
                      "different from these — don't repeat a name or a very similar "
                      "personality):")
        for g in recent:
            lines.append(f"- {g['name']}: {g['personality']}")

    lines.append(
        "\nAt the end of the script, after any PREDICTION/MOMENT tags, add exactly "
        "one line (never spoken, stripped before audio):\n"
        "GUEST_COACH: <name> | <one-line personality/voice descriptor>"
    )

    return "\n".join(lines)


def extract_guest_coach_tag(script):
    """Strips the optional trailing GUEST_COACH: tag line and returns
    (clean_script, guest_entry_or_None)."""
    lines = script.strip().splitlines()
    clean_lines = []
    guest_entry = None

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("GUEST_COACH:"):
            parts = [p.strip() for p in stripped[len("GUEST_COACH:"):].split("|")]
            if len(parts) >= 2:
                guest_entry = {"name": parts[0], "personality": parts[1]}
            continue
        clean_lines.append(line)

    clean_script = "\n".join(clean_lines).strip()
    return clean_script, guest_entry


def record_episode_result(log, triggered, guest_entry):
    """Advances the cadence counters after an episode generates. Call this
    exactly once per episode, regardless of whether it was a guest-coach
    episode."""
    if triggered:
        log["episodes_since_last"] = 0
        log["gap_target"] = random.randint(MIN_GAP, MAX_GAP)
        if guest_entry:
            log["history"].append(guest_entry)
    else:
        log["episodes_since_last"] += 1
    return log
