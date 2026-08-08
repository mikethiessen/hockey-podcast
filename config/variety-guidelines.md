# Script Variety Guidelines

This file gives the AI tools to keep episodes feeling fresh even though every game
only produces three kinds of events: goals, assists, and penalties. Nothing here
invents new facts — it's about varying *how* real events are described and sequenced.

---

## 1. Phrase Banks

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

## 2. Vary What Opens the Recap

The Cold Open should still be Casey's (see host dynamic — Casey leads), but what
Casey opens *on* should vary game to game based on what's actually notable in the
data:

- A high-penalty game → open on the penalty count/tone, not the score first
- A game with a standout assist chain → open on the setup, then the score
- A tight/low-event game → open on the score, since there's not much else to lead with
- A blowout → open on the score, since that's the story

Pick whichever event type is most distinctive for *that* game's data rather than
defaulting to score-first every time.

---

## 3. Vary Reaction Order Within Segments

Casey always opens the Cold Open. That's fixed. But within other segments
(Game Recap, Player Spotlight, Season Storylines), it doesn't have to always be
"Casey says something, then Gord reacts." Let Gord occasionally be the one who
raises a point first within a segment, with Casey reacting — as long as Casey
still owns the top of the Cold Open.

---

## 4. Derive Patterns From the Existing Data (No New Fields Needed)

The stats JSON already contains period, clock_time, assist type, and penalty
severity. Use it:

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

---

## 5. Gord's Disagreement

Gord can push back on penalty calls specifically — was it fair, harsh, a good
call — since that's commentary on real data, not invented fact. This should feel
like genuine analyst disagreement, not forced conflict.
