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
A mystery guest coach character joins for one segment to offer tactical advice.
Define the character in the episode's game entry in `data/schedule.json` under `special_guest`.
Example: `"special_guest": "Coach Boudreau, a retired AHL coach who takes rec hockey way too seriously"`
Replaces: `gord_corner` for that episode.

### milestone_watch
Use when a player is close to a season milestone (e.g. 5th goal, 10th point).
Requires: milestone data to be manually noted in `data/schedule.json` for that game.
Slot: inserted after `player_spotlight`.

### rivalry_alert
Use when the opponent is a team the Village People have a notable record against.
Requires: at least 2 prior games against this opponent in the season log.
Slot: inserted before `closing_take`.

---

## Active Special Segments This Episode

active_special_segments: []

<!-- 
To activate a special segment for the next episode, edit the list above. Example:
active_special_segments: [guest_coach]
Then add the guest details to the game entry in data/schedule.json.
After the episode generates, clear this list.
-->
