# Episode Segments

This file controls the segment structure for each episode.
Edit this file to add, remove, reorder, or introduce special segments.

---

## Segment Bank

Full definitions and guidance for each of these live in `podcast-guidelines.md`'s
"Episode Structure" section — this is just the index.

**Anchors (always present):**
- `cold_open` — always first
- `season_storylines` — required every episode, position among the others is flexible
- `next_game_preview` — always last, now also carries the closing take (Casey's
  outlook + Gord's grumbling counterpoint)

**Flexible bank (pick and order per episode, based on what tonight's game
actually supports — not a fixed checklist):**
- `game_recap`
- `player_spotlight`
- `gord_corner`
- Any active special segment below (e.g. `rivalry_alert`)

`next_game_preview` pulls the date, time, and opponent for the next scheduled
game from `data/schedule.json`. If we've already played that opponent this
season, it also recaps the last meeting (final score, and who scored for
them) using real data from that game. If it's a first meeting, it stays
general — no invented opponent player details. Skipped automatically if
there's no game left on the schedule.

---

## Segment Structure by Game Type

The game is auto-classified from the score margin and overtime flag. Use the
type to guide which bank segments to include and how much room they get —
this is guidance for the selection described above, not a separate fixed
structure:

- **BLOWOUT_WIN** (won by 4+): `game_recap` can be brief or skipped — the
  score tells most of the story. `player_spotlight` is usually worth
  including since a blowout often means someone had a big game worth
  dwelling on. `gord_corner` is optional and short if included; he's got
  less to grumble about, though he can still find something.
- **BLOWOUT_LOSS** (lost by 4+): `game_recap` stays brief and matter-of-fact
  if included — don't dwell on every goal against. `gord_corner` is the
  strongest candidate here; this is where his frustration gets the most
  room. `player_spotlight` should usually be skipped unless there's one
  genuine bright spot worth a short mention.
- **CLOSE_OR_OVERTIME** (decided by 1 goal, or went to OT): `game_recap` is
  almost always worth including and expanding — this is the version of the
  show where the play-by-play tension matters most.
- **SHUTOUT_WIN** (opponent scored 0): if `player_spotlight` is included, it
  should lead with the goalie's performance before any skater.
- **SHUTOUT_LOSS** (we scored 0): `gord_corner` is a strong candidate here;
  `player_spotlight` should usually be skipped since there's no offensive
  standout — don't force one focused on "effort" just to fill the slot.
- **NORMAL**: No default weighting — pick freely based on what's genuinely
  most interesting about tonight's game.

---

## Special Segments (activate per-episode by adding to `active_special_segments` below)

### guest_coach
**Currently disabled** — set `ENABLED = True` at the top of `scripts/guest_coach.py`
to turn it back on. The code and cadence tracking are untouched and ready to
go; while disabled, `generate_script.py` skips this feature entirely and
doesn't advance the cadence log, so it picks back up cleanly whenever it's
re-enabled.

A one-off guest coach character joins for one segment to offer tactical advice,
taking the tactical-analysis slot in the bank that `gord_corner` would
otherwise fill, for that episode only. When enabled, this is fully
automatic — no manual config edit needed. `scripts/guest_coach.py` tracks a
randomized 3-6 episode gap and triggers this segment on its own; when it
fires, the model invents a brand new character on the spot (distinct from
Casey and Gord, bound by the same no-invented-facts rules) and the result
gets logged to `data/guest_coach_log.json` and mirrored into that game's
`special_guest` field in `data/schedule.json` afterward, for reference only.

### rivalry_alert
Use when the opponent is a team the Village People have a notable record against.
Requires: at least 2 prior games against this opponent in the season log.
Slot: part of the flexible bank, placed wherever it fits best — but before `next_game_preview`, since that segment closes the episode.

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
