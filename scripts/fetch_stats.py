"""
Fetches game stats from SportNinja API and returns a clean structured dict.
"""

import requests

TEAM_ID = "Nz7BgbzbxfrhWtft"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

# Our league plays three 12-minute periods, with a 5-minute overtime if needed.
REGULATION_PERIOD_MINUTES = 12
OVERTIME_PERIOD_MINUTES = 5

# The API's period_clock_time is a COUNTDOWN — time remaining in the period,
# same convention as the clock on a real scoreboard (e.g. "2:00" means 2
# minutes left, not 2 minutes elapsed). We convert it to elapsed time here so
# nothing downstream (prompt text or the model) has to guess which direction
# the clock runs.
def _seconds_from_clock(time_str):
    """Parse a 'MM:SS' string into total seconds. Returns None if unparseable."""
    if not time_str:
        return None
    try:
        mm, ss = str(time_str).split(":")
        return int(mm) * 60 + int(ss)
    except (ValueError, AttributeError):
        return None


def _format_seconds(total_seconds):
    m, s = divmod(total_seconds, 60)
    return f"{m}:{s:02d}"


def _remaining_to_elapsed(remaining, is_overtime):
    """Convert a 'MM:SS' time-remaining string into a 'MM:SS' elapsed string."""
    remaining_seconds = _seconds_from_clock(remaining)
    if remaining_seconds is None:
        return None

    period_minutes = OVERTIME_PERIOD_MINUTES if is_overtime else REGULATION_PERIOD_MINUTES
    total_seconds = period_minutes * 60
    elapsed_seconds = max(0, total_seconds - remaining_seconds)
    return _format_seconds(elapsed_seconds)


def fetch_game(game_id):
    url = f"https://canlan2-api.sportninja.net/v1/games/{game_id}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()["data"]


