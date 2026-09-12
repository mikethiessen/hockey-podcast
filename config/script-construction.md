# Script Construction

This is the decision layer: how an episode actually gets assembled from
`content-bank.md`, given tonight's real game data. See `core-rules.md` for
the hard rules that apply no matter what gets picked, and `content-bank.md`
for what each segment/bit/gag actually contains.

---

## Episode Structure

There are three fixed anchors. Everything else is a flexible bank — choose
which of those to include and in what order based on what actually happened
in tonight's game, not a fixed checklist run the same way every episode.
Total spoken length should still land around ~5 minutes (700-800 words)
regardless of how many segments you pick — an episode with fewer segments
runs each one a bit longer; a busier episode with more segments keeps each
one tighter. Don't pad a segment just to hit a word count, and don't force
one in when tonight's game gives it nothing to say.

**Anchors (always present):**
- `cold_open` — always first
- `season_storylines` — required every episode, position among the others is flexible
- `next_game_preview` — always last, also carries the closing take (Casey's
  outlook + Gord's grumbling counterpoint)

**Flexible bank (pick and order per episode, based on what tonight's game
actually supports — not a fixed checklist):**
- `game_recap`
- `player_spotlight`
- `gord_corner`
- Any active special segment (e.g. `rivalry_alert`)

---

## Segment Structure by Game Type

The game is auto-classified from the score margin and overtime flag. Use the
type to guide which bank segments to include and how much room they get —
this is guidance for the selection above, not a separate fixed structure:

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

## Vary Delivery

Selection and ordering aren't the only place variety matters — how a segment
unfolds should vary too, on both of these axes:

- **What opens the recap.** Casey's very first line is always the fixed
  welcome-to-the-show opener (see `hosts.md`/`core-rules.md`) — that never
  changes. But what comes immediately after it should vary game to game
  based on what's actually notable in the data: a high-penalty game opens on
  the penalty count/tone rather than the score; a standout assist chain
  opens on the setup, then the score; a tight or low-event game just opens
  on the score, since there's not much else to lead with; a blowout does the
  same, since the score *is* the story. Pick whichever event type is most
  distinctive for tonight's data rather than defaulting to score-first every
  time.
- **Who speaks first within a segment.** Casey always opens the Cold Open —
  that's fixed. But within other segments (Game Recap, Player Spotlight,
  Season Storylines), it doesn't have to always be "Casey says something,
  then Gord reacts." Let Gord occasionally raise the point first, with Casey
  reacting, as long as Casey still owns the top of the Cold Open.

---

## Active Special Segments This Episode

active_special_segments: []

<!--
guest_coach is fully automatic (see content-bank.md) — do NOT add it here.
milestone_watch is not a special segment at all — see content-bank.md's
"Milestones" section; it's never added here.
rivalry_alert is still manual for now: to activate it for the next episode,
edit the list above, e.g.:
active_special_segments: [rivalry_alert]
Then add the required data to the game entry in data/schedule.json.
After the episode generates, clear this list.
-->

