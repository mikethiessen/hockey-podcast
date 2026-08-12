"""
Aggregates real per-player stats across all played games in the current season,
up to and including the game being scripted. Used to surface season-long
storylines (streaks, points leaders, frequent scoring connections, penalty
trends) without inventing anything — every number here comes directly from
game stats already fetched via fetch_stats.get_game_stats.
"""

from fetch_stats import get_game_stats

MIN_STREAK_TO_MENTION = 3
MIN_PAIR_COUNT_TO_MENTION = 2


def compute_season_stats(schedule, up_to_game_id):
    all_games = sorted(schedule["games"], key=lambda g: g["starts_at"])
    current = next((g for g in all_games if g["game_id"] == up_to_game_id), None)
    if current is None:
        return None
    season = current.get("season")

    season_games = [
        g for g in all_games
        if g.get("season") == season and g["starts_at"] <= current["starts_at"]
    ]

    played_stats = []
    for g in season_games:
        try:
            s = get_game_stats(g["game_id"])
            played_stats.append(s)
        except Exception:
            # Game hasn't happened yet or data isn't available — skip silently.
            continue

    player_totals = {}  # name -> {goals, assists, points, penalties}
    pair_counts = {}    # (assister, scorer) -> count
    game_log = []        # per-game: {point_players: set, present: set}

    def bump(name, field, amount=1):
        if not name or name == "Unknown":
            return
        player_totals.setdefault(name, {"goals": 0, "assists": 0, "points": 0, "penalties": 0})
        player_totals[name][field] += amount

    for s in played_stats:
        point_players = set()

        for goal in s.get("our_goals", []):
            scorer = goal.get("scorer")
            if scorer and scorer != "Unknown":
                bump(scorer, "goals")
                bump(scorer, "points")
                point_players.add(scorer)

            for a in goal.get("assists", []):
                aname = a.get("name")
                if aname and aname != "Unknown":
                    bump(aname, "assists")
                    bump(aname, "points")
                    point_players.add(aname)
                    if scorer and scorer != "Unknown":
                        key = (aname, scorer)
                        pair_counts[key] = pair_counts.get(key, 0) + 1

        for pen in s.get("penalties", []):
            if pen.get("team") == "us":
                bump(pen.get("player"), "penalties")

        present = set(s.get("players_present", []))
        if s.get("goalie"):
            present.add(s["goalie"])
        game_log.append({"point_players": point_players, "present": present})

    # Active point streaks: consecutive most recent games (that the player
    # actually played in) with at least one goal or assist.
    streaks = {}
    for player in player_totals:
        streak = 0
        for entry in reversed(game_log):
            if player not in entry["present"]:
                continue  # game they didn't play — doesn't break the streak
            if player in entry["point_players"]:
                streak += 1
            else:
                break
        if streak >= MIN_STREAK_TO_MENTION:
            streaks[player] = streak

    points_leaders = sorted(
        player_totals.items(), key=lambda kv: kv[1]["points"], reverse=True
    )[:5]

    top_pairs = sorted(
        [(a, sc, c) for (a, sc), c in pair_counts.items() if c >= MIN_PAIR_COUNT_TO_MENTION],
        key=lambda x: x[2], reverse=True
    )[:5]

    penalty_leaders = sorted(
        [(n, d["penalties"]) for n, d in player_totals.items() if d["penalties"] > 0],
        key=lambda x: x[1], reverse=True
    )[:3]

    return {
        "games_counted": len(played_stats),
        "points_leaders": points_leaders,
        "streaks": streaks,
        "top_assist_pairs": top_pairs,
        "penalty_leaders": penalty_leaders,
    }


def format_season_stats(season_stats):
    if not season_stats or season_stats["games_counted"] < 2:
        return (
            "## Season Stats\n"
            "Not enough games played yet this season to draw meaningful season-long "
            "storylines. Skip statistical storylines this episode rather than forcing "
            "one from too little data.\n"
        )

    lines = ["## Season Stats"]
    lines.append(
        f"(Computed from {season_stats['games_counted']} real game(s) played this "
        "season, through tonight. Every number below is real — use it as material, "
        "but do not add detail beyond what's listed.)\n"
    )

    if season_stats["points_leaders"]:
        lines.append("**Points leaders this season:**")
        for name, d in season_stats["points_leaders"]:
            lines.append(f"- {name}: {d['points']} points ({d['goals']}G, {d['assists']}A)")
        lines.append("")

    if season_stats["streaks"]:
        lines.append("**Active point streaks (3+ straight games played with a point):**")
        for name, streak in sorted(season_stats["streaks"].items(), key=lambda x: -x[1]):
            lines.append(f"- {name}: {streak} straight games with a point")
        lines.append("")

    if season_stats["top_assist_pairs"]:
        lines.append("**Frequent scoring connections this season:**")
        for assister, scorer, count in season_stats["top_assist_pairs"]:
            lines.append(f"- {assister} has assisted on {scorer}'s goal {count} times")
        lines.append("")

    if season_stats["penalty_leaders"]:
        lines.append("**Penalty trend this season:**")
        for name, count in season_stats["penalty_leaders"]:
            lines.append(f"- {name}: {count} penalties")
        lines.append("")

    lines.append(
        "If none of the above has anything notable for tonight's game specifically, "
        "it's fine to skip season storylines and lean on last episode's carried-forward "
        "storyline instead — don't force a stat in that isn't actually interesting."
    )

    return "\n".join(lines)
