# Content Bank

Material to draw from when building an episode. It opens with the show's
richest creative territory — the season-long theories the hosts develop and
their accountability for past claims — because that's where an episode
becomes worth listening to twice. What follows (segment contents, bits, gags,
phrasing) is supporting material: examples of the register this show works
in, not a checklist to work through.

See `script-construction.md` for how an episode picks and orders from this
bank, and `core-rules.md` for the hard rules that apply underneath all of it.

---

## Season-Long Theories (the hosts' own running arguments)

This is where the show earns repeat listeners. Per-game facts are a closed set —
who scored, who assisted, who sat. But a *theory* about the season compounds
across episodes, and only someone who's been listening can appreciate it paying
off or falling apart.

Casey and Gord can each develop a running thesis about this team and revisit it
as the season goes: that they win when a particular pair connects, that penalty
trouble is what actually costs them games, that a specific player is on the
verge of a breakout, that the team is better on the road. A theory is
**interpretation, not fact** — it must be built only on real numbers from the
season stats provided, and framed as what a host believes rather than something
the data proves. Never invent a stat to support one.

The interesting part isn't stating a theory — it's testing it. Tonight's real
result either supports a host's standing theory, complicates it, or blows it up
entirely. Let them notice that. A theory that survives three episodes and then
collapses is better television than one that's simply correct, and a host
quietly dropping a theory he was loud about is its own kind of callback.

Don't force a theory into every episode, and don't invent one where the data
gives nothing to build on. But when a real season-long pattern is there, it's
almost always more interesting than restating who leads in points.

---

## Holding the Hosts Accountable

The past-episode context and the relationship log carry forward what Casey and
Gord actually said in previous episodes — predictions they made, players they
wrote off, calls they were confident about. Use it.

The show should be willing to revisit its own past claims against what really
happened: Gord's skepticism about a player who has since been producing, Casey's
"he's about to break out" call that either landed or didn't, a prediction that
aged badly. Being *wrong* is more fun than being right, and a host having to
concede it is one of the few things that genuinely can't be appreciated on a
first listen.

Only do this when there's a specific, real prior claim to return to — never
invent a past prediction or misremember what was actually said. If the log has
nothing concrete, skip it.

---

## Segment Content

What each segment actually contains. Whether it's an anchor (always present)
or part of the flexible bank (picked per episode) is defined in
`script-construction.md` — this section is just what goes in it once chosen.

- **Cold Open** — Casey's very first line always welcomes listeners
  to the show by name (e.g. "Welcome to Ice & Easy!" — vary the exact
  phrasing episode to episode) — this opening line plays under the tail of
  the intro music, so it needs to work as a clean opener on its own. What
  Casey and Gord lead on immediately after that welcome is NOT fixed — see
  `script-construction.md`'s "Vary Delivery" section for choosing the
  final score, penalty tone, an assist chain, etc. based on what's most
  distinctive in tonight's game, rather than the score by default.
- **Game Recap** — who scored, who assisted, how the game
  unfolded. Keep this about *what happened and who was involved*, not a
  period-by-period or clock-time-by-clock-time recitation — only call out a
  specific time if it's genuinely part of the story (a last-minute goal, a
  rapid flurry, a third-period collapse). Most episodes will want this, but
  if the cold open or player spotlight already covers what happened, it's
  fine to skip a separate recap rather than repeat it.
- **Player Spotlight** — whatever real pattern in tonight's data is most
  worth dwelling on. Often that's a single standout performer, but it can
  just as easily be a pair who kept connecting, a goalie's night, a
  defensive effort, or a team-wide trend the season stats surfaced — let the
  data set the scope rather than forcing it into a fixed number of players.
  Can be positive or negative. Skip this one entirely if nothing tonight
  genuinely stood out — don't manufacture a spotlight out of an
  unremarkable performance just to fill the slot.
- **The Gord Corner** — Gord gives his "tactical analysis."
- **Season Storylines** — the heart of the show's long-term
  identity, and the single best place to be genuinely creative. The per-game
  data is a closed set, but the season layer compounds: build the storyline
  out of *change over time* — a rank that moved, a streak that broke, a
  first that only counts as a first because of everything
  before it — rather than reciting current standings. This is also where the
  hosts' running theories and their own past claims come into play (see
  "Season-Long Theories" and "Holding the Hosts Accountable" at the top of
  this file). Be
  creative in *how* a real pattern gets presented — but never state a number
  that isn't in the provided season stats data.
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

Examples of the kind of bit that works on this show — not an exhaustive menu.
Pick 1, occasionally 2, that fit this episode's data — don't force one in if
nothing fits. Just as often, invent a genuinely new one-off bit that tonight's
data suggests and the list below doesn't cover; a bit that only makes sense
because of what happened in *this* game is usually better than reaching for a
stock one. The examples exist to show the register, not to limit the options.
These are separate from Gord's core "safe hockey league" running gag below —
that gag is its own thing, situational and NOT on a fixed cadence.

- **The Nickname Mill**: Casey tries out a nickname for a player who had a
  notable moment (goal, key assist, big penalty kill) this game. Gord either
  shoots it down instantly or, rarely, admits it's not bad.

- **Back In My Day**: Gord compares something from this game to how it
  "used to be played," always in a way that circles back to missing physical
  play.

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

This is occasional, not a per-episode beat — most episodes shouldn't use it
at all. Reach for it only when tonight's game gives a genuinely specific,
strong opening (a borderline hit, a scrum, a hard collision that was
otherwise clean), not any minor or generic contact moment. When in doubt,
skip it — it should feel like a rare, earned release of frustration, not a
running expectation the show has to hit every time.

### Casey's Mispronunciation
Casey occasionally mispronounces or misremembers something that Gord
corrects grumpily — only when it arises naturally in the flow of a segment,
not forced into every episode.

---

## Phrasing

Hockey events repeat constantly — goals, assists, penalties are most of what
the data contains — so the language describing them has to carry the variety
the events themselves don't.

Don't reuse the same verb or construction for an event type across a script,
and avoid repeating phrasing from the previous episode's summary. Casey and
Gord should also describe the same *kind* of event differently from each
other; they're different people, and a goal Casey calls one thing Gord would
describe another way entirely. Reach for whatever fits the moment and the
speaker rather than a house style for each event type.

---

## Gord's Disagreement

Gord can push back on penalty calls specifically — was it fair, harsh, a good
call — since that's commentary on real data, not invented fact. This should feel
like genuine analyst disagreement, not forced conflict.

---

## Derive Patterns From the Existing Data (No New Fields Needed)

The stats JSON already contains period, time_elapsed, assist type, and penalty
severity. `time_elapsed` is the time elapsed into that period (not time
remaining) — e.g. "10:12" in a 12-minute period means it happened late, with
under two minutes left; "1:00" means it happened early. Use it:

- **Multi-point games**: if a player appears as both a scorer and an assister
  in the same game's `our_goals` list, call that out as a multi-point night.
- **Assist chains**: if a goal has 2 assists, it's a passing play — describe it
  as one. If it has 0 assists, call it a hustle/individual goal.
- **Penalty clustering by period**: look at the `period` field on each penalty
  entry. If most penalties happened in one period, say so ("three of the four
  penalties came in the third") instead of listing them flatly in order.
- **Quick hits**: when a game has a lot of minor events (e.g. 4+ penalties, or
  several late/low-impact goals), group the less important ones into a fast
  "quick hits" list rather than giving each the same full treatment as the
  headline events.
