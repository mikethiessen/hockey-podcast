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
        game_scorers = {}
        game_penalty_players = []

        for goal in s.get("our_goals", []):
            scorer = goal.get("scorer")
            if scorer and scorer != "Unknown":
                bump(scorer, "goals")
                bump(scorer, "points")
                point_players.add(scorer)
                game_scorers[scorer] = game_scorers.get(scorer, 0) + 1

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
                if pen.get("player") and pen["player"] != "Unknown":
                    game_penalty_players.append(pen["player"])

        present = set(s.get("players_present", []))
        if s.get("goalie"):
            present.add(s["goalie"])
        game_log.append({
            "point_players": point_players,
            "present": present,
            "scorers": game_scorers,
            "penalty_players": game_penalty_players,
            "goals_for": len(s.get("our_goals", [])),
            "result": s.get("result"),
            "goalie": s.get("goalie"),
            "periods": s.get("periods", []),
            "our_score": s.get("our_score"),
            "opp_score": s.get("opp_score"),
        })

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

    trajectories = _compute_trajectories(game_log)
    returns = _compute_returns(game_log)
    rarities = _compute_rarities(game_log)
    two_way = _compute_two_way_season(game_log)

    return {
        "games_counted": len(played_stats),
        "points_leaders": points_leaders,
        "streaks": streaks,
        "top_assist_pairs": top_pairs,
        "penalty_leaders": penalty_leaders,
        "trajectories": trajectories,
        "returns": returns,
        "rarities": rarities,
        "two_way": two_way,
    }


def _compute_two_way_season(game_log):
    """Season-level aggregates covering the parts of the game that don't show
    up in a scoresheet: goaltending workload, period tendencies, discipline
    over time, leads held, and shots-vs-result mismatches. Everything is
    counted from real per-game data already fetched — no estimation, and no
    interpretation baked in. What any of it *means* is left open."""
    if not game_log:
        return {}

    out = {}

    # --- Goalie workload across the season ---
    goalie_games = {}
    for e in game_log:
        g = e.get("goalie")
        if not g:
            continue
        shots_faced = sum(p.get("shots_them") or 0 for p in e.get("periods", []))
        rec = goalie_games.setdefault(g, {"games": 0, "shots_faced": 0, "goals_against": 0})
        rec["games"] += 1
        rec["shots_faced"] += shots_faced
        rec["goals_against"] += (e.get("opp_score") or 0)
    if goalie_games:
        out["goalies"] = [
            {
                "name": n,
                "games": d["games"],
                "shots_faced": d["shots_faced"],
                "goals_against": d["goals_against"],
                "avg_shots_faced": round(d["shots_faced"] / d["games"], 1),
            }
            for n, d in sorted(goalie_games.items(), key=lambda kv: -kv[1]["games"])
        ]

    # --- Period tendencies: goal and shot differential by period ---
    period_totals = {}
    for e in game_log:
        for p in e.get("periods", []):
            if p.get("is_overtime"):
                continue
            name = p.get("name") or "Unknown"
            rec = period_totals.setdefault(
                name, {"goals_us": 0, "goals_them": 0, "shots_us": 0, "shots_them": 0}
            )
            rec["goals_us"] += p.get("goals_us") or 0
            rec["goals_them"] += p.get("goals_them") or 0
            rec["shots_us"] += p.get("shots_us") or 0
            rec["shots_them"] += p.get("shots_them") or 0
    if period_totals:
        out["by_period"] = [
            {"period": name, **rec} for name, rec in period_totals.items()
        ]

    # --- Discipline over time: penalties per game, first half vs second half ---
    pen_counts = [len(e["penalty_players"]) for e in game_log]
    if len(pen_counts) >= 4:
        mid = len(pen_counts) // 2
        out["discipline"] = {
            "total": sum(pen_counts),
            "per_game": round(sum(pen_counts) / len(pen_counts), 1),
            "earlier_per_game": round(sum(pen_counts[:mid]) / mid, 1),
            "recent_per_game": round(sum(pen_counts[mid:]) / (len(pen_counts) - mid), 1),
        }
    elif pen_counts:
        out["discipline"] = {
            "total": sum(pen_counts),
            "per_game": round(sum(pen_counts) / len(pen_counts), 1),
        }

    # --- Leads held vs. not, from period-by-period running score ---
    led_after_a_period = 0
    led_and_won = 0
    for e in game_log:
        running_us = running_them = 0
        ever_led = False
        for p in e.get("periods", []):
            running_us += p.get("goals_us") or 0
            running_them += p.get("goals_them") or 0
            if running_us > running_them:
                ever_led = True
        if ever_led:
            led_after_a_period += 1
            if e.get("result") == "win":
                led_and_won += 1
    if led_after_a_period:
        out["leads"] = {
            "games_led_at_some_point": led_after_a_period,
            "of_those_won": led_and_won,
        }

    # --- Shots vs. result mismatches ---
    outshot_lost = 0
    outshot_by_opp_won = 0
    for e in game_log:
        su = sum(p.get("shots_us") or 0 for p in e.get("periods", []))
        st = sum(p.get("shots_them") or 0 for p in e.get("periods", []))
        if su > st and e.get("result") == "loss":
            outshot_lost += 1
        if st > su and e.get("result") == "win":
            outshot_by_opp_won += 1
    if outshot_lost or outshot_by_opp_won:
        out["shot_result_mismatch"] = {
            "outshot_opponent_but_lost": outshot_lost,
            "were_outshot_but_won": outshot_by_opp_won,
        }

    return out


