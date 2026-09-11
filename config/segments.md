# Episode Segments

This file controls the segment structure for each episode.
Edit this file to add, remove, reorder, or introduce special segments.

---

## Standard Segments (run every episode)

- cold_open
- game_recap
- player_spotlight
- gord_corner
- season_storylines
- closing_take
- next_game_preview

`next_game_preview` closes the episode with the date, time, and opponent for the
next scheduled game, pulled from `data/schedule.json`. If we've already played
that opponent this season, it also recaps the last meeting (final score, and
who scored for them) using real data from that game. If it's a first meeting,
it stays general — no invented opponent player details. Skipped automatically
if there's no game left on the schedule.

---

## Segment Structure by Game Type

The game is auto-classified from the score margin and overtime flag. Use the
type to flex the standard segments — same segment list, different emphasis:

- **BLOWOUT_WIN** (won by 4+): Keep `game_recap` brief — the score tells most
  of the story. Expand `player_spotlight` since a blowout usually means someone
  had a big game worth dwelling on. `gord_corner` should be short; he's got
  less to grumble about, though he can still find something.
- **BLOWOUT_LOSS** (lost by 4+): Keep `game_recap` brief and matter-of-fact —
  don't dwell on every goal against. Expand `gord_corner` instead; this is
  where his frustration gets the most room. `player_spotlight` can shrink or
  focus on the one bright spot rather than a full breakdown.
- **CLOSE_OR_OVERTIME** (decided by 1 goal, or went to OT): Expand `game_recap`
  — this is the version of the show where the play-by-play tension matters
  most. Keep every segment at normal length; don't rush this one.
- **SHUTOUT_WIN** (opponent scored 0): `player_spotlight` should lead with the
  goalie's performance before any skater.
- **SHUTOUT_LOSS** (we scored 0): `game_recap` stays brief; `gord_corner` gets
  extra room, and there's no offensive standout to spotlight — keep
  `player_spotlight` short, focused on effort rather than results.
- **NORMAL**: Standard length and structure for all segments, no adjustment.

---

## Special Segments (activate per-episode by adding to `active_special_segments` below)

### guest_coach
**Currently disabled** — set `ENABLED = True` at the top of `scripts/guest_coach.py`
to turn it back on. The code and cadence tracking are untouched and ready to
go; while disabled, `generate_script.py` skips this feature entirely and
doesn't advance the cadence log, so it picks back up cleanly whenever it's
re-enabled.

A one-off guest coach character joins for one segment to offer tactical advice,
replacing `gord_corner` for that episode. When enabled, this is fully
automatic — no manual config edit needed. `scripts/guest_coach.py` tracks a
randomized 3-6 episode gap and triggers this segment on its own; when it
fires, the model invents a brand new character on the spot (distinct from
Casey and Gord, bound by the same no-invented-facts rules) and the result
gets logged to `data/guest_coach_log.json` and mirrored into that game's
`special_guest` field in `data/schedule.json` afterward, for reference only.

### rivalry_alert
Use when the opponent is a team the Village People have a notable record against.
Requires: at least 2 prior games against this opponent in the season log.
Slot: inserted before `closing_take`.

---

## Milestones (organic, not a segment)

This is NOT a special segment and doesn't get its own slot — it's real material
that should surface naturally inside whatever segment it fits, the same way
Season Stats or Recurring Bits do. Fully automatic; no manual config edit
needed. `scripts/milestones.py` detects two kinds of real, data-only events
each episode:
- A player becoming the sole new season leader in goals, assists, points, or
  penalties, but only when they recorded that stat in tonight's game — and
  each category has its own 3-episode cooldown so a back-and-forth lead race
  doesn't get mentioned every episode.
- A player extending an active goal-scoring streak to 3+ consecutive games
  played.
Nothing is invented; both checks run purely on real per-game stats. When
something qualifies, it should be woven into game_recap, player_spotlight, or
season_storylines — whichever the moment genuinely calls for — conversationally,
not announced as its own segment. Results are logged to
`data/milestone_log.json` and mirrored into that game's `milestones` field in
`data/schedule.json` afterward, for reference only.

---

## Active Special Segments This Episode

active_special_segments: []

<!--
guest_coach is fully automatic (see its section above) — do NOT add it here.
milestone_watch is no longer a special segment at all — see "Milestones"
above; it's never added here.
rivalry_alert is still manual for now: to activate it for the next episode,
edit the list above, e.g.:
active_special_segments: [rivalry_alert]
Then add the required data to the game entry in data/schedule.json.
After the episode generates, clear this list.
-->
