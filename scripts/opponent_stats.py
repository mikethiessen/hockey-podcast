"""
Computes an opponent's real season leaders by aggregating that team's own
completed games from the public SportNinja game API (the same data
fetch_stats.py already uses for the Village People).

Why aggregate instead of calling a stats endpoint: Canlan's team-statistics
endpoints require a login (401) or don't exist for anonymous callers, but the
division schedule and every game payload (goals, assists, penalties, rosters)
are public. So we do for opponents what season_stats.py does for our own team.

Used two ways by generate_script.py:
  - next_game_preview: the team we play NEXT (season leaders to watch)
  - game_recap: the team we JUST played (their season leaders, incl. tonight)

Never invents anything: if the opponent can't be resolved, has no completed
games, or the API fails, a plain "no data" note is returned that explicitly
tells the model not to make up players or stats.

Season scoping: only games in the schedule named by data/schedule.json's
"schedule_id" are counted, so stats reset when that ID is rolled over.

CLI test:  python scripts/opponent_stats.py "Slap Nuts"
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

import requests

DATA_DIR = Path(__file__).parent.parent / "data"
API_BASE = "https://canlan2-api.sportninja.net/v1"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}
OUR_TEAM_ID = "Nz7BgbzbxfrhWtft"  # Village People
FINAL_STATUS_ID = 9  # game_status_id 9 == final
TOP_N = 5
MAX_PAGES = 20  # safety stop on pagination


def _schedule_id():
    with open(DATA_DIR / "schedule.json") as f:
        return json.load(f)["schedule_id"]


def _fetch_games(schedule_id, team_id):
    """All non-cancelled games in the schedule involving team_id (server-side
    filter), walking every page. Stops on last_page, an empty page, or a page
    that adds no new games, so a missing/odd meta block can't cause a silent
    single-page read or an endless loop."""
    games, seen, page = [], set(), 1
    while page <= MAX_PAGES:
        params = {"page": page, "order": "asc", "exclude_cancelled_games": 1, "team_id": team_id}
        resp = requests.get(
            f"{API_BASE}/schedules/{schedule_id}/games",
            headers=HEADERS, params=params, timeout=20,
        )
        resp.raise_for_status()
        body = resp.json()
        batch = [g for g in body.get("data", []) if g["id"] not in seen]
        if not batch:
            break
        seen.update(g["id"] for g in batch)
        games.extend(batch)
        last_page = body.get("meta", {}).get("last_page")
        if last_page is not None and page >= last_page:
            break
        page += 1
    return games


def _fetch_game(game_id):
    resp = requests.get(f"{API_BASE}/games/{game_id}", headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.json()["data"]


def find_team_id(games, team_name):
    """Resolve a team name (as stored in schedule.json) to its SportNinja ID using
    a list of games. Exact match first, then case-insensitive."""
    names = {}
    for g in games:
        for side in ("homeTeam", "visitingTeam"):
            t = g.get(side) or {}
            if t.get("id") and t.get("name"):
                names[t["name"]] = t["id"]
    if team_name in names:
        return names[team_name]
    lowered = {n.lower(): i for n, i in names.items()}
    return lowered.get(team_name.lower())


def aggregate_team(team_id, final_games_full):
    """Aggregates one team's player totals and record from full game payloads."""
    players = defaultdict(lambda: {"name": None, "gp": 0, "goals": 0, "assists": 0, "penalties": 0})
    record = {"gp": 0, "w": 0, "l": 0, "t": 0, "gf": 0, "ga": 0}

    for data in final_games_full:
        is_home = data["homeTeam"]["id"] == team_id
        gf = data["home_team_score"] if is_home else data["visiting_team_score"]
        ga = data["visiting_team_score"] if is_home else data["home_team_score"]
        record["gp"] += 1
        record["gf"] += gf
        record["ga"] += ga
        record["w" if gf > ga else "l" if gf < ga else "t"] += 1

        # Roster: id -> name for everyone on this team's sheet, GP for those who played
        id_to_name = {}
        for roster in data.get("playerRosters", []):
            for p in roster.get("players", []):
                id_to_name[p["id"]] = f"{p['name_first']} {p['name_last']}".strip()
                if roster.get("team_id") == team_id:
                    pt = p.get("player_type") or {}
                    if p.get("is_playing") and not pt.get("is_goalie"):
                        e = players[p["id"]]
                        e["name"] = id_to_name[p["id"]]
                        e["gp"] += 1

        name_to_id = {n: i for i, n in id_to_name.items()}

        for g in data.get("goals", []):
            shot = g.get("shot") or {}
            if shot.get("team_id") != team_id:
                continue
            pid = shot.get("player_id")
            if pid:
                e = players[pid]
                e["name"] = e["name"] or id_to_name.get(pid)
                e["goals"] += 1
            for a in g.get("assists", []):
                ap = a.get("player") or {}
                apid = ap.get("id") or name_to_id.get(
                    f"{ap.get('name_first', '')} {ap.get('name_last', '')}".strip()
                )
                if apid:
                    e = players[apid]
                    e["name"] = e["name"] or f"{ap.get('name_first', '')} {ap.get('name_last', '')}".strip()
                    e["assists"] += 1

        for o in data.get("offenses", []):
            if o.get("team_id") == team_id and o.get("player_id"):
                e = players[o["player_id"]]
                e["name"] = e["name"] or id_to_name.get(o["player_id"])
                e["penalties"] += 1

    rows = []
    for e in players.values():
        if not e["name"]:
            continue
        e["points"] = e["goals"] + e["assists"]
        rows.append(e)
    rows.sort(key=lambda r: (-r["points"], -r["goals"], -r["assists"], r["name"]))
    return rows, record