def _points_after_n_games(game_log, n):
    """Cumulative points per player through the first `n` games of the log."""
    totals = {}
    for entry in game_log[:n]:
        for p in entry["point_players"]:
            # point_players is a set per game, but a player can have multiple
            # points in one game — recount from scorers/assists is not available
            # here, so this is "games with a point," used only for ranking shape.
            totals[p] = totals.get(p, 0) + 1
    return totals


def _rank_map(totals):
    """name -> 1-based rank, ties share the better rank."""
    ranked = sorted(totals.items(), key=lambda kv: -kv[1])
    ranks = {}
    last_val = None
    last_rank = 0
    for i, (name, val) in enumerate(ranked, start=1):
        if val != last_val:
            last_rank = i
            last_val = val
        ranks[name] = last_rank
    return ranks


def _compute_trajectories(game_log, lookback=3):
    """#1 — Who is climbing or sliding in the productivity ranking compared to
    where they stood `lookback` games ago. Real movement, not invented."""
    if len(game_log) < lookback + 2:
        return []

    then_totals = _points_after_n_games(game_log, len(game_log) - lookback)
    now_totals = _points_after_n_games(game_log, len(game_log))
    if not then_totals or not now_totals:
        return []

    then_ranks = _rank_map(then_totals)
    now_ranks = _rank_map(now_totals)

    moves = []
    for name, now_rank in now_ranks.items():
        then_rank = then_ranks.get(name)
        if then_rank is None:
            # Newly on the board entirely — that's a "first appearance" arc.
            if now_totals[name] >= 2:
                moves.append({
                    "player": name,
                    "direction": "new",
                    "from_rank": None,
                    "to_rank": now_rank,
                    "lookback": lookback,
                })
            continue
        delta = then_rank - now_rank
        if abs(delta) >= 2:
            moves.append({
                "player": name,
                "direction": "up" if delta > 0 else "down",
                "from_rank": then_rank,
                "to_rank": now_rank,
                "lookback": lookback,
            })

    moves.sort(key=lambda m: -abs((m["from_rank"] or 99) - m["to_rank"]))
    return moves[:4]


def _compute_returns(game_log, min_absence=2):
    """#2 — A regular who missed `min_absence`+ straight games and is back in
    tonight's lineup. Real roster data only."""
    if len(game_log) < min_absence + 1:
        return []

    tonight = game_log[-1]["present"]
    prior = game_log[:-1]
    if not prior:
        return []

    returns = []
    for player in tonight:
        # Count consecutive games immediately before tonight that they missed.
        absent_run = 0
        for entry in reversed(prior):
            if player in entry["present"]:
                break
            absent_run += 1
        # Only count as a "return" if they'd played at some point before that.
        played_before = any(player in e["present"] for e in prior)
        if played_before and absent_run >= min_absence:
            returns.append({"player": player, "games_missed": absent_run})

    returns.sort(key=lambda r: -r["games_missed"])
    return returns[:4]


