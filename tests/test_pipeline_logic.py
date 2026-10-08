"""
Tests for the script-generation logic (no network, no API key needed).

Run from the repo root:
    python3 -m unittest discover -s tests -v

These cover the parts that decide what the model is told and what gets
remembered: config loading, recent-episode memory, lens selection, opponent
scouting, the season outlook, and the prediction/theory log.
"""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import config_loader  # noqa: E402
import episode_memory  # noqa: E402
import look_ahead  # noqa: E402
import lenses  # noqa: E402
import opponent_stats  # noqa: E402
import relationship_log as rl  # noqa: E402
import season_stats  # noqa: E402


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def make_schedule(n=5, generated_through=None, season="S1"):
    """n games, one per day. Games with index < generated_through are marked generated."""
    games = []
    for i in range(n):
        games.append({
            "game_id": f"g{i + 1}",
            "starts_at": f"2026-10-{i + 1:02d}T18:00:00+00:00",
            "opponent": f"Team{i + 1}",
            "home_or_away": "home" if i % 2 == 0 else "away",
            "season": season,
            "episode_generated": generated_through is not None and i < generated_through,
        })
    return {"season": season, "games": games}


def game_stats(result="loss", us=1, them=4, opponent="X", present=(), goals=()):
    return {
        "result": result, "our_score": us, "opp_score": them, "opponent": opponent,
        "players_present": list(present), "our_goals": list(goals),
    }


# ---------------------------------------------------------------------------
# config_loader
# ---------------------------------------------------------------------------

