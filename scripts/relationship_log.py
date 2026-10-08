"""
Maintains data/relationship_log.json — a running log that lets the Casey/Gord
relationship build across a season.

Every entry originates from something a host actually said in a prior episode
(a checkable prediction, a running theory, or a distinct moment) — the model
tags it optionally at generation time. Resolution (did a prediction come true?)
and callback matching (does this moment relate to tonight's game?) are both done
here in plain code against real schedule/game/season data — never guessed or
reconstructed by the model.

What's tracked:
  - predictions: specific, checkable calls. Resolved by code against real results.
  - theories: a host's season-long hunch, e.g. "they win when X and Y connect".
    Code can't judge these, so the model reports whether each episode supports,
    complicates, or drops them (THEORY_UPDATE). Capped so the show doesn't pile up
    a dozen open arguments.
  - notable moments: one-sentence summaries of things the hosts said.

A settled prediction has to be raised on air. It stays in the queue until an
episode that includes it has actually been published (`surfaced`), instead of
being offered once and lost if the model happened to skip it.
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
LOG_PATH = DATA_DIR / "relationship_log.json"

SEASON_TYPES = {
    "team_result_streak",
    "player_goal_count",
    "player_points_streak",
    "penalty_trend",
}
NEXT_GAME_TYPES = {
    "next_game_result",
    "next_game_goals_for",
    "next_game_goals_against",
    "next_game_player_point",
    "next_game_player_goal",
}
PLAYER_NEXT_GAME_TYPES = {"next_game_player_point", "next_game_player_goal"}
CHECKABLE_TYPES = SEASON_TYPES | NEXT_GAME_TYPES

HOSTS = ("casey", "gord")
RESULTS = ("win", "loss", "tie")

MAX_OPEN_THEORIES = 3
MAX_CALLBACKS_PER_EPISODE = 3
MAX_MOMENT_MATCHES = 3
THEORY_VERDICTS = ("supports", "complicates", "dropped")
MAX_TEXT_CHARS = 280


# ---------------------------------------------------------------------------
# Loading / saving / migration
# ---------------------------------------------------------------------------

def _new_log(season):
    return {"season": season, "predictions": [], "notable_moments": [], "theories": []}


def _next_id(prefix, items):
    nums = []
    for item in items:
        iid = str(item.get("id", ""))
        if iid.startswith(prefix) and iid[len(prefix):].isdigit():
            nums.append(int(iid[len(prefix):]))
    return f"{prefix}{max(nums, default=0) + 1}"


def _migrate(log):
    """Bring an older log up to the current shape without losing anything.

    Predictions that were already resolved before this version existed are marked
    `surfaced` so a stale, context-free callback isn't dredged up weeks later.
    """
    log.setdefault("predictions", [])
    log.setdefault("notable_moments", [])
    log.setdefault("theories", [])
    for pred in log["predictions"]:
        if "surfaced" not in pred:
            pred["surfaced"] = bool(pred.get("resolved"))
    for pred in log["predictions"]:
        if not pred.get("id"):
            pred["id"] = _next_id("P", log["predictions"])
    return log


def load_relationship_log(season, path=None):
    path = Path(path or LOG_PATH)
    if path.exists():
        log = json.loads(path.read_text())
        if log.get("season") == season:
            return _migrate(log)
    return _new_log(season)


def save_relationship_log(log, path=None):
    path = Path(path or LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(log, indent=2))


# ---------------------------------------------------------------------------
# Predictions: describing, resolving, queueing
# ---------------------------------------------------------------------------

def describe_prediction(pred):
    """Plain-English version of what the host predicted, for the prompt."""
    t, target = pred["checkable_type"], pred.get("checkable_target", {})
    if t == "team_result_streak":
        n = target.get("window_games", 3)
        verb = "win" if target.get("metric", "wins") == "wins" else "lose"
        return f"that the team would {verb} its next {n} game{'s' if n != 1 else ''} in a row"
    if t == "player_goal_count":
        return f"that {target.get('player')} would reach {target.get('threshold')} goals this season"
    if t == "player_points_streak":
        return f"that {target.get('player')}'s point streak would reach {target.get('threshold')} games"
    if t == "penalty_trend":
        return f"that {target.get('player')} would reach {target.get('threshold')} penalties this season"
    if t == "next_game_result":
        return f"that the team would {target.get('result')} its next game"
    if t == "next_game_goals_for":
        return f"that the team would score at least {target.get('threshold')} goals in its next game"
    if t == "next_game_goals_against":
        return f"that the team would hold its next opponent to {target.get('threshold')} goals or fewer"
    if t == "next_game_player_point":
        return f"that {target.get('player')} would record a point in the next game"
    if t == "next_game_player_goal":
        return f"that {target.get('player')} would score in the next game"
    return "something checkable"


def _points_in_game(stats, player):
    n = 0
    for goal in stats.get("our_goals", []):
        if goal.get("scorer") == player:
            n += 1
        n += sum(1 for a in goal.get("assists", []) if a.get("name") == player)
    return n


def _check_next_game(ctype, target, stats):
    """Returns (outcome, detail) for a next-game prediction against real stats.
    outcome is "confirmed", "missed", or "void" (a named player didn't play)."""
    score = f"{stats['result'].upper()} {stats['our_score']}-{stats['opp_score']} vs {stats['opponent']}"

    if ctype in PLAYER_NEXT_GAME_TYPES:
        player = target.get("player")
        if player not in stats.get("players_present", []):
            return "void", f"{player} did not play ({score})"
        if ctype == "next_game_player_point":
            pts = _points_in_game(stats, player)
            return ("confirmed" if pts >= 1 else "missed"), f"{score}; {player} had {pts} point(s)"
        goals = sum(1 for g in stats.get("our_goals", []) if g.get("scorer") == player)
        return ("confirmed" if goals >= 1 else "missed"), f"{score}; {player} scored {goals} goal(s)"

    if ctype == "next_game_result":
        ok = stats["result"] == target.get("result")
    elif ctype == "next_game_goals_for":
        ok = stats["our_score"] >= target.get("threshold", 0)
    else:  # next_game_goals_against
        ok = stats["opp_score"] <= target.get("threshold", 0)
    return ("confirmed" if ok else "missed"), score


def resolve_predictions(log, schedule, get_game_stats_fn, season_stats_fn, up_to_game_id):
    """Checks unresolved predictions against real data now available.
    Returns the list of predictions newly resolved on this run.

    Only games up to and including `up_to_game_id` count as played. That fixes two
    problems: a prediction about "the next game" now resolves at the very next
    episode (the game just played is real data even though its episode isn't
    marked generated yet), and re-generating an old game in test mode can't
    resolve anything against games that come after it.
    """
    newly_resolved = []
    all_games = sorted(schedule["games"], key=lambda g: g["starts_at"])
    current_index = next((i for i, g in enumerate(all_games) if g["game_id"] == up_to_game_id), None)
    if current_index is None:
        return newly_resolved

    stats_cache = {}

    def game_stats(game_id):
        if game_id not in stats_cache:
            try:
                stats_cache[game_id] = get_game_stats_fn(game_id)
            except Exception:
                stats_cache[game_id] = None
        return stats_cache[game_id]

    season_cache = {}

    def season_stats():
        if "v" not in season_cache:
            season_cache["v"] = season_stats_fn(schedule, up_to_game_id)
        return season_cache["v"]

    def following_games(made_index, season, window):
        games = [g for g in all_games[made_index + 1: current_index + 1] if g.get("season") == season]
        return games[:window] if len(games) >= window else None

    for pred in log["predictions"]:
        if pred["resolved"]:
            continue

        made_index = next((i for i, g in enumerate(all_games) if g["game_id"] == pred["game_id"]), None)
        # Never resolve a prediction against the episode it was made in, or earlier.
        if made_index is None or made_index >= current_index:
            continue

        ctype = pred["checkable_type"]
        target = pred["checkable_target"]
        pred_season = all_games[made_index].get("season")

        if ctype == "team_result_streak":
            window = target.get("window_games", 3)
            metric = target.get("metric", "wins")
            following = following_games(made_index, pred_season, window)
            if following is None:
                continue  # not enough real games played yet this season to check this

            results = []
            for g in following:
                s = game_stats(g["game_id"])
                if s:
                    results.append(s["result"])
            if len(results) < window:
                continue

            outcome = all(r == "win" for r in results) if metric == "wins" else all(r == "loss" for r in results)
            pred["resolved"] = True
            pred["outcome"] = "confirmed" if outcome else "missed"
            pred["outcome_detail"] = ", ".join(r.upper() for r in results)
            newly_resolved.append(pred)

        elif ctype in NEXT_GAME_TYPES:
            following = following_games(made_index, pred_season, 1)
            if following is None:
                continue
            s = game_stats(following[0]["game_id"])
            if not s:
                continue
            outcome, detail = _check_next_game(ctype, target, s)
            pred["resolved"] = True
            pred["outcome"] = outcome
            pred["outcome_detail"] = detail
            if outcome == "void":
                pred["surfaced"] = True  # nothing fair to say about it on air
            else:
                newly_resolved.append(pred)

        elif ctype in ("player_goal_count", "player_points_streak", "penalty_trend"):
            stats = season_stats()
            if not stats:
                continue
            player = target.get("player")

            if ctype == "player_goal_count":
                found = next((d for n, d in stats.get("points_leaders", []) if n == player), None)
                if found is None:
                    continue
                threshold = target.get("threshold")
                outcome = found["goals"] >= threshold
                pred["outcome_detail"] = f"{player} has {found['goals']} goals this season (real data)"
            elif ctype == "player_points_streak":
                streak = stats.get("streaks", {}).get(player)
                if streak is None:
                    continue
                threshold = target.get("threshold", 3)
                outcome = streak >= threshold
                pred["outcome_detail"] = f"{player} is on a {streak}-game point streak (real data)"
            else:  # penalty_trend
                leaders = dict(stats.get("penalty_leaders", []))
                count = leaders.get(player)
                if count is None:
                    continue
                threshold = target.get("threshold")
                outcome = count >= threshold
                pred["outcome_detail"] = f"{player} has {count} penalties this season (real data)"

            pred["resolved"] = True
            pred["outcome"] = "confirmed" if outcome else "missed"
            newly_resolved.append(pred)

    return newly_resolved


def pending_callbacks(log):
    """Settled predictions that haven't been raised on air yet, oldest first."""
    pending = [
        p for p in log["predictions"]
        if p.get("resolved") and not p.get("surfaced") and p.get("outcome") in ("confirmed", "missed")
    ]
    return pending[:MAX_CALLBACKS_PER_EPISODE]


def mark_surfaced(log, prediction_ids):
    """Record that an episode containing these callbacks has been published."""
    ids = set(prediction_ids)
    for pred in log["predictions"]:
        if pred.get("id") in ids:
            pred["surfaced"] = True


def add_predictions(log, new_predictions):
    for pred in new_predictions:
        pred["id"] = _next_id("P", log["predictions"])
        log["predictions"].append(pred)


# ---------------------------------------------------------------------------
# Theories
# ---------------------------------------------------------------------------

def open_theories(log):
    return [t for t in log["theories"] if t.get("status") == "open"]


def can_add_theory(log):
    return len(open_theories(log)) < MAX_OPEN_THEORIES


def apply_theory_tags(log, new_theories, updates, game_id):
    """Apply parsed THEORY / THEORY_UPDATE tags. Updates go first so dropping a
    theory can free a slot for a new one. Returns (added, updated)."""
    added = updated = 0

    for u in updates:
        theory = next(
            (t for t in log["theories"] if t["id"] == u["id"] and t.get("status") == "open"), None
        )
        if not theory:
            continue
        theory["history"].append({"game_id": game_id, "verdict": u["verdict"], "note": u["note"]})
        theory["last_touched_game_id"] = game_id
        if u["verdict"] == "dropped":
            theory["status"] = "dropped"
        updated += 1

    for t in new_theories:
        if not can_add_theory(log):
            break
        entry = dict(t)
        entry["id"] = _next_id("T", log["theories"])
        log["theories"].append(entry)
        added += 1

    return added, updated


# ---------------------------------------------------------------------------
# Moments
# ---------------------------------------------------------------------------

def match_notable_moments(log, opponent, margin_bucket, exclude_game_id):
    """Only real matches (same opponent or same score-margin bucket) — never
    a fuzzy or reconstructed match. Capped to the most recent few so an old
    bucket doesn't keep resurfacing every episode."""
    matches = []
    for m in log.get("notable_moments", []):
        if m["game_id"] == exclude_game_id:
            continue
        keys = m.get("match_keys", {})
        if keys.get("opponent") == opponent or keys.get("score_margin_bucket") == margin_bucket:
            matches.append(m)
    return matches[-MAX_MOMENT_MATCHES:]


# ---------------------------------------------------------------------------
# Prompt section
# ---------------------------------------------------------------------------

def _where(entry):
    if entry.get("opponent") and entry.get("date"):
        return f"in the episode vs {entry['opponent']} ({entry['date']})"
    return "in an earlier episode"


def format_relationship_context(callbacks, moment_matches, theories=None):
    """Builds the optional prompt section. Returns "" (section omitted
    entirely) if there's nothing real to surface this episode."""
    theories = theories or []
    if not callbacks and not moment_matches and not theories:
        return ""

    lines = ["## Relationship Context (real, from prior episodes)"]
    lines.append(
        "Everything below actually happened in a prior episode. A settled prediction "
        "is owed an on-air resolution. Open theories and prior moments are optional: "
        "use one only if it genuinely fits tonight's episode naturally.\n"
    )

    if callbacks:
        lines.append("**Predictions now settled by real results (settle these on air):**")
        for p in callbacks:
            who = p["made_by"].capitalize()
            status = "came true" if p["outcome"] == "confirmed" else "didn't pan out"
            lines.append(
                f"- {who} predicted, {_where(p)}, {describe_prediction(p)}. "
                f"It {status}: {p['outcome_detail']}"
            )
        lines.append("")

    if theories:
        lines.append(
            "**Open theories (the hosts' own running arguments). If you revisit one, record "
            "the verdict with a THEORY_UPDATE tag using its id:**"
        )
        for t in theories:
            who = t["made_by"].capitalize()
            line = f"- [{t['id']}] {who} {_where(t)}: \"{t['thesis']}\""
            if t.get("history"):
                last = t["history"][-1]
                line += f" (last check: {last['verdict']} — {last['note']})"
            lines.append(line)
        lines.append("")

    if moment_matches:
        lines.append("**Prior moments relevant to tonight's opponent/result type:**")
        for m in moment_matches:
            lines.append(f"- {m['who'].capitalize()} previously: {m['summary']}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tag parsing (trailing, never-spoken lines the model may add)
# ---------------------------------------------------------------------------

def _clip(text):
    text = " ".join(text.split())
    return text[:MAX_TEXT_CHARS]


def extract_relationship_tags(script, game_id, context=None):
    """Strips optional trailing PREDICTION:/MOMENT:/THEORY:/THEORY_UPDATE: tag
    lines from the script (never spoken).

    Returns (clean_script, new_predictions, new_moments, new_theories, theory_updates).
    A tag line is always removed from the script, even if it turns out to be
    malformed, so a bad tag can never be read aloud.

    `context` is an optional {"date", "opponent"} for the game being scripted,
    stored on predictions and theories so later callbacks can say where they came
    from.
    """
    context = context or {}
    lines = script.strip().splitlines()
    clean_lines = []
    new_predictions, new_moments, new_theories, theory_updates = [], [], [], []

    for line in lines:
        stripped = line.strip()

        # THEORY_UPDATE must be checked before THEORY (it starts with the same word).
        if stripped.startswith("THEORY_UPDATE:"):
            parts = [p.strip() for p in stripped[len("THEORY_UPDATE:"):].split("|", 2)]
            if len(parts) == 3 and parts[1].lower() in THEORY_VERDICTS and parts[0]:
                theory_updates.append({
                    "id": parts[0].upper(),
                    "verdict": parts[1].lower(),
                    "note": _clip(parts[2]),
                })
            continue

        if stripped.startswith("THEORY:"):
            parts = [p.strip() for p in stripped[len("THEORY:"):].split("|", 1)]
            if len(parts) == 2 and parts[0].lower() in HOSTS and parts[1]:
                new_theories.append({
                    "game_id": game_id,
                    "made_by": parts[0].lower(),
                    "thesis": _clip(parts[1]),
                    "status": "open",
                    "history": [],
                    "date": context.get("date"),
                    "opponent": context.get("opponent"),
                })
            continue

        if stripped.startswith("PREDICTION:"):
            parts = [p.strip() for p in stripped[len("PREDICTION:"):].split("|")]
            if len(parts) >= 3:
                made_by, ctype = parts[0].lower(), parts[1]
                if ctype in CHECKABLE_TYPES:
                    entry = _build_prediction_entry(game_id, made_by, ctype, parts[2:], context)
                    if entry:
                        new_predictions.append(entry)
            continue

        if stripped.startswith("MOMENT:"):
            parts = [p.strip() for p in stripped[len("MOMENT:"):].split("|")]
            if len(parts) >= 3:
                who, summary, bucket = parts[0].lower(), parts[1], parts[2]
                new_moments.append({
                    "game_id": game_id,
                    "who": who,
                    "summary": summary,
                    "match_keys": {"score_margin_bucket": bucket},
                })
            continue

        clean_lines.append(line)

    clean_script = "\n".join(clean_lines).strip()
    return clean_script, new_predictions, new_moments, new_theories, theory_updates


def _build_prediction_entry(game_id, made_by, ctype, rest, context=None):
    context = context or {}
    if made_by not in HOSTS:
        return None

    base = {
        "game_id": game_id,
        "made_by": made_by,
        "checkable_type": ctype,
        "resolved": False,
        "outcome": None,
        "surfaced": False,
        "date": context.get("date"),
        "opponent": context.get("opponent"),
    }

    if ctype == "team_result_streak":
        if len(rest) < 1:
            return None
        metric = rest[0]
        try:
            window = int(rest[1]) if len(rest) > 1 else 3
        except ValueError:
            window = 3
        return {**base, "checkable_target": {"metric": metric, "window_games": window}}

    if ctype in ("player_goal_count", "player_points_streak", "penalty_trend"):
        if len(rest) < 2:
            return None
        player = rest[0]
        try:
            threshold = int(rest[1])
        except ValueError:
            return None
        return {**base, "checkable_target": {"player": player, "threshold": threshold}}

    if ctype == "next_game_result":
        result = rest[0].lower() if rest else ""
        if result not in RESULTS:
            return None
        return {**base, "checkable_target": {"result": result}}

    if ctype in ("next_game_goals_for", "next_game_goals_against"):
        if not rest:
            return None
        try:
            threshold = int(rest[0])
        except ValueError:
            return None
        return {**base, "checkable_target": {"threshold": threshold}}

    if ctype in PLAYER_NEXT_GAME_TYPES:
        player = rest[0] if rest else ""
        if not player:
            return None
        return {**base, "checkable_target": {"player": player}}

    return None
