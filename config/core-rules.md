# Podcast Core Rules

These are the hard, always-true rules for every episode, independent of which
segments get chosen. See `script-construction.md` for how an episode actually
gets assembled, and `content-bank.md` for the material to draw from.

---

## What the AI CAN discuss
- Events that appear explicitly in the game stats JSON: goals, assists, penalties, final score, period-by-period scores, shots on goal
- Which players were on the roster and marked as playing (`is_playing: true`)
- Which players were absent (`attendance_status: 1`)
- Who played goal and how many shots they faced
- Trends observable from the season game log: win/loss record, and the computed season stats provided each episode (points leaders, active point streaks, frequent scoring connections, penalty trends) — all derived from real per-game data, never estimated
- Storylines carried forward from previous episode notes
- Comparisons between this game and past games (only using data from past game logs)

## What the AI CANNOT do
- Invent how a goal was scored (e.g. "a wrist shot from the slot") — the data only tells us who scored and when, not the play itself
- Describe crowd reactions, bench reactions, or player emotions
- Speculate about injuries, personal lives, or reasons for absences
- Make up quotes from players
- Invent stats not present in the data (e.g. "he's been on a hot streak" unless the season log confirms it)
- Reference events from other games not in the data store

---

## Tone & Style

- **Conversational**, not scripted-sounding. Natural interruptions and reactions are encouraged.
- **Funny but not mean-spirited.** Players are real people. Ribbing is fine; mockery is not.

For the specific recurring gags and bits that flesh out this tone (the ASHL
no-contact joke, Casey's mispronunciations, Gord's grudging compliment, etc.),
see `content-bank.md` — this section is just the blanket rule that applies
underneath all of them.

---

## Script Format

Scripts must use this exact format for the TTS parser:

```
CASEY: [dialogue here]

GORD: [dialogue here]
```

No stage directions, no parentheticals, no asterisks for emphasis. Just the speaker label and their words.

---

## Season Reset

When the season changes (Winter → Summer or Summer → Winter), the hosts should acknowledge the new season in the first episode but carry no memory of past season stats or storylines. Start fresh.

This is enforced automatically in code, not just in the script prompt: `season_stats.py`'s computations, `data/relationship_log.json` (predictions and notable moments), and the recent-form signal are all scoped to the current game's `season` field in `schedule.json`. When the season value changes, the relationship log resets to empty and all season-stat computations start counting from the first game of the new season.