def get_opponent_season_stats(team_name):
    """Returns {"team_id", "record", "players"} or None if the opponent can't be
    resolved. Raises requests exceptions on API failure (caller handles).

    The opponent's ID is found in OUR OWN team-filtered games (every opponent we
    play appears there), then that opponent's games are fetched with the same
    server-side team filter, so we get all of their games, not just one page of
    the whole league."""
    schedule_id = _schedule_id()
    our_games = _fetch_games(schedule_id, OUR_TEAM_ID)
    team_id = find_team_id(our_games, team_name)
    if not team_id:
        return None
    team_finals = [g for g in _fetch_games(schedule_id, team_id)
                   if g.get("game_status_id") == FINAL_STATUS_ID]
    full = [_fetch_game(g["id"]) for g in team_finals]
    players, record = aggregate_team(team_id, full)
    return {"team_id": team_id, "record": record, "players": players}


def format_opponent_stats(team_name, stats, purpose):
    """Prompt-ready text. purpose is 'preview' (next opponent) or 'recap' (team we
    just played; totals include tonight's game)."""
    header = (
        f"## Reference data (optional): opponent season leaders — {team_name} "
        + ("(team we play next)" if purpose == "preview" else "(team we played tonight)")
    )
    guard = (
        "Use ONLY the real numbers listed here. Do not add stats, positions, nicknames, "
        "or backstory for these players, and do not name any other opposing players."
    )
    if stats is None:
        return (
            f"{header}\nNo season data could be found for {team_name}. Do not invent "
            "players, stats, or standings for this team."
        )
    rec, players = stats["record"], stats["players"]
    if rec["gp"] == 0:
        return (
            f"{header}\n{team_name} has no completed games this season yet, so there are "
            "no season totals. Do not invent players or stats for this team."
        )
    scorers = [p for p in players if p["points"] > 0]
    scope = (
        "Season totals through their last completed game, which includes tonight's game against us."
        if purpose == "recap"
        else "Season totals through their last completed game."
    )
    lines = [
        header,
        f"{scope} Record: {rec['w']}-{rec['l']}-{rec['t']} in {rec['gp']} game(s), "
        f"goals for {rec['gf']}, goals against {rec['ga']}.",
    ]
    if not scorers:
        lines.append("No opposing player has recorded a point yet this season.")
    else:
        lines.append(f"Their top {min(TOP_N, len(scorers))} by points:")
        for i, p in enumerate(scorers[:TOP_N], 1):
            lines.append(
                f"{i}. {p['name']} — {p['points']} pts ({p['goals']} G, {p['assists']} A) "
                f"in {p['gp']} GP, {p['penalties']} penalties"
            )
        if len(scorers) > 1 and rec["gp"] <= 2:
            lines.append("(Small sample — only a game or two played, so treat these as early-season numbers.)")
    lines.append(guard)
    return "\n".join(lines)


def build_opponent_context(team_name, purpose):
    """Safe wrapper for generate_script.py: never raises, never invents."""
    if not team_name:
        return ""
    try:
        stats = get_opponent_season_stats(team_name)
    except Exception as e:  # network/API/shape problems must not break episode generation
        print(f"  Warning: opponent stats unavailable for {team_name}: {e}")
        return (
            f"## Reference data (optional): opponent season leaders — {team_name}\n"
            "Real season stats for this team could not be fetched this run. Do not invent "
            "players, stats, or standings for this team."
        )
    return format_opponent_stats(team_name, stats, purpose)


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "Slap Nuts"
    purpose = sys.argv[2] if len(sys.argv) > 2 else "preview"
    print(build_opponent_context(name, purpose))