def _compute_rarities(game_log):
    """#5 — Genuinely unusual events relative to this season's own baseline:
    firsts and season-highs/lows. All derived, nothing invented."""
    if not game_log:
        return []

    tonight = game_log[-1]
    prior = game_log[:-1]
    rarities = []

    # First goal of the season for a player
    prior_scorers = set()
    for e in prior:
        prior_scorers |= set(e["scorers"].keys())
    for scorer in tonight["scorers"]:
        if scorer not in prior_scorers:
            rarities.append({
                "kind": "first_goal",
                "detail": f"{scorer} scored their first goal of the season tonight.",
            })

    # Multi-goal game (season-relative notability)
    for scorer, count in tonight["scorers"].items():
        if count >= 3:
            rarities.append({
                "kind": "hat_trick",
                "detail": f"{scorer} scored {count} goals in tonight's game.",
            })
        elif count == 2:
            rarities.append({
                "kind": "multi_goal",
                "detail": f"{scorer} scored twice tonight.",
            })

    if prior:
        prior_goals = [e["goals_for"] for e in prior]

        # Season-high offensive output
        if tonight["goals_for"] > max(prior_goals):
            rarities.append({
                "kind": "season_high_goals",
                "detail": (
                    f"Tonight's {tonight['goals_for']} goals is the team's highest "
                    f"output of the season so far (previous best: {max(prior_goals)})."
                ),
            })

        # Shutout thrown by our goalie is handled elsewhere; note scoreless nights
        if tonight["goals_for"] == 0 and min(prior_goals) > 0:
            rarities.append({
                "kind": "first_scoreless",
                "detail": "Tonight was the team's first scoreless game of the season.",
            })

        # Season-high penalty night
        prior_pen_counts = [len(e["penalty_players"]) for e in prior]
        tonight_pens = len(tonight["penalty_players"])
        if tonight_pens > 0 and tonight_pens > max(prior_pen_counts):
            rarities.append({
                "kind": "season_high_penalties",
                "detail": (
                    f"Tonight's {tonight_pens} penalties is the team's most in a "
                    f"single game this season (previous most: {max(prior_pen_counts)})."
                ),
            })

        # First win / first loss of the season
        prior_results = [e["result"] for e in prior if e.get("result")]
        if tonight.get("result") == "win" and "win" not in prior_results:
            rarities.append({
                "kind": "first_win",
                "detail": "This was the team's first win of the season.",
            })
        if tonight.get("result") == "loss" and "loss" not in prior_results:
            rarities.append({
                "kind": "first_loss",
                "detail": "This was the team's first loss of the season.",
            })

    return rarities[:6]


def compute_recent_form(schedule, up_to_game_id, window=5):
    """Real win/loss form over the last `window` played games this season,
    up to and including the current game. Used only to nudge the host dynamic
    dial (Gord's edge / Casey's shine) — never to invent storylines.

    Mirrors compute_season_stats' approach: tries real game data for every
    season game up to and including tonight (not gated on the episode_generated
    flag, since that only tracks whether a *podcast episode* was produced, not
    whether the game itself has real results available)."""
    all_games = sorted(schedule["games"], key=lambda g: g["starts_at"])
    current = next((g for g in all_games if g["game_id"] == up_to_game_id), None)
    if current is None:
        return None
    season = current.get("season")

    season_games = [
        g for g in all_games
        if g.get("season") == season and g["starts_at"] <= current["starts_at"]
    ]

    results = []
    for g in season_games:
        try:
            s = get_game_stats(g["game_id"])
            results.append(s["result"])
        except Exception:
            continue

    recent = results[-window:]
    if len(recent) < window:
        return {"window": recent, "signal": "neutral"}

    wins = recent.count("win")
    losses = recent.count("loss")
    if wins >= 4:
        signal = "hot"
    elif losses >= 4:
        signal = "cold"
    else:
        signal = "neutral"

    return {"window": recent, "signal": signal}


