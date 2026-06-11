"""
Fetches game stats from SportNinja API and returns a clean structured dict.
"""

import requests

TEAM_ID = "Nz7BgbzbxfrhWtft"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}


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

    # Parse goals - separate ours vs theirs
    our_goals = []
    their_goals = []
    for g in data.get("goals", []):
        shot = g.get("shot", {})
        scorer_id = shot.get("player_id")
        team_id = shot.get("team_id")
        period_id = g.get("period_id")

        # Find period name
        period_name = next(
            (p["period_type"]["name_full"] for p in data.get("periods", []) if p["id"] == period_id),
            "Unknown"
        )

        assists = [
            {
                "name": f"{a['player']['name_first']} {a['player']['name_last']}",
                "type": a["type"]["name"]
            }
            for a in g.get("assists", [])
        ]

        goal_entry = {
            "period": period_name,
            "clock_time": g.get("period_clock_time"),
            "assists": assists,
        }

        if team_id == TEAM_ID:
            # Find scorer name from rosters
            scorer_name = find_player_name(scorer_id, data.get("playerRosters", []))
            goal_entry["scorer"] = scorer_name
            our_goals.append(goal_entry)
        else:
            scorer_name = find_player_name(scorer_id, data.get("playerRosters", []))
            goal_entry["scorer"] = scorer_name
            their_goals.append(goal_entry)

    # Parse penalties
    penalties = []
    for o in data.get("offenses", []):
        player_name = find_player_name(o.get("player_id"), data.get("playerRosters", []))
        team_id = o.get("team_id")
        penalties.append({
            "team": "us" if team_id == TEAM_ID else "them",
            "player": player_name,
            "infraction": o["offense_type"]["name_full"],
            "severity": o["offense_severity"]["name"],
            "period": next(
                (p["period_type"]["name_full"] for p in data.get("periods", []) if p["id"] == o.get("period_id")),
                "Unknown"
            ),
            "clock_time": o.get("period_clock_time"),
        })

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
