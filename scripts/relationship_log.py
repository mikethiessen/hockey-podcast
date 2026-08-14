"""
Maintains data/relationship_log.json — a running log that lets the Casey/Gord
relationship build across a season.

Every entry originates from something a host actually said in a prior episode
(a checkable prediction, or a distinct moment) — the model tags it optionally
at generation time. Resolution (did a prediction come true?) and callback
matching (does this moment relate to tonight's game?) are both done here in
plain code against real schedule/game/season data — never guessed or
reconstructed by the model.
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
LOG_PATH = DATA_DIR / "relationship_log.json"

CHECKABLE_TYPES = {
    "team_result_streak",
    "player_goal_count",
    "player_points_streak",
    "penalty_trend",
}


def load_relationship_log(season):
    if LOG_PATH.exists():
        log = json.loads(LOG_PATH.read_text())
        if log.get("season") == season:
            return log
    return {"season": season, "predictions": [], "notable_moments": []}


def save_relationship_log(log):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(log, indent=2))


def resolve_predictions(log, schedule, get_game_stats_fn, season_stats_fn, up_to_game_id):
    """Checks unresolved predictions against real data now available.
    Returns the list of predictions newly resolved on this run (so the
    caller can choose to surface them, once, as fresh context)."""
    newly_resolved = []
    all_games = sorted(schedule["games"], key=lambda g: g["starts_at"])
    current_index = next((i for i, g in enumerate(all_games) if g["game_id"] == up_to_game_id), None)
    if current_index is None:
        return newly_resolved

    for pred in log["predictions"]:
        if pred["resolved"]:
            continue

        made_index = next((i for i, g in enumerate(all_games) if g["game_id"] == pred["game_id"]), None)
        if made_index is None:
            continue

        ctype = pred["checkable_type"]
        target = pred["checkable_target"]

        if ctype == "team_result_streak":
            window = target.get("window_games", 3)
            metric = target.get("metric", "wins")
            following = all_games[made_index + 1: made_index + 1 + window]
            if len(following) < window or not all(g.get("episode_generated") for g in following):
                continue  # not enough real games played yet to check this

            results = []
            for g in following:
                try:
                    results.append(get_game_stats_fn(g["game_id"])["result"])
                except Exception:
                    pass
            if len(results) < window:
                continue

            outcome = all(r == "win" for r in results) if metric == "wins" else all(r == "loss" for r in results)
            pred["resolved"] = True
            pred["outcome"] = "confirmed" if outcome else "missed"
            pred["outcome_detail"] = ", ".join(r.upper() for r in results)
            newly_resolved.append(pred)

        elif ctype in ("player_goal_count", "player_points_streak", "penalty_trend"):
            stats = season_stats_fn(schedule, up_to_game_id)
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


def match_notable_moments(log, opponent, margin_bucket, exclude_game_id):
    """Only real matches (same opponent or same score-margin bucket) — never
    a fuzzy or reconstructed match."""
    matches = []
    for m in log.get("notable_moments", []):
        if m["game_id"] == exclude_game_id:
            continue
        keys = m.get("match_keys", {})
        if keys.get("opponent") == opponent or keys.get("score_margin_bucket") == margin_bucket:
            matches.append(m)
    return matches


def format_relationship_context(newly_resolved, moment_matches):
    """Builds the optional prompt section. Returns "" (section omitted
    entirely) if there's nothing real to surface this episode."""
    if not newly_resolved and not moment_matches:
        return ""

    lines = ["## Relationship Context (real, from prior episodes)"]
    lines.append(
        "Everything below actually happened in a prior episode. Use it only if it "
        "genuinely fits tonight's episode naturally — skip anything that doesn't.\n"
    )

    if newly_resolved:
        lines.append("**Predictions that can now be checked against real results:**")
        for p in newly_resolved:
            who = p["made_by"].capitalize()
            status = "came true" if p["outcome"] == "confirmed" else "didn't pan out"
            lines.append(f"- {who} predicted this a prior episode. It {status}: {p['outcome_detail']}")
        lines.append("")

    if moment_matches:
        lines.append("**Prior moments relevant to tonight's opponent/result type:**")
        for m in moment_matches:
            lines.append(f"- {m['who'].capitalize()} previously: {m['summary']}")
        lines.append("")

    return "\n".join(lines)


def extract_relationship_tags(script, game_id):
    """Strips optional trailing PREDICTION:/MOMENT: tag lines from the script
    (never spoken) and returns (clean_script, new_predictions, new_moments)."""
    lines = script.strip().splitlines()
    clean_lines = []
    new_predictions = []
    new_moments = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("PREDICTION:"):
            parts = [p.strip() for p in stripped[len("PREDICTION:"):].split("|")]
            if len(parts) >= 3:
                made_by, ctype = parts[0].lower(), parts[1]
                if ctype in CHECKABLE_TYPES:
                    entry = _build_prediction_entry(game_id, made_by, ctype, parts[2:])
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
    return clean_script, new_predictions, new_moments


def _build_prediction_entry(game_id, made_by, ctype, rest):
    if ctype == "team_result_streak":
        if len(rest) < 1:
            return None
        metric = rest[0]
        try:
            window = int(rest[1]) if len(rest) > 1 else 3
        except ValueError:
            window = 3
        return {
            "game_id": game_id,
            "made_by": made_by,
            "checkable_type": ctype,
            "checkable_target": {"metric": metric, "window_games": window},
            "resolved": False,
            "outcome": None,
        }

    if ctype in ("player_goal_count", "player_points_streak", "penalty_trend"):
        if len(rest) < 2:
            return None
        player = rest[0]
        try:
            threshold = int(rest[1])
        except ValueError:
            return None
        return {
            "game_id": game_id,
            "made_by": made_by,
            "checkable_type": ctype,
            "checkable_target": {"player": player, "threshold": threshold},
            "resolved": False,
            "outcome": None,
        }

    return None