class ConfigLoaderTests(unittest.TestCase):
    def test_fills_placeholders(self):
        self.assertEqual(config_loader.render_template("a {{x}} b {{ y }}", {"x": 1, "y": "two"}), "a 1 b two")

    def test_missing_placeholder_value_raises(self):
        with self.assertRaises(ValueError) as cm:
            config_loader.render_template("hello {{name}}", {})
        self.assertIn("name", str(cm.exception))

    def test_unused_values_are_ignored(self):
        self.assertEqual(config_loader.render_template("plain", {"x": 1}), "plain")

    def test_comments_are_stripped_and_not_scanned_for_placeholders(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "t.md").write_text("<!-- note about {{ghost}} -->\n\nBody {{x}}\n")
            self.assertEqual(config_loader.load_rendered("t.md", {"x": "ok"}, config_dir=d), "Body ok")

    def test_missing_and_empty_files_raise(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                config_loader.load_config("nope.md", d)
            (Path(d) / "empty.md").write_text("<!-- only a comment -->")
            with self.assertRaises(ValueError):
                config_loader.load_config("empty.md", d)

    def test_real_config_files_all_load(self):
        for name in ("hosts.md", "core-rules.md", "content-bank.md", "players.md",
                     "script-construction.md", "episode-brief.md", "lenses.md"):
            self.assertTrue(config_loader.load_config(name))

    def test_episode_brief_renders_with_expected_placeholders(self):
        text = config_loader.load_rendered(
            "episode-brief.md", {"game_type": "NORMAL", "featured_lenses": "LENSES-HERE"}
        )
        self.assertIn("NORMAL", text)
        self.assertIn("LENSES-HERE", text)
        self.assertNotRegex(text, r"\{\{\w+\}\}")


# ---------------------------------------------------------------------------
# episode_memory
# ---------------------------------------------------------------------------

class EpisodeMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write_episode(self, game_id, script="CASEY: hi", summary=None):
        d = self.data / "episodes" / game_id
        d.mkdir(parents=True)
        (d / "script.txt").write_text(script)
        if summary is not None:
            (d / "summary.json").write_text(json.dumps(summary))

    def test_returns_last_n_before_current_oldest_first(self):
        sched = make_schedule(6, generated_through=5)
        for i in range(1, 6):
            self.write_episode(f"g{i}", f"script {i}")
        got = episode_memory.load_recent_scripts(sched, "g6", "S1", count=3, data_dir=self.data)
        self.assertEqual([e["game_id"] for e in got], ["g3", "g4", "g5"])

    def test_never_includes_current_or_later_games(self):
        sched = make_schedule(5, generated_through=5)
        for i in range(1, 6):
            self.write_episode(f"g{i}")
        got = episode_memory.load_recent_scripts(sched, "g3", "S1", data_dir=self.data)
        self.assertEqual([e["game_id"] for e in got], ["g1", "g2"])

    def test_other_seasons_and_ungenerated_games_are_skipped(self):
        sched = make_schedule(4, generated_through=4)
        sched["games"][1]["season"] = "OLD"
        sched["games"][2]["episode_generated"] = False
        for i in range(1, 5):
            self.write_episode(f"g{i}")
        got = episode_memory.load_recent_scripts(sched, "g4", "S1", data_dir=self.data)
        self.assertEqual([e["game_id"] for e in got], ["g1"])

    def test_fails_safe(self):
        sched = make_schedule(3, generated_through=3)
        self.write_episode("g1")
        self.assertEqual(episode_memory.load_recent_scripts(sched, "g3", None, data_dir=self.data), [])
        self.assertEqual(episode_memory.load_recent_scripts(sched, "missing", "S1", data_dir=self.data), [])

    def test_missing_script_file_is_skipped(self):
        sched = make_schedule(3, generated_through=3)
        self.write_episode("g2")  # g1 has no script file
        got = episode_memory.load_recent_scripts(sched, "g3", "S1", data_dir=self.data)
        self.assertEqual([e["game_id"] for e in got], ["g2"])

    def test_format(self):
        self.assertEqual(episode_memory.format_recent_scripts([]), "")
        text = episode_memory.format_recent_scripts([
            {"opponent": "Aces", "date": "2026-10-01", "result_summary": "LOSS 1-4", "script": "CASEY: hello"}
        ])
        self.assertIn("avoid repeating", text)
        self.assertIn("Aces", text)
        self.assertIn("CASEY: hello", text)


# ---------------------------------------------------------------------------
# opponent scouting
# ---------------------------------------------------------------------------

def team_of(points):
    return [{"name": f"P{i}", "points": p, "goals": p // 2, "assists": p - p // 2, "gp": 5, "penalties": 0}
            for i, p in enumerate(points, 1)]


class StandoutTests(unittest.TestCase):
    def names(self, points):
        return [p["name"] for p in opponent_stats.find_standouts(team_of(points))]

    def test_one_clear_star(self):
        self.assertEqual(self.names([10, 5, 4, 3, 2]), ["P1"])

    def test_two_stars(self):
        self.assertEqual(self.names([10, 9, 4, 3]), ["P1", "P2"])

    def test_three_stars(self):
        self.assertEqual(self.names([8, 8, 8, 2, 1]), ["P1", "P2", "P3"])

    def test_flat_scoring_has_no_standouts(self):
        self.assertEqual(self.names([5, 5, 4, 4, 4, 3]), [])

    def test_below_minimum_points(self):
        self.assertEqual(self.names([2, 0, 0]), [])

    def test_four_way_tie_is_not_a_standout_group(self):
        self.assertEqual(self.names([9, 9, 9, 9, 2]), [])

    def test_no_scorers(self):
        self.assertEqual(self.names([0, 0]), [])

    def test_text_names_only_the_standouts(self):
        rec = {"w": 2, "l": 1, "t": 0, "gp": 3, "gf": 9, "ga": 5}
        so = opponent_stats.find_standouts(team_of([10, 5, 4]))
        text = opponent_stats._scouting_text("Aces", rec, so, "preview")
        self.assertIn("P1", text)
        self.assertNotIn("P2", text)
        self.assertIn("players to watch", text)


# ---------------------------------------------------------------------------
# season stats + look-ahead
# ---------------------------------------------------------------------------

class TeamRecordTests(unittest.TestCase):
    def test_record_split_and_results(self):
        log = [
            {"result": "win", "our_score": 4, "opp_score": 2, "home_or_away": "home"},
            {"result": "loss", "our_score": 1, "opp_score": 3, "home_or_away": "away"},
            {"result": "tie", "our_score": 2, "opp_score": 2, "home_or_away": "away"},
            {"result": None, "our_score": None, "opp_score": None, "home_or_away": "home"},
        ]
        total, split, results = season_stats._compute_team_record(log)
        self.assertEqual((total["gp"], total["w"], total["l"], total["t"], total["gf"], total["ga"]), (3, 1, 1, 1, 7, 7))
        self.assertEqual(split["home"]["gp"], 1)
        self.assertEqual(split["away"]["gp"], 2)
        self.assertEqual(results, ["win", "loss", "tie"])


class LookAheadTests(unittest.TestCase):
    def stats(self, results):
        w, l, t = results.count("win"), results.count("loss"), results.count("tie")
        return {
            "games_counted": len(results),
            "team_record": {"gp": len(results), "w": w, "l": l, "t": t, "gf": 2 * len(results), "ga": 3 * len(results)},
            "home_road": {"home": {"gp": 1, "w": 0, "l": 1, "t": 0, "gf": 1, "ga": 2},
                          "away": {"gp": 1, "w": 1, "l": 0, "t": 0, "gf": 3, "ga": 2}},
            "results": results,
            "points_leaders": [("Ann", {"points": 4, "goals": 2, "assists": 2})],
        }

    def test_schedule_counts_and_pace(self):
        sched = make_schedule(10)
        la = look_ahead.compute_look_ahead(sched, "g4", self.stats(["win", "loss", "loss", "loss"]))
        self.assertEqual((la["season_total_games"], la["games_played"], la["games_remaining"]), (10, 4, 6))
        self.assertEqual(la["pace"]["goals_for"], round(8 * 10 / 4))
        self.assertEqual(la["pace"]["top_scorers"][0]["points_pace"], 10)
        self.assertEqual(len(la["upcoming"]), 3)

    def test_rematches_counted(self):
        sched = make_schedule(6)
        sched["games"][4]["opponent"] = "Team1"  # we already faced Team1 in g1
        la = look_ahead.compute_look_ahead(sched, "g3", self.stats(["win", "loss", "loss"]))
        self.assertEqual(la["rematches_remaining"], {"Team1": 1})

    def test_no_pace_before_two_games(self):
        sched = make_schedule(5)
        la = look_ahead.compute_look_ahead(sched, "g1", self.stats(["loss"]))
        self.assertIsNone(la["pace"])

    def test_streak_wording(self):
        sched = make_schedule(5)
        for kind, word in (("win", "wins"), ("loss", "losses"), ("tie", "ties")):
            la = look_ahead.compute_look_ahead(sched, "g3", self.stats([kind] * 3))
            self.assertIn(f"3 straight {word}", look_ahead.format_look_ahead(la))

    def test_unknown_game_and_empty_format(self):
        self.assertIsNone(look_ahead.compute_look_ahead(make_schedule(3), "nope", None))
        self.assertEqual(look_ahead.format_look_ahead(None), "")


# ---------------------------------------------------------------------------
# lenses
# ---------------------------------------------------------------------------

def rich_ctx(**over):
    ctx = {
        "has_next_game": True,
        "prior_meetings": [{"x": 1}],
        "pending_callbacks": [],
        "open_theories": [],
        "can_add_theory": True,
        "season_stats": {
            "games_counted": 5,
            "trajectories": [{"x": 1}], "top_assist_pairs": [("a", "b", 2)], "streaks": {"p": 3},
            "penalty_leaders": [("n", 2)], "returns": [{"x": 1}], "rarities": [{"detail": "x"}],
            "two_way": {
                "goalies": [{"x": 1}], "by_period": [{"x": 1}], "discipline": {"total": 4},
                "leads": {"games_led_at_some_point": 2},
                "shot_result_mismatch": {"outshot_opponent_but_lost": 1, "were_outshot_but_won": 0},
            },
        },
        "look_ahead": {
            "pace": {"x": 1}, "streak": {"kind": "loss", "length": 4}, "record": {"gp": 5},
            "next_opponent_record": {"gp": 3},
            "home_road": {"home": {"gp": 2}, "away": {"gp": 3}},
        },
    }
    ctx.update(over)
    return ctx


class LensTests(unittest.TestCase):
    def test_config_and_code_agree_on_lens_ids(self):
        self.assertEqual(set(lenses.load_lens_descriptions()), set(lenses.ELIGIBILITY))

    def test_data_gating(self):
        self.assertEqual(lenses.eligible_lenses({"season_stats": {"games_counted": 1}}), ["season_outlook"])
        self.assertNotIn("accountability", lenses.eligible_lenses(rich_ctx()))
        self.assertIn("accountability", lenses.eligible_lenses(rich_ctx(pending_callbacks=[{"id": "P1"}])))
        self.assertNotIn("theory_check", lenses.eligible_lenses(rich_ctx()))
        self.assertIn("theory_check", lenses.eligible_lenses(rich_ctx(open_theories=[{"id": "T1"}])))
        self.assertNotIn("new_theory", lenses.eligible_lenses(rich_ctx(can_add_theory=False)))
        self.assertNotIn("prediction", lenses.eligible_lenses(rich_ctx(has_next_game=False)))
        self.assertNotIn("rivalry", lenses.eligible_lenses(rich_ctx(prior_meetings=[])))

    def test_predictions_need_a_few_games(self):
        ctx = rich_ctx()
        ctx["season_stats"]["games_counted"] = 2
        self.assertNotIn("prediction", lenses.eligible_lenses(ctx))
        self.assertNotIn("new_theory", lenses.eligible_lenses(ctx))

    def test_pick_is_repeatable_and_varies_by_game(self):
        el = lenses.eligible_lenses(rich_ctx())
        self.assertEqual(lenses.pick_lenses(el, set(), "g1"), lenses.pick_lenses(el, set(), "g1"))
        picks = {tuple(lenses.pick_lenses(el, set(), f"g{i}")) for i in range(20)}
        self.assertGreater(len(picks), 5)

    def test_recently_used_lenses_are_avoided(self):
        el = lenses.eligible_lenses(rich_ctx())
        first = lenses.pick_lenses(el, set(), "gA")
        again = lenses.pick_lenses(el, set(first), "gA")
        self.assertFalse(set(first) & set(again))

    def test_accountability_is_forced(self):
        el = lenses.eligible_lenses(rich_ctx(pending_callbacks=[{"id": "P1"}]))
        for i in range(10):
            self.assertIn("accountability", lenses.pick_lenses(el, {"accountability"}, f"g{i}"))

    def test_at_most_one_priority_lens_and_it_is_not_recent(self):
        ctx = rich_ctx(open_theories=[{"id": "T1"}])
        el = lenses.eligible_lenses(ctx)
        for i in range(30):
            picked = lenses.pick_lenses(el, set(), f"g{i}")
            self.assertEqual(len(picked), 3)
            # priority lens is always present when eligible and not recent...
            self.assertTrue({"theory_check", "prediction"} & set(picked))
        # ...and not forced back in when it was just used
        picked = lenses.pick_lenses(el, {"theory_check", "prediction"}, "gZ")
        self.assertEqual(len(picked), 3)

    def test_recent_lenses_used_reads_last_n_summaries(self):
        past = [{"lenses": ["a"]}, {"lenses": ["b"]}, {"lenses": ["c"]}, {}]
        self.assertEqual(lenses.recent_lenses_used(past, 2), {"c"})

    def test_format_requires_descriptions(self):
        with self.assertRaises(KeyError):
            lenses.format_featured_lenses(["no_such_lens"], {"a": "b"})
        text = lenses.format_featured_lenses(["trajectory"], lenses.load_lens_descriptions())
        self.assertIn("trajectory", text)


# ---------------------------------------------------------------------------
# relationship log: tags
# ---------------------------------------------------------------------------

class TagParsingTests(unittest.TestCase):
    CTX = {"date": "2026-10-02", "opponent": "Aces"}

    def parse(self, tags):
        return rl.extract_relationship_tags("CASEY: hi\n\nGORD: yo\n" + tags, "g1", self.CTX)

    def test_all_tag_types_parse_and_script_is_clean(self):
        script, preds, moments, theories, updates = self.parse(
            "PREDICTION: casey | next_game_result | win\n"
            "PREDICTION: gord | next_game_goals_for | 4\n"
            "PREDICTION: gord | next_game_goals_against | 2\n"
            "PREDICTION: casey | next_game_player_point | Ann Lee\n"
            "PREDICTION: casey | next_game_player_goal | Ann Lee\n"
            "PREDICTION: gord | team_result_streak | losses | 2\n"
            "PREDICTION: gord | player_goal_count | Ann Lee | 5\n"
            "THEORY: gord | They win when the top line connects.\n"
            "THEORY_UPDATE: t1 | Complicates | One game isn't a trend.\n"
            "MOMENT: casey | Casey flagged the shots | NORMAL\n"
        )
        self.assertEqual(script, "CASEY: hi\n\nGORD: yo")
        self.assertEqual(len(preds), 7)
        self.assertEqual(len(moments), 1)
        self.assertEqual(theories[0]["thesis"], "They win when the top line connects.")
        self.assertEqual(theories[0]["opponent"], "Aces")
        self.assertEqual(updates, [{"id": "T1", "verdict": "complicates", "note": "One game isn't a trend."}])

    def test_malformed_tags_are_dropped_but_never_left_in_the_script(self):
        script, preds, moments, theories, updates = self.parse(
            "PREDICTION: casey | next_game_result | draw\n"
            "PREDICTION: nobody | next_game_result | win\n"
            "PREDICTION: casey | next_game_goals_for | lots\n"
            "PREDICTION: casey | made_up_type | x\n"
            "THEORY: someone | x\n"
            "THEORY_UPDATE: T1 | maybe | note\n"
            "THEORY_UPDATE: T1\n"
        )
        self.assertEqual(script, "CASEY: hi\n\nGORD: yo")
        self.assertEqual((preds, moments, theories, updates), ([], [], [], []))

    def test_theory_update_is_not_mistaken_for_theory(self):
        _, _, _, theories, updates = self.parse("THEORY_UPDATE: T2 | supports | yes\n")
        self.assertEqual(theories, [])
        self.assertEqual(len(updates), 1)

    def test_long_text_is_clipped(self):
        _, _, _, theories, _ = self.parse("THEORY: casey | " + "x " * 500 + "\n")
        self.assertLessEqual(len(theories[0]["thesis"]), rl.MAX_TEXT_CHARS)


# ---------------------------------------------------------------------------
# relationship log: resolution
# ---------------------------------------------------------------------------

def pred(ptype, target, game_id="g1", made_by="casey", **extra):
    base = {"id": "P1", "game_id": game_id, "made_by": made_by, "checkable_type": ptype,
            "checkable_target": target, "resolved": False, "outcome": None, "surfaced": False,
            "date": "2026-10-01", "opponent": "Team1"}
    base.update(extra)
    return base


def new_log(*preds):
    log = {"season": "S1", "predictions": list(preds), "notable_moments": [], "theories": []}
    return rl._migrate(log)


class ResolutionTests(unittest.TestCase):
    def test_next_game_prediction_resolves_at_the_very_next_episode(self):
        # g2 is the game just played; its episode is NOT marked generated yet.
        sched = make_schedule(3, generated_through=1)
        log = new_log(pred("next_game_result", {"result": "win"}))
        got = rl.resolve_predictions(log, sched, lambda gid: game_stats("loss", 1, 4, "Team2"), lambda *a: None, "g2")
        self.assertEqual(len(got), 1)
        self.assertEqual(log["predictions"][0]["outcome"], "missed")
        self.assertIn("LOSS 1-4", log["predictions"][0]["outcome_detail"])

    def test_confirmed_prediction(self):
        sched = make_schedule(3, generated_through=1)
        log = new_log(pred("next_game_goals_for", {"threshold": 3}))
        rl.resolve_predictions(log, sched, lambda gid: game_stats("win", 5, 1), lambda *a: None, "g2")
        self.assertEqual(log["predictions"][0]["outcome"], "confirmed")

    def test_goals_against_is_a_ceiling(self):
        sched = make_schedule(3, generated_through=1)
        log = new_log(pred("next_game_goals_against", {"threshold": 2}))
        rl.resolve_predictions(log, sched, lambda gid: game_stats("loss", 1, 3), lambda *a: None, "g2")
        self.assertEqual(log["predictions"][0]["outcome"], "missed")

    def test_not_resolved_against_its_own_episode(self):
        sched = make_schedule(3, generated_through=1)
        log = new_log(pred("next_game_result", {"result": "win"}, game_id="g2"))
        got = rl.resolve_predictions(log, sched, lambda gid: game_stats(), lambda *a: None, "g2")
        self.assertEqual(got, [])
        self.assertFalse(log["predictions"][0]["resolved"])

    def test_regenerating_an_old_game_cannot_see_the_future(self):
        sched = make_schedule(5, generated_through=5)
        # made at g1; we are re-running g1 itself, with later games all generated
        log = new_log(pred("next_game_result", {"result": "win"}))
        got = rl.resolve_predictions(log, sched, lambda gid: game_stats("win", 3, 1), lambda *a: None, "g1")
        self.assertEqual(got, [])
        # and a 3-game streak made at g1 can't resolve when only g2 is "played"
        log = new_log(pred("team_result_streak", {"metric": "wins", "window_games": 3}))
        got = rl.resolve_predictions(log, sched, lambda gid: game_stats("win"), lambda *a: None, "g2")
        self.assertEqual(got, [])

    def test_streak_resolves_once_enough_games_are_played(self):
        sched = make_schedule(5, generated_through=2)
        log = new_log(pred("team_result_streak", {"metric": "losses", "window_games": 2}))
        got = rl.resolve_predictions(log, sched, lambda gid: game_stats("loss"), lambda *a: None, "g3")
        self.assertEqual(len(got), 1)
        self.assertEqual(log["predictions"][0]["outcome"], "confirmed")

    def test_player_prediction_is_void_if_the_player_did_not_play(self):
        sched = make_schedule(3, generated_through=1)
        log = new_log(pred("next_game_player_point", {"player": "Ann Lee"}))
        got = rl.resolve_predictions(log, sched, lambda gid: game_stats(present=["Bob"]), lambda *a: None, "g2")
        self.assertEqual(got, [])
        self.assertEqual(log["predictions"][0]["outcome"], "void")
        self.assertEqual(rl.pending_callbacks(log), [])

    def test_player_point_and_goal_checks(self):
        goals = [{"scorer": "Bob", "assists": [{"name": "Ann Lee"}]}]
        sched = make_schedule(3, generated_through=1)
        log = new_log(pred("next_game_player_point", {"player": "Ann Lee"}),
                      pred("next_game_player_goal", {"player": "Ann Lee"}, id="P2"))
        rl.resolve_predictions(log, sched, lambda gid: game_stats(present=["Ann Lee", "Bob"], goals=goals),
                               lambda *a: None, "g2")
        self.assertEqual(log["predictions"][0]["outcome"], "confirmed")  # assist counts as a point
        self.assertEqual(log["predictions"][1]["outcome"], "missed")     # but she didn't score

    def test_season_type_uses_cached_season_stats(self):
        calls = []

        def season_fn(schedule, gid):
            calls.append(gid)
            return {"points_leaders": [("Ann Lee", {"goals": 6, "assists": 1, "points": 7})],
                    "streaks": {}, "penalty_leaders": []}

        sched = make_schedule(4, generated_through=1)
        log = new_log(pred("player_goal_count", {"player": "Ann Lee", "threshold": 5}),
                      pred("player_goal_count", {"player": "Ann Lee", "threshold": 9}, id="P2"))
        rl.resolve_predictions(log, sched, lambda gid: game_stats(), season_fn, "g3")
        self.assertEqual([p["outcome"] for p in log["predictions"]], ["confirmed", "missed"])
        self.assertEqual(len(calls), 1)


# ---------------------------------------------------------------------------
# relationship log: callback queue, theories, migration, prompt
# ---------------------------------------------------------------------------

class CallbackQueueTests(unittest.TestCase):
    def settled(self, pid, surfaced=False, outcome="missed"):
        return pred("next_game_result", {"result": "win"}, id=pid, resolved=True, outcome=outcome,
                    outcome_detail="LOSS 1-4 vs X", surfaced=surfaced)

    def test_settled_predictions_stay_queued_until_surfaced(self):
        log = new_log(self.settled("P1"))
        self.assertEqual(len(rl.pending_callbacks(log)), 1)
        self.assertEqual(len(rl.pending_callbacks(log)), 1)  # still there: nothing consumed it
        rl.mark_surfaced(log, ["P1"])
        self.assertEqual(rl.pending_callbacks(log), [])

    def test_capped_per_episode_oldest_first(self):
        log = new_log(*[self.settled(f"P{i}") for i in range(1, 6)])
        self.assertEqual([p["id"] for p in rl.pending_callbacks(log)], ["P1", "P2", "P3"])

    def test_add_predictions_assigns_unique_ids(self):
        log = new_log(self.settled("P1"))
        rl.add_predictions(log, [pred("next_game_result", {"result": "win"}), pred("next_game_result", {"result": "loss"})])
        self.assertEqual([p["id"] for p in log["predictions"]], ["P1", "P2", "P3"])

    def test_prompt_section_mentions_who_what_and_result(self):
        log = new_log(self.settled("P1"))
        text = rl.format_relationship_context(rl.pending_callbacks(log), [], [])
        self.assertIn("Casey predicted", text)
        self.assertIn("episode vs Team1 (2026-10-01)", text)
        self.assertIn("win its next game", text)
        self.assertIn("didn't pan out", text)
        self.assertIn("settle these on air", text)
        self.assertEqual(rl.format_relationship_context([], [], []), "")


class TheoryTests(unittest.TestCase):
    def theory(self, thesis="They win on the road."):
        return {"game_id": "g1", "made_by": "gord", "thesis": thesis, "status": "open", "history": [],
                "date": "2026-10-01", "opponent": "Team1"}

    def test_cap_on_open_theories(self):
        log = new_log()
        added, _ = rl.apply_theory_tags(log, [self.theory(f"t{i}") for i in range(5)], [], "g2")
        self.assertEqual(added, rl.MAX_OPEN_THEORIES)
        self.assertFalse(rl.can_add_theory(log))
        self.assertEqual([t["id"] for t in log["theories"]], ["T1", "T2", "T3"])

    def test_update_records_history_and_dropping_frees_a_slot(self):
        log = new_log()
        rl.apply_theory_tags(log, [self.theory(f"t{i}") for i in range(3)], [], "g2")
        added, updated = rl.apply_theory_tags(
            log, [self.theory("fresh")],
            [{"id": "T1", "verdict": "dropped", "note": "Dead."}], "g3")
        self.assertEqual((added, updated), (1, 1))
        t1 = log["theories"][0]
        self.assertEqual(t1["status"], "dropped")
        self.assertEqual(t1["history"][0]["verdict"], "dropped")
        self.assertEqual(log["theories"][-1]["id"], "T4")  # ids are never reused

    def test_unknown_or_closed_theory_updates_are_ignored(self):
        log = new_log()
        rl.apply_theory_tags(log, [self.theory()], [], "g2")
        _, updated = rl.apply_theory_tags(log, [], [{"id": "T9", "verdict": "supports", "note": "x"}], "g3")
        self.assertEqual(updated, 0)

    def test_open_theories_appear_in_prompt_with_last_check(self):
        log = new_log()
        rl.apply_theory_tags(log, [self.theory()], [{"id": "T1", "verdict": "supports", "note": "x"}], "g2")
        rl.apply_theory_tags(log, [], [{"id": "T1", "verdict": "complicates", "note": "Lost at home."}], "g3")
        text = rl.format_relationship_context([], [], rl.open_theories(log))
        self.assertIn("[T1] Gord", text)
        self.assertIn("complicates", text)
        self.assertIn("THEORY_UPDATE", text)


class MigrationAndMomentTests(unittest.TestCase):
    def test_legacy_log_is_migrated_without_dredging_up_stale_callbacks(self):
        legacy = {"season": "S1", "predictions": [
            {"game_id": "g1", "made_by": "casey", "checkable_type": "team_result_streak",
             "checkable_target": {"metric": "wins", "window_games": 1},
             "resolved": True, "outcome": "missed", "outcome_detail": "LOSS"},
            {"game_id": "g2", "made_by": "gord", "checkable_type": "penalty_trend",
             "checkable_target": {"player": "A", "threshold": 3}, "resolved": False, "outcome": None},
        ], "notable_moments": []}
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "log.json"
            path.write_text(json.dumps(legacy))
            log = rl.load_relationship_log("S1", path=path)
        self.assertEqual(log["theories"], [])
        self.assertEqual([p["id"] for p in log["predictions"]], ["P1", "P2"])
        self.assertTrue(log["predictions"][0]["surfaced"])    # already-resolved: treated as handled
        self.assertFalse(log["predictions"][1]["surfaced"])
        self.assertEqual(rl.pending_callbacks(log), [])

    def test_new_season_starts_empty(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "log.json"
            rl.save_relationship_log(new_log(pred("next_game_result", {"result": "win"})), path=path)
            fresh = rl.load_relationship_log("S2", path=path)
        self.assertEqual((fresh["predictions"], fresh["theories"]), ([], []))

    def test_moment_matches_are_capped_to_most_recent(self):
        log = new_log()
        log["notable_moments"] = [
            {"game_id": f"g{i}", "who": "casey", "summary": f"m{i}", "match_keys": {"score_margin_bucket": "NORMAL"}}
            for i in range(1, 8)
        ]
        got = rl.match_notable_moments(log, "Anyone", "NORMAL", "g9")
        self.assertEqual([m["summary"] for m in got], ["m5", "m6", "m7"])

    def test_describe_prediction_covers_every_type(self):
        samples = {
            "team_result_streak": {"metric": "wins", "window_games": 2},
            "player_goal_count": {"player": "A", "threshold": 3},
            "player_points_streak": {"player": "A", "threshold": 3},
            "penalty_trend": {"player": "A", "threshold": 3},
            "next_game_result": {"result": "win"},
            "next_game_goals_for": {"threshold": 3},
            "next_game_goals_against": {"threshold": 2},
            "next_game_player_point": {"player": "A"},
            "next_game_player_goal": {"player": "A"},
        }
        self.assertEqual(set(samples), rl.CHECKABLE_TYPES)
        for t, target in samples.items():
            self.assertNotEqual(rl.describe_prediction(pred(t, target)), "something checkable", t)


# ---------------------------------------------------------------------------
# prompt assembly
# ---------------------------------------------------------------------------

class PromptAssemblyTests(unittest.TestCase):
    def test_prompt_builds_with_no_leftovers(self):
        try:
            import generate_script as gs
        except ImportError as e:  # anthropic / requests not installed
            self.skipTest(f"generate_script imports unavailable: {e}")

        cfg = ROOT / "config"
        prompt = gs.build_prompt(
            stats={"game_id": "g", "opponent": "X"}, past_episodes=[],
            hosts=(cfg / "hosts.md").read_text(), core_rules=(cfg / "core-rules.md").read_text(),
            content_bank=(cfg / "content-bank.md").read_text(), players=(cfg / "players.md").read_text(),
            script_construction=(cfg / "script-construction.md").read_text(),
            next_game_context="## Next Game Preview\nNext game: vs Y.\n", game_type="NORMAL",
            season_stats_context="## Season Stats\nx", relationship_context="", recent_form_context="",
            guest_coach_context="", milestone_context="", featured_lenses="LENS-LIST",
        )
        self.assertNotRegex(prompt, r"\{\{\w+\}\}")
        self.assertIn("LENS-LIST", prompt)
        for needle in ("welcome to the show by name", "THEORY_UPDATE", "next_game_result", "Use ONLY the exact format below"):
            self.assertIn(needle, prompt)
        for stale in ("gord_corner", "game_recap", "player_spotlight", "season_storylines",
                      "next_game_preview", "cold_open", "rivalry_alert", "active_special_segments",
                      "Script Variety Guidelines"):
            self.assertNotIn(stale, prompt, f"stale reference: {stale}")


if __name__ == "__main__":
    unittest.main()
