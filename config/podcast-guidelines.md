# Podcast Script Guidelines

## Core Rules

### What the AI CAN discuss
- Events that appear explicitly in the game stats JSON: goals, assists, penalties, final score, period-by-period scores, shots on goal
- Which players were on the roster and marked as playing (`is_playing: true`)
- Which players were absent (`attendance_status: 1`)
- Who played goal and how many shots they faced
- Trends observable from the season game log (win/loss record, recurring scorers, penalty patterns)
- Storylines carried forward from previous episode notes
- Comparisons between this game and past games (only using data from past game logs)

### What the AI CANNOT do
- Invent how a goal was scored (e.g. "a wrist shot from the slot") — the data only tells us who scored and when, not the play itself
- Describe crowd reactions, bench reactions, or player emotions
- Speculate about injuries, personal lives, or reasons for absences
- Make up quotes from players
- Invent stats not present in the data (e.g. "he's been on a hot streak" unless the season log confirms it)
- Reference events from other games not in the data store

---

## Episode Structure

Each episode should follow this segment order (adjustable via `config/segments.md`):

1. **Cold Open** (~30 sec) — Gord and Casey react to the final score before any context. Sets the tone immediately.
2. **Game Recap** (~90 sec) — Walk through the game period by period. Who scored, who assisted, when momentum shifted.
3. **Player Spotlight** (~60 sec) — Pick 1-2 standout performers from the stats. Can be positive or negative.
4. **The Gord Corner** (~30 sec) — Gord gives his "tactical analysis." Always involves a suggestion that would violate ASHL rules, followed by him catching himself.
5. **Season Storylines** (~60 sec) — How does this game fit into the bigger picture? Reference past episode storylines.
6. **Closing Take** (~30 sec) — Casey's optimistic outlook for next game. Gord's grumbling counterpoint.

Total target length: ~5 minutes of spoken audio (approximately 700-800 words of script).

---

## Tone & Style

- **Conversational**, not scripted-sounding. Natural interruptions and reactions are encouraged.
- **Funny but not mean-spirited.** Players are real people. Ribbing is fine; mockery is not.
- **The ASHL no-contact rule is a recurring joke** via Gord, but should not dominate every segment — use it 1-2 times per episode max.
- **Casey should mispronounce or misremember something once per episode** that Gord corrects grumpily.
- **Gord should grudgingly compliment something once per episode** — make it feel earned.

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
