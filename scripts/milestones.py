"""
Detects real, data-driven milestones for the milestone_watch special segment.
Nothing here is invented or manually noted — everything is computed from
real game stats already fetched via fetch_stats.get_game_stats:

1. A player becoming the sole new season leader in goals, assists, points,
   or penalties — but ONLY surfaced when that player actually recorded that
   stat in tonight's specific game (never just because the game happened to
   shuffle the rankings around them). Each category has its own cooldown in
   data/milestone_log.json so a back-and-forth race for the lead doesn't get
   called out every single episode.

2. A player extending an active goal-scoring streak (a goal in consecutive
   games played, not just a point) to 3+ games. This naturally only fires on
   the specific game the streak first crosses the threshold — if it keeps
   going, the streak grows past 3 next time and doesn't re-trigger, and if it
   breaks and later builds back up to 3, that's a new occurrence worth a
   fresh mention.
"""

import json
from pathlib import Path
from fetch_stats import get_game_stats

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
LOG_PATH = DATA_DIR / "milestone_log.json"

CATEGORIES = ["goals", "assists", "points", "penalties"]
SINGULAR = {"goals": "goal", "assists": "assist", "points": "point", "penalties": "penalty"}
LEADER_COOLDOWN_EPISODES = 3
GOAL_STREAK_THRESHOLD = 3


def load_milestone_log():
    if LOG_PATH.exists():
        log = json.loads(LOG_PATH.read_text())
    else:
        log = {"leader_cooldowns": {}}
    for c in CATEGORIES:
        log.setdefault("leader_cooldowns", {}).setdefault(c, 0)
    return log


def save_milestone_log(log):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(log, indent=2))


def _season_games_through(schedule, season, up_to_starts_at, include_current):
    all_games = sorted(schedule["games"], key=lambda g: g["starts_at"])
    if include_current:
        return [g for g in all_games if g.get("season") == season and g["starts_at"] <= up_to_starts_at]
    return [g for g in all_games if g.get("season") == season and g["starts_at"] < up_to_starts_at]


def _accumulate_totals(games):
    """Returns (player_totals, ordered_played_stats) for the given games list."""
    player_totals = {}
    played_stats = []

    def bump(name, field, amount=1):
        if not name or name == "Unknown":
            return
        player_totals.setdefault(name, {"goals": 0, "assists": 0, "points": 0, "penalties": 0})
        player_totals[name][field] += amount

    for g in games:
        try:
            s = get_game_stats(g["game_id"])
        except Exception:
            continue
        played_stats.append(s)
        for goal in s.get("our_goals", []):
            scorer = goal.get("scorer")
            if scorer and scorer != "Unknown":
                bump(scorer, "goals")
                bump(scorer, "points")
            for a in goal.get("assists", []):
                aname = a.get("name")
                if aname and aname != "Unknown":
                    bump(aname, "assists")
                    bump(aname, "points")
        for pen in s.get("penalties", []):
            if pen.get("team") == "us":
                bump(pen.get("player"), "penalties")

    return player_totals, played_stats


def _sole_leader(player_totals, field):
    """Returns (name, total) for the strict max in `field`, or (None, 0) if
    there's a tie for first or no data at all — a tie means nobody is
    reported as "the leader"."""
    ranked = sorted(
        ((n, d[field]) for n, d in player_totals.items() if d[field] > 0),
        key=lambda x: -x[1]
    )
    if not ranked:
        return None, 0
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return None, ranked[0][1]
    return ranked[0][0], ranked[0][1]


def _player_recorded_stat_tonight(stats, player, category):
    goals = stats.get("our_goals", [])
    if category == "goals":
        return any(g.get("scorer") == player for g in goals)
    if category == "assists":
        return any(a.get("name") == player for g in goals for a in g.get("assists", []))
    if category == "points":
        scored = any(g.get("scorer") == player for g in goals)
        assisted = any(a.get("name") == player for g in goals for a in g.get("assists", []))
        return scored or assisted
    if category == "penalties":
        return any(p.get("team") == "us" and p.get("player") == player for p in stats.get("penalties", []))
    return False


def _goal_streaks(played_stats):
    """Consecutive-games (that they actually played in) goal streaks, counting
    backward from the most recent game."""
    all_players = set()
    for s in played_stats:
        present = set(s.get("players_present", []))
        if s.get("goalie"):
            present.add(s["goalie"])
        all_players |= present

    streaks = {}
    for player in all_players:
        streak = 0
        for s in reversed(played_stats):
            present = set(s.get("players_present", []))
            if s.get("goalie"):
                present.add(s["goalie"])
            if player not in present:
                continue  # game they didn't play — doesn't break the streak
            scored = any(g.get("scorer") == player for g in s.get("our_goals", []))
            if scored:
                streak += 1
            else:
                break
        if streak > 0:
            streaks[player] = streak
    return streaks


def compute_milestones(schedule, game_id):
    """Returns (milestones, updated_log). `milestones` is a list of plain-
    English, fully real facts ready to hand to the model as-is."""
    log = load_milestone_log()

    all_games = sorted(schedule["games"], key=lambda g: g["starts_at"])
    current = next((g for g in all_games if g["game_id"] == game_id), None)
    if current is None:
        return [], log
    season = current.get("season")

    before_games = _season_games_through(schedule, season, current["starts_at"], include_current=False)
    after_games = _season_games_through(schedule, season, current["starts_at"], include_current=True)

    totals_before, _ = _accumulate_totals(before_games)
    totals_after, played_after = _accumulate_totals(after_games)

    try:
        tonight = get_game_stats(game_id)
    except Exception:
        tonight = {}

    milestones = []

    # --- New season leader, gated by cooldown + "did it happen tonight" ---
    for category in CATEGORIES:
        leader_before, _ = _sole_leader(totals_before, category)
        leader_after, total_after = _sole_leader(totals_after, category)

        changed = leader_after is not None and leader_after != leader_before
        did_it_tonight = changed and _player_recorded_stat_tonight(tonight, leader_after, category)
        cooldown_remaining = log["leader_cooldowns"][category]

        if did_it_tonight and cooldown_remaining <= 0:
            milestones.append(
                f"{leader_after} is now the season's sole leader in {category} "
                f"({total_after}), after recording a {SINGULAR[category]} tonight."
            )
            log["leader_cooldowns"][category] = LEADER_COOLDOWN_EPISODES
        else:
            log["leader_cooldowns"][category] = max(0, cooldown_remaining - 1)

    # --- Goal-scoring streaks reaching the threshold tonight ---
    streaks = _goal_streaks(played_after)
    for player, streak in streaks.items():
        if streak == GOAL_STREAK_THRESHOLD:
            milestones.append(
                f"{player} has scored a goal in {streak} straight games played, "
                "extending an active goal-scoring streak."
            )

    return milestones, log


def format_milestone_context(milestones):
    """Returns "" (section omitted) if nothing real qualifies this episode."""
    if not milestones:
        return ""
    lines = ["## Special Segment: Milestone Watch (insert after player_spotlight)"]
    lines.append(
        "The following are real, verified facts from tonight's game and season data. "
        "Insert a short milestone_watch segment after player_spotlight covering only "
        "what's listed below — do not invent any additional milestone, streak, or "
        "leadership claim beyond these:"
    )
    for m in milestones:
        lines.append(f"- {m}")
    return "\n".join(lines)
