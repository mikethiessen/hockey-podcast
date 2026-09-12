# Content Bank

Every reusable piece of episode material lives here: what each segment
actually contains, the special segments, the organic milestone material,
the recurring bits, and the running gags. See `script-construction.md` for
how an episode picks and orders from this bank, and `core-rules.md` for the
hard rules that apply underneath all of it.

---

## Segment Content

What each segment actually contains. Whether it's an anchor (always present)
or part of the flexible bank (picked per episode) is defined in
`script-construction.md` — this section is just what goes in it once chosen.

- **Cold Open** (~30 sec) — Casey's very first line always welcomes listeners
  to the show by name (e.g. "Welcome to Ice & Easy!" — vary the exact
  phrasing episode to episode) — this opening line plays under the tail of
  the intro music, so it needs to work as a clean opener on its own. What
  Casey and Gord lead on immediately after that welcome is NOT fixed — see
  `script-construction.md`'s "Vary What Opens the Recap" for choosing the
  final score, penalty tone, an assist chain, etc. based on what's most
  distinctive in tonight's game, rather than the score by default.
- **Game Recap** (~20 sec) — who scored, who assisted, how the game
  unfolded. Keep this about *what happened and who was involved*, not a
  period-by-period or clock-time-by-clock-time recitation — only call out a
  specific time if it's genuinely part of the story (a last-minute goal, a
  rapid flurry, a third-period collapse). Most episodes will want this, but
  if the cold open or player spotlight already covers what happened, it's
  fine to skip a separate recap rather than repeat it.
- **Player Spotlight** — pick 1-2 standout performers from the stats. Can be
  positive or negative. Skip this one entirely if nothing tonight genuinely
  stood out — don't manufacture a spotlight out of an unremarkable
  performance just to fill the slot.
- **The Gord Corner** (~20 sec) — Gord gives his "tactical analysis."
- **Season Storylines** (~60-90 sec) — the heart of the show's long-term
  identity. Use real, computed season stats (points leaders, active
  streaks, frequent scoring connections, penalty trends) to build a
  storyline, not just a one-off recap of tonight. Be creative in *how* a
  real stat gets presented — but never state a number that isn't in the
  provided season stats data.
- **Next Game Preview** — date, time, and opponent for the next scheduled
  game. If we've already played this opponent this season, recap the last
  meeting using real data. This segment also carries the show's closing
  beat: Casey's outlook heading into that next game, and Gord's grumbling
  counterpoint — fold that into the same segment rather than treating it as
  a separate goodbye. Skipped entirely if there's no game left on the
  schedule.

---

## Special Segments

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
Recurring Bits do. Fully automatic; no manual config edit needed.
`scripts/milestones.py` detects two kinds of real, data-only events each
episode:
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

## Recurring Bits

A bank of optional callbacks and running bits. Pick 1, occasionally 2, that fit
this episode's data — don't force one in if nothing fits. Never use the same
bit two episodes in a row (check the past episode context provided). These are
separate from Gord's core "safe hockey league" running gag below — that gag is
its own thing, situational and NOT on a fixed cadence.

- **The Nickname Mill**: Casey tries out a nickname for a player who had a
  notable moment (goal, key assist, big penalty kill) this game. Gord either
  shoots it down instantly or, rarely, admits it's not bad.

- **Back In My Day**: Gord compares something from this game to how it
  "used to be played," always in a way that circles back to missing physical
  play. Only use if it hasn't come up in the last episode's script.

- **The Standings Tangent**: If the schedule data or past results give any
  real basis for it, Casey speculates enthusiastically about where this
  result puts the team, and Gord deflates it. Skip entirely if there's no
  real data to speculate from — do not invent a standing or record.

- **Callback to Last Episode**: Reference something specific that happened in
  the immediately preceding episode (a storyline, a Gord prediction, a bit)
  using the past-episode context provided, and follow up on it — did it hold
  up, did Gord jinx it, etc. Only use when there IS a specific prior detail
  worth returning to; skip if the past episode gave nothing concrete to
  callback to.

- **Casey's Disco Detour**: Casey makes a Village People / disco-era reference
  tied to something that happened in the game (a player's name, a play style,
  the final score). Keep it quick — one line, not a tangent.

- **Gord's Grudging Compliment**: Gord is walked, reluctantly, into admitting
  a specific player or play was genuinely good — but immediately undercuts
  the compliment with a complaint about something unrelated. Use it when it
  fits the data, same as any other bit in this bank, not as a mandatory
  once-per-episode beat.

Usage note: these are flavor, not filler. If a bit doesn't have real data to
hang on, skip it rather than forcing it in generically.

---

## Running Gags

### Gord's "Safe League" Gag
When a game situation calls for it, Gord suggests a physical response, then
catches himself and remembers he's in a no-contact league. Vary the wording
each time rather than repeating a set phrase — the beat is "he catches
himself and gripes about the safe league," not a specific line, for example
something like this being exactly the spot for a good hip check, except this
league would probably suspend him for even thinking about it.

This should come from a real opening in the moment, not appear on a fixed
cadence. It's fine for an episode to not use it at all if nothing calls for it.

### Casey's Mispronunciation
Casey occasionally mispronounces or misremembers something that Gord
corrects grumpily — only when it arises naturally in the flow of a segment,
not forced into every episode.

---

## Phrase Banks

Don't reuse the same verb/phrase for an event type every episode. Rotate through
variants like these (write your own in the same spirit — this is a starting set,
not a fixed list to quote verbatim):

**Goals**
- "buried it"
- "found the back of the net"
- "beat the goalie clean"
- "snuck one through"
- "capitalized on the chance"
- "got the puck to go in"
- "put the Village People on the board"
- "made it count"

**Assists**
- "set that up"
- "threaded the pass"
- "did the legwork on that one"
- "picked up the helper"
- "made the play that made the play"
- "got credit for the assist"

**Penalties**
- "took a seat in the box"
- "picked up two minutes"
- "gave the other team a power play"
- "got called for it"
- "cost the team a man"
- "found himself in the box"

Casey and Gord should not describe the same *kind* of event identically twice in
one script, and should avoid repeating the exact same phrase from the previous
episode's summary where possible.

---

## Gord's Disagreement

Gord can push back on penalty calls specifically — was it fair, harsh, a good
call — since that's commentary on real data, not invented fact. This should feel
like genuine analyst disagreement, not forced conflict.