def parse_game(data):
    is_home = data["homeTeam"]["id"] == TEAM_ID
    our_team = data["homeTeam"] if is_home else data["visitingTeam"]
    opp_team = data["visitingTeam"] if is_home else data["homeTeam"]
    our_score = data["home_team_score"] if is_home else data["visiting_team_score"]
    opp_score = data["visiting_team_score"] if is_home else data["home_team_score"]

    if our_score > opp_score:
        result = "win"
    elif our_score < opp_score:
        result = "loss"
    else:
        result = "tie"

    # Parse periods
    periods = []
    for p in data.get("periods", []):
        periods.append({
            "name": p["period_type"]["name_full"],
            "is_overtime": p["period_type"]["is_overtime"],
            "goals_us": p["goals_home_count"] if is_home else p["goals_visiting_count"],
            "goals_them": p["goals_visiting_count"] if is_home else p["goals_home_count"],
            "shots_us": p["shots_home_count"] if is_home else p["shots_visiting_count"],
            "shots_them": p["shots_visiting_count"] if is_home else p["shots_home_count"],
        })

    # Period order, by position in the API's own periods array (1st, 2nd, 3rd,
    # OT, in that sequence) — used below to sort goals and penalties into one
    # true chronological timeline across period boundaries.
    period_order = {p["id"]: idx for idx, p in enumerate(data.get("periods", []))}

    # Parse goals - separate ours vs theirs (kept for existing consumers that
    # read these two lists directly), and also collect every goal into a single
    # sort key alongside penalties below to build one merged timeline.
    our_goals = []
    their_goals = []
    timeline_events = []  # (period_order, elapsed_seconds, event_dict) — sorted and emitted as game_timeline below

    for g in data.get("goals", []):
        shot = g.get("shot", {})
        scorer_id = shot.get("player_id")
        team_id = shot.get("team_id")
        period_id = g.get("period_id")

        # Find period name and whether it's an overtime period
        period_info = next(
            (p for p in data.get("periods", []) if p["id"] == period_id),
            None
        )
        period_name = period_info["period_type"]["name_full"] if period_info else "Unknown"
        period_is_ot = period_info["period_type"]["is_overtime"] if period_info else False

        assists = [
            {
                "name": f"{a['player']['name_first']} {a['player']['name_last']}",
                "type": a["type"]["name"]
            }
            for a in g.get("assists", [])
        ]

        raw_remaining = g.get("period_clock_time")
        elapsed = _remaining_to_elapsed(raw_remaining, period_is_ot)
        scorer_name = find_player_name(scorer_id, data.get("playerRosters", []))

        goal_entry = {
            "period": period_name,
            # Time elapsed into the period (e.g. "10:12" in a 12-minute period
            # means it happened late, with 1:48 left) and, explicitly, how much
            # time was left in the period when it happened — so a goal in the
            # last few seconds reads as such without anyone doing subtraction.
            "time_elapsed": elapsed,
            "time_remaining": raw_remaining,
            "assists": assists,
            "scorer": scorer_name,
        }

        team = "us" if team_id == TEAM_ID else "them"
        if team == "us":
            our_goals.append(goal_entry)
        else:
            their_goals.append(goal_entry)

        timeline_events.append((
            period_order.get(period_id, 999),
            _seconds_from_clock(elapsed) if elapsed is not None else -1,
            {
                "type": "goal",
                "team": team,
                "period": period_name,
                "time_elapsed": elapsed,
                "time_remaining": raw_remaining,
                "scorer": scorer_name,
                "assists": assists,
            },
        ))

    # Parse penalties
    penalties = []
    for o in data.get("offenses", []):
        player_name = find_player_name(o.get("player_id"), data.get("playerRosters", []))
        team_id = o.get("team_id")
        period_id = o.get("period_id")
        penalty_period_info = next(
            (p for p in data.get("periods", []) if p["id"] == period_id),
            None
        )
        penalty_period_is_ot = penalty_period_info["period_type"]["is_overtime"] if penalty_period_info else False
        penalty_period_name = penalty_period_info["period_type"]["name_full"] if penalty_period_info else "Unknown"

        raw_remaining = o.get("period_clock_time")
        elapsed = _remaining_to_elapsed(raw_remaining, penalty_period_is_ot)
        team = "us" if team_id == TEAM_ID else "them"

        penalty_entry = {
            "team": team,
            "player": player_name,
            "infraction": o["offense_type"]["name_full"],
            "severity": o["offense_severity"]["name"],
            "period": penalty_period_name,
            "time_elapsed": elapsed,
            "time_remaining": raw_remaining,
        }
        penalties.append(penalty_entry)

        timeline_events.append((
            period_order.get(period_id, 999),
            _seconds_from_clock(elapsed) if elapsed is not None else -1,
            {
                "type": "penalty",
                "team": team,
                "period": penalty_period_name,
                "time_elapsed": elapsed,
                "time_remaining": raw_remaining,
                "player": player_name,
                "infraction": o["offense_type"]["name_full"],
                "severity": o["offense_severity"]["name"],
            },
        ))

    # One merged, truly chronological timeline across both teams and all
    # periods — goals and penalties interleaved in the order they actually
    # happened, not two separate per-team lists the model would otherwise
    # have to interleave itself by comparing clock values across arrays.
    timeline_events.sort(key=lambda e: (e[0], e[1]))
    game_timeline = [e[2] for e in timeline_events]

    # Parse our roster for this game
    our_roster_entry = next(
        (r for r in data.get("playerRosters", []) if r["team_id"] == TEAM_ID),
        {}
    )
    players_present = []
    players_absent = []
    goalie = None
    for p in our_roster_entry.get("players", []):
        name = f"{p['name_first']} {p['name_last']}"
        is_goalie = p["player_type"]["is_goalie"]
        if p.get("is_playing"):
            if is_goalie and p.get("is_starting"):
                goalie = name
            elif not is_goalie:
                players_present.append(name)
        elif p.get("attendance_status") == 1:
            players_absent.append(name)

    return {
        "game_id": data["id"],
        "date": data["starts_at"][:10],
        "started_at": data.get("started_at"),
        "ended_at": data.get("ended_at"),
        "venue": data["venue"]["name"],
        "our_team": our_team["name"],
        "opponent": opp_team["name"],
        "home_or_away": "home" if is_home else "away",
        "our_score": our_score,
        "opp_score": opp_score,
        "result": result,
        "went_to_overtime": any(p["period_type"]["is_overtime"] for p in data.get("periods", [])),
        "periods": periods,
        "our_goals": our_goals,
        "their_goals": their_goals,
        "penalties": penalties,
        # Authoritative chronological order of events — use this, not our_goals/
        # their_goals/penalties separately, to describe the sequence of what
        # happened in the game. Those three lists are kept for other code that
        # reads them directly (season stats, recent-form tracking), but they are
        # NOT in game order relative to each other.
        "game_timeline": game_timeline,
        "players_present": players_present,
        "players_absent": players_absent,
        "goalie": goalie,
    }


def find_player_name(player_id, rosters):
    if not player_id:
        return "Unknown"
    for roster in rosters:
        for p in roster.get("players", []):
            if p["id"] == player_id:
                return f"{p['name_first']} {p['name_last']}"
    return "Unknown"


def get_game_stats(game_id):
    raw = fetch_game(game_id)
    return parse_game(raw)


if __name__ == "__main__":
    import sys, json
    game_id = sys.argv[1] if len(sys.argv) > 1 else "dcLlXKV6P2gm5LGe"
    stats = get_game_stats(game_id)
    print(json.dumps(stats, indent=2))
