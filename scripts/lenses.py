"""
Picks the "lenses" (angles on the season) that tonight's episode is built around.

Why this exists: left to choose freely from a menu, the model keeps picking the
same few items and episodes start to sound alike. Here code does the picking:

  1. work out which lenses have REAL data behind them tonight (no data, no lens)
  2. prefer lenses that weren't used in the last couple of episodes
  3. pick a few, using a random choice seeded by the game id (so a re-run of the
     same game with the same history picks the same lenses, which makes testing
     and debugging predictable)

The descriptions of each lens live in config/lenses.md so they can be edited
without touching Python. The rules for "has real data" stay here, in code.
"""

import random

from config_loader import load_config

LENS_COUNT = 3
RECENT_LENS_LOOKBACK = 2   # avoid lenses used in this many most-recent episodes
MIN_GAMES_FOR_STATS = 2    # below this, statistical lenses are off the table
MIN_GAMES_FOR_SPLITS = 3   # home/road splits need a few games each way to mean much
TEAM_STREAK_TO_FEATURE = 3

# Chosen first whenever eligible, because dropping them would let the show's
# accountability slip (a settled prediction only gets one chance to be raised).
FORCED_LENSES = ("accountability",)

# Only used to fill empty slots when too few data lenses are eligible.
FALLBACK_LENSES = ("season_outlook",)


def _stats_ok(ctx):
    ss = ctx.get("season_stats")
    return bool(ss) and ss.get("games_counted", 0) >= MIN_GAMES_FOR_STATS


def _two_way(ctx):
    return (ctx.get("season_stats") or {}).get("two_way") or {}


def _home_road_ok(ctx):
    la = ctx.get("look_ahead") or {}
    hr = la.get("home_road") or {}
    home, away = hr.get("home"), hr.get("away")
    games = (ctx.get("season_stats") or {}).get("games_counted", 0)
    return bool(home and away and home["gp"] and away["gp"]) and games >= MIN_GAMES_FOR_SPLITS


def _team_streak_ok(ctx):
    st = (ctx.get("look_ahead") or {}).get("streak") or {}
    return st.get("length", 0) >= TEAM_STREAK_TO_FEATURE


def _matchup_ok(ctx):
    la = ctx.get("look_ahead") or {}
    opp = la.get("next_opponent_record")
    ours = la.get("record")
    return bool(ctx.get("has_next_game") and opp and opp.get("gp") and ours and ours.get("gp"))


# lens id -> function(ctx) -> True when there is real data behind it tonight.
# Order here is the order ties are broken in before shuffling, so keep it stable.
ELIGIBILITY = {
    "accountability": lambda c: bool(c.get("pending_callbacks")),
    "trajectory": lambda c: _stats_ok(c) and bool(c["season_stats"].get("trajectories")),
    "chemistry": lambda c: _stats_ok(c) and bool(c["season_stats"].get("top_assist_pairs")),
    "streaks": lambda c: _stats_ok(c) and (bool(c["season_stats"].get("streaks")) or _team_streak_ok(c)),
    "discipline": lambda c: _stats_ok(c) and bool(
        c["season_stats"].get("penalty_leaders")
        or (_two_way(c).get("discipline") or {}).get("total")
    ),
    "goaltending": lambda c: _stats_ok(c) and bool(_two_way(c).get("goalies")),
    "period_splits": lambda c: _stats_ok(c) and bool(_two_way(c).get("by_period")),
    "leads_and_shots": lambda c: _stats_ok(c) and bool(
        (_two_way(c).get("leads") or {}).get("games_led_at_some_point")
        or any((_two_way(c).get("shot_result_mismatch") or {}).values())
    ),
    "home_road": _home_road_ok,
    "pace_outlook": lambda c: bool((c.get("look_ahead") or {}).get("pace")),
    "matchup": _matchup_ok,
    "rivalry": lambda c: bool(c.get("has_next_game") and c.get("prior_meetings")),
    "lineup": lambda c: _stats_ok(c) and bool(c["season_stats"].get("returns")),
    "firsts": lambda c: _stats_ok(c) and bool(c["season_stats"].get("rarities")),
    "season_outlook": lambda c: True,
}


def eligible_lenses(ctx):
    """Lens ids that have real data behind them tonight, in stable order."""
    return [lens for lens, ok in ELIGIBILITY.items() if ok(ctx)]


def recent_lenses_used(past_episodes, lookback=RECENT_LENS_LOOKBACK):
    """Lens ids used in the last `lookback` episodes (from their summary.json)."""
    used = set()
    for ep in past_episodes[-lookback:] if lookback else []:
        used.update(ep.get("lenses") or [])
    return used


def pick_lenses(eligible, recently_used, seed, count=LENS_COUNT):
    """Choose up to `count` lenses.

    Order of preference: forced lenses, then data lenses not used recently, then
    data lenses that were used recently, then fallback lenses. Within each tier
    the order is shuffled using `seed` so the choice is varied but repeatable.
    """
    rng = random.Random(str(seed))
    chosen = [l for l in FORCED_LENSES if l in eligible]

    pool = [l for l in eligible if l not in chosen and l not in FALLBACK_LENSES]
    fresh = [l for l in pool if l not in recently_used]
    stale = [l for l in pool if l in recently_used]
    rng.shuffle(fresh)
    rng.shuffle(stale)

    for lens in fresh + stale:
        if len(chosen) >= count:
            break
        chosen.append(lens)

    for lens in FALLBACK_LENSES:
        if len(chosen) >= count:
            break
        if lens in eligible and lens not in chosen:
            chosen.append(lens)

    return chosen


def load_lens_descriptions(config_dir=None):
    """Parse config/lenses.md into {lens_id: description}. Sections start with
    '## <lens_id>'; the text under the heading is the description."""
    text = load_config("lenses.md", config_dir)
    descriptions, current, buf = {}, None, []
    for line in text.splitlines():
        if line.startswith("## "):
            if current is not None:
                descriptions[current] = " ".join(" ".join(buf).split())
            current, buf = line[3:].strip(), []
        elif current is not None:
            buf.append(line.strip())
    if current is not None:
        descriptions[current] = " ".join(" ".join(buf).split())
    return descriptions


def format_featured_lenses(chosen, descriptions):
    """Text block for the brief's {{featured_lenses}} placeholder."""
    if not chosen:
        return ""
    missing = [l for l in chosen if l not in descriptions or not descriptions[l]]
    if missing:
        raise KeyError(
            "config/lenses.md has no description for lens(es): " + ", ".join(missing)
        )
    lines = [
        "This episode's featured lenses. Build the middle of the episode mainly around these. "
        "Each is an angle on tonight's real data: use them in whatever order and voice suits "
        "the hosts, add another angle if the data begs for one, and drop a lens if it turns out "
        "to have nothing real behind it.",
        "",
    ]
    for i, lens in enumerate(chosen, 1):
        lines.append(f"{i}. **{lens.replace('_', ' ')}** — {descriptions[lens]}")
    return "\n".join(lines)
