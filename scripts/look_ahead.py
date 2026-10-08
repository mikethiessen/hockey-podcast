"""
Forward-looking season context for the hosts to speculate from.

The existing season stats are backward-looking (leaders, streaks, chemistry).
Predictions and speculation need a "where is this heading" layer, so this
module adds one using only real data:

  - our record, goal differential, current streak, home/away split
  - the schedule picture: games played, games remaining, who's coming up,
    how many remaining games are rematches
  - simple pace arithmetic (current rate x games on the schedule), clearly
    labelled as a projection and never as a fact
  - the next opponent's record next to ours, when available

Plain code, no network. The numbers come from the season_stats dict and
data/schedule.json; the model is told to present projections as opinion.
"""

from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

MIN_GAMES_FOR_PACE = 2     # below this a "pace" is meaningless
SMALL_SAMPLE_GAMES = 3     # at or below this, flag pace as a rough talking point
UPCOMING_GAMES_SHOWN = 3
MIN_STREAK_TO_MENTION = 2
TOP_SCORERS_FOR_PACE = 3
LOCAL_TZ = "America/Winnipeg"


def _fmt_date(starts_at):
    """'Sun Oct 11' in league-local time. Date-only strings are used as-is."""
    try:
        dt = datetime.fromisoformat(starts_at)
        if dt.tzinfo is not None:
            dt = dt.astimezone(ZoneInfo(LOCAL_TZ))
        return dt.strftime("%a %b %-d")
    except (ValueError, TypeError):
        return str(starts_at)[:10]


def _current_streak(results):
    """('loss', 4) for four straight losses; (None, 0) if no results."""
    if not results:
        return None, 0
    last = results[-1]
    n = 0
    for r in reversed(results):
        if r != last:
            break
        n += 1
    return last, n


def compute_look_ahead(schedule, current_game_id, season_stats, next_opponent_record=None):
    """Return a dict of real schedule/record/pace facts, or None if the
    current game isn't in the schedule."""
    all_games = sorted(schedule["games"], key=lambda g: g["starts_at"])
    current = next((g for g in all_games if g["game_id"] == current_game_id), None)
    if current is None:
        return None
    season = current.get("season")

    season_games = [g for g in all_games if g.get("season") == season]
    position = next(i for i, g in enumerate(season_games) if g["game_id"] == current_game_id) + 1
    remaining = season_games[position:]
    faced = {g["opponent"] for g in season_games[:position]}

    rematch_counts = Counter(g["opponent"] for g in remaining if g["opponent"] in faced)

    record = (season_stats or {}).get("team_record")
    gp = record["gp"] if record else 0

    pace = None
    if record and gp >= MIN_GAMES_FOR_PACE and season_games:
        factor = len(season_games) / gp
        pace = {
            "games_on_schedule": len(season_games),
            "wins": round(record["w"] * factor),
            "goals_for": round(record["gf"] * factor),
            "goals_against": round(record["ga"] * factor),
            "top_scorers": [
                {"name": name, "points_now": d["points"], "points_pace": round(d["points"] * factor)}
                for name, d in (season_stats.get("points_leaders") or [])[:TOP_SCORERS_FOR_PACE]
                if d["points"] > 0
            ],
        }

    streak_kind, streak_len = _current_streak((season_stats or {}).get("results") or [])

    return {
        "season_total_games": len(season_games),
        "games_played": position,
        "games_remaining": len(remaining),
        "home_remaining": sum(1 for g in remaining if g.get("home_or_away") == "home"),
        "away_remaining": sum(1 for g in remaining if g.get("home_or_away") == "away"),
        "rematches_remaining": dict(rematch_counts),
        "upcoming": [
            {"date": _fmt_date(g["starts_at"]), "opponent": g["opponent"], "home_or_away": g.get("home_or_away")}
            for g in remaining[:UPCOMING_GAMES_SHOWN]
        ],
        "record": record,
        "home_road": (season_stats or {}).get("home_road"),
        "streak": {"kind": streak_kind, "length": streak_len},
        "pace": pace,
        "next_opponent_record": next_opponent_record,
        "small_sample": gp <= SMALL_SAMPLE_GAMES,
    }


def _rec_str(r):
    return f"{r['w']}-{r['l']}-{r['t']}"


def _diff_str(r):
    d = r["gf"] - r["ga"]
    return f"{d:+d}"


def format_look_ahead(la):
    """Prompt section for the hosts to look forward from. "" if nothing to say."""
    if not la:
        return ""

    lines = [
        "## Season Outlook (real schedule and results; projections are simple pace arithmetic)",
        "Every figure here is either real or straight arithmetic on real figures. Projections "
        "are opinion fodder: say \"on pace for\", never \"will finish with\".",
        "",
    ]

    rec = la.get("record")
    if rec and rec["gp"]:
        lines.append(
            f"- Record through tonight: {_rec_str(rec)} in {rec['gp']} game(s), "
            f"{rec['gf']} goals for, {rec['ga']} against (goal differential {_diff_str(rec)})."
        )

    st = la.get("streak") or {}
    if st.get("length", 0) >= MIN_STREAK_TO_MENTION:
        plural = {"win": "wins", "loss": "losses", "tie": "ties"}.get(st["kind"], f"{st['kind']}s")
        lines.append(f"- Current run: {st['length']} straight {plural}.")

    hr = la.get("home_road") or {}
    home, away = hr.get("home"), hr.get("away")
    if home and away and home["gp"] and away["gp"]:
        lines.append(
            f"- At home: {_rec_str(home)} ({home['gf']} GF, {home['ga']} GA). "
            f"On the road: {_rec_str(away)} ({away['gf']} GF, {away['ga']} GA)."
        )

    lines.append(
        f"- Schedule: {la['season_total_games']} games on the schedule, {la['games_played']} played, "
        f"{la['games_remaining']} remaining ({la['home_remaining']} home, {la['away_remaining']} away)."
    )

    if la["rematches_remaining"]:
        rem = ", ".join(f"{team} ({n})" for team, n in sorted(la["rematches_remaining"].items()))
        lines.append(f"- Remaining games against teams we've already faced this season: {rem}.")

    if la["upcoming"]:
        ups = "; ".join(
            f"{u['date']} vs {u['opponent']}" + (f" ({u['home_or_away']})" if u.get("home_or_away") else "")
            for u in la["upcoming"]
        )
        lines.append(f"- Coming up: {ups}.")

    opp = la.get("next_opponent_record")
    if opp and opp.get("gp"):
        lines.append(
            f"- The next opponent's record so far: {_rec_str(opp)} in {opp['gp']} game(s), "
            f"{opp['gf']} GF, {opp['ga']} GA (goal differential {_diff_str(opp)}). "
            "Compare it to ours if it makes a story."
        )

    pace = la.get("pace")
    if pace:
        lines.append(
            f"- If the current rate held across all {pace['games_on_schedule']} games: about "
            f"{pace['wins']} wins, {pace['goals_for']} goals for and {pace['goals_against']} against."
        )
        for sc in pace["top_scorers"]:
            lines.append(
                f"- {sc['name']} has {sc['points_now']} point(s) so far, which is a pace of about "
                f"{sc['points_pace']} over the full schedule."
            )
        if la.get("small_sample"):
            lines.append(
                "- Small sample: only a few games played, so treat any pace as a rough talking "
                "point, not a trend."
            )

    return "\n".join(lines)