def format_recent_form(recent_form):
    """Returns an empty string when form is neutral, so the prompt simply
    omits this section rather than forcing a dial-shift note every episode."""
    if not recent_form or recent_form["signal"] == "neutral":
        return ""

    record = ", ".join(r.upper() for r in recent_form["window"])

    if recent_form["signal"] == "hot":
        note = (
            f"Recent form is hot (real results, last {len(recent_form['window'])}: {record}). "
            "Gord's edge can ease slightly and Casey's optimism can feel a touch more "
            "validated than usual — but only if tonight's game gives a natural opening for it. "
            "Do not force a dial-shift line in if it doesn't fit."
        )
    else:
        note = (
            f"Recent form is cold (real results, last {len(recent_form['window'])}: {record}). "
            "Gord's edge can sharpen slightly and Casey's optimism can strain a bit more than "
            "usual — but only if tonight's game gives a natural opening for it. Do not force a "
            "dial-shift line in if it doesn't fit."
        )

    return "## Recent Form (Host Dynamic)\n" + note + "\n"


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

    if season_stats.get("rarities"):
        lines.append("**Rare / first-time events tonight (season-relative):**")
        for r in season_stats["rarities"]:
            lines.append(f"- {r['detail']}")
        lines.append("")

    if season_stats.get("trajectories"):
        lines.append("**Movement in the productivity order (vs. a few games ago):**")
        for m in season_stats["trajectories"]:
            if m["direction"] == "new":
                lines.append(
                    f"- {m['player']} has appeared on the scoresheet for the first time "
                    f"in this stretch, now sitting {m['to_rank']}th"
                )
            else:
                verb = "climbed" if m["direction"] == "up" else "slid"
                lines.append(
                    f"- {m['player']} has {verb} from {m['from_rank']}th to "
                    f"{m['to_rank']}th over the last {m['lookback']} games"
                )
        lines.append("")

    if season_stats.get("returns"):
        lines.append("**Back in the lineup tonight:**")
        for r in season_stats["returns"]:
            lines.append(
                f"- {r['player']} returned after missing {r['games_missed']} game(s)"
            )
        lines.append("")

    tw = season_stats.get("two_way") or {}
    if tw:
        lines.append("**The other side of the game this season (real, unaggregated by opinion):**")

        if tw.get("goalies"):
            for g in tw["goalies"]:
                lines.append(
                    f"- {g['name']} in goal: {g['games']} game(s), {g['shots_faced']} shots "
                    f"faced ({g['avg_shots_faced']}/game), {g['goals_against']} goals against"
                )

        if tw.get("by_period"):
            for p in tw["by_period"]:
                lines.append(
                    f"- {p['period']}: scored {p['goals_us']}, allowed {p['goals_them']}; "
                    f"shots {p['shots_us']} for, {p['shots_them']} against"
                )

        if tw.get("discipline"):
            d = tw["discipline"]
            base = f"- Penalties: {d['total']} total, {d['per_game']}/game"
            if "recent_per_game" in d:
                base += (
                    f" (earlier half {d['earlier_per_game']}/game, "
                    f"recent half {d['recent_per_game']}/game)"
                )
            lines.append(base)

        if tw.get("leads"):
            l = tw["leads"]
            lines.append(
                f"- Led at some point in {l['games_led_at_some_point']} game(s); "
                f"won {l['of_those_won']} of those"
            )

        if tw.get("shot_result_mismatch"):
            m = tw["shot_result_mismatch"]
            if m["outshot_opponent_but_lost"]:
                lines.append(
                    f"- Outshot the opponent and still lost: "
                    f"{m['outshot_opponent_but_lost']} game(s)"
                )
            if m["were_outshot_but_won"]:
                lines.append(
                    f"- Were outshot and won anyway: {m['were_outshot_but_won']} game(s)"
                )

        lines.append("")

    lines.append(
        "These are the show's richest creative territory. Per-game facts are a closed "
        "set, but season-long patterns compound — a rank that *moved*, a streak that "
        "*broke*, a first that only counts as a first because of everything before it. "
        "Build the storyline out of change over time, not a recitation of current "
        "standings. Reward the listener who has heard the earlier episodes.\n"
    )

    lines.append(
        "If none of the above has anything notable for tonight's game specifically, "
        "it's fine to skip season storylines and lean on last episode's carried-forward "
        "storyline instead — don't force a stat in that isn't actually interesting."
    )

    return "\n".join(lines)
