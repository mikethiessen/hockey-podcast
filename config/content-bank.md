# Content Bank

Material and register to draw from when building an episode. Nothing here is a
checklist and nothing here is required. It opens with the show's richest
creative territory — the season-long theories the hosts develop and their
accountability for past claims — because that's where an episode becomes worth
listening to twice. What follows (predictions, bits, gags, phrasing, data
patterns) is supporting material: examples of the register this show works in.

See `script-construction.md` for the frame an episode fits in, `lenses.md` for the
angles featured each episode, and `core-rules.md` for the hard rules that apply
underneath all of it.

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

## Predictions and Speculation

The show looks down the road as much as it looks back. Where this team is
heading, who is on pace for what, who has the edge in the next game: this is
opinion territory, and it should sound like opinion.

- Frame projections as projections: "on pace for", "if this keeps up", "I'd bet".
  Never "will finish with". The numbers underneath must be real; the conclusion is
  the host's belief.
- The hosts should see it differently. A prediction one of them loves, the other
  can fade. Neither should win every time.
- A specific call is more fun than hype. "They win Sunday" or "he gets to ten
  points by the break" gives the show something to come back to; "I like this
  team's energy" doesn't.
- Only make a prediction when the data genuinely supports one. If it doesn't,
  speculate about the season instead, or skip it.

---

## Scouting Opponents

When a "Scouting report" block is present, one or more of the opposing team's
players clearly outscore the rest of their team. That's worth the hosts' attention:
a heads-up in the preview, or, for tonight's opponent, an explanation of how the
game went. Use only the players and numbers listed. If no such block is present,
the opponent has no standout scorers worth naming, so the hosts don't name any
opposing player beyond those already given elsewhere in the prompt.

---

## Milestones (organic, not a segment)

This is real material that should surface naturally inside whatever the hosts are
discussing, the same way a bit does. Fully automatic; no manual config edit
needed. `scripts/milestones.py` detects two kinds of real, data-only events each
episode:
- A player becoming the sole new season leader in goals, assists, points, or
  penalties, but only when they recorded that stat in tonight's game — and
  each category has its own 3-episode cooldown so a back-and-forth lead race
  doesn't get mentioned every episode.
- A player extending an active goal-scoring streak to 3+ consecutive games
  played.
Nothing is invented; both checks run purely on real per-game stats. When
something qualifies, weave it in conversationally wherever it genuinely fits, not
announced on its own. Results are logged to `data/milestone_log.json` and mirrored
into that game's `milestones` field in `data/schedule.json` afterward, for
reference only.

---

## Bits and Flavor

Examples of the kind of bit that works on this show — not a menu, and not
required. Most episodes need at most one or two, and plenty need none. A bit that
only makes sense because of what happened in *this* game is almost always better
than a stock one, so invent new ones from tonight's data.

The one firm rule: anything that has already run in a recent episode is spent.
Check the Recent Episodes block and retire any bit, catchphrase, or reaction line
that appears there. If a bit doesn't have real data to hang on, skip it rather
than forcing it in.

- **The Nickname Mill**: Casey tries out a nickname for a player who had a
  notable moment this game. Gord shoots it down, or rarely admits it's not bad.
- **Back In My Day**: Gord compares something from this game to how it "used to
  be played," in a way that circles back to missing physical play.
- **The Standings Tangent**: Casey speculates enthusiastically about where a
  result puts the team, and Gord deflates it. Only with real data to speculate
  from; never invent a standing or record.
- **Callback to Last Episode**: reference something specific that happened in a
  recent episode and follow up on it: did it hold up, did Gord jinx it? Only when
  there is a specific prior detail worth returning to.
- **Casey's Disco Detour**: a quick Village People / disco-era reference tied to
  something in the game. One line, not a tangent.

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

---

## Phrasing

Hockey events repeat constantly — goals, assists, penalties are most of what
the data contains — so the language describing them has to carry the variety
the events themselves don't.

Don't reuse the same verb or construction for an event type across a script,
and avoid repeating phrasing from the recent episodes. Casey and
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

## Guest Coach (currently disabled)

Set `ENABLED = True` at the top of `scripts/guest_coach.py` to turn it back on.
The code and cadence tracking are untouched and ready to go; while disabled,
`generate_script.py` skips this feature entirely and doesn't advance the cadence
log, so it picks back up cleanly whenever it's re-enabled.

When enabled, it is fully automatic. `scripts/guest_coach.py` tracks a randomized
3-6 episode gap and, when it fires, a "Special Segment: Guest Coach" section
appears in the prompt: the model invents a brand new character on the spot
(distinct from Casey and Gord, bound by the same no-invented-facts rules) who
takes over the tactical-analysis moment for that episode only. The result is
logged to `data/guest_coach_log.json` and mirrored into that game's
`special_guest` field in `data/schedule.json`, for reference only.

---

## Derive Patterns From the Existing Data (No New Fields Needed)

The stats JSON already contains period, time_elapsed, time_remaining, assist
type, and penalty severity. `time_elapsed` is the time elapsed into that period
(not time remaining) — e.g. "10:12" in a 12-minute period means it happened
late, with under two minutes left. `time_remaining` is the flip side — how
much time was left in the period at that moment — so a low `time_remaining`
value is a late/last-minute event without doing any subtraction. For the order
things happened in, use `game_timeline` (goals and penalties from both teams,
already merged into one true chronological sequence) rather than reconstructing
order from `our_goals`/`their_goals`/`penalties` separately. Use this data:

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
- **Scoring runs and game flow**: use `game_timeline` to notice things that only
  show up in true sequence — a team scoring several in a row, who actually
  opened or closed the scoring, a late collapse or comeback. Don't describe a
  sequence of events (who scored first, a run of unanswered goals, how the game
  closed) without checking `game_timeline` for the real order first.
