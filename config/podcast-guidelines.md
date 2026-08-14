# Podcast Script Guidelines

## Core Rules

### What the AI CAN discuss
- Events that appear explicitly in the game stats JSON: goals, assists, penalties, final score, period-by-period scores, shots on goal
- Which players were on the roster and marked as playing (`is_playing: true`)
- Which players were absent (`attendance_status: 1`)
- Who played goal and how many shots they faced
- Trends observable from the season game log: win/loss record, and the computed season stats provided each episode (points leaders, active point streaks, frequent scoring connections, penalty trends) — all derived from real per-game data, never estimated
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

1. **Cold Open** (~30 sec) — Casey's very first line welcomes listeners to the show by name (e.g. "Welcome to Ice & Easy!" — vary the exact phrasing episode to episode) before reacting to the final score. This opening line plays under the tail of the intro music, so it needs to work as a clean opener on its own. Gord and Casey then react to the final score before any other context. Sets the tone immediately.
2. **Game Recap** (~30 sec) — Who scored, who assisted, how the game unfolded. Keep this about *what happened and who was involved*, not a period-by-period or clock-time-by-clock-time recitation — only call out a specific time if it's genuinely part of the story (a last-minute goal, a rapid flurry, a third-period collapse).
3. **Player Spotlight** (~60 sec) — Pick 1-2 standout performers from the stats. Can be positive or negative.
4. **The Gord Corner** (~30 sec) — Gord gives his "tactical analysis." See `hosts.md`'s running gag for how and when he suggests something that would violate ASHL rules — it should come from a real opening in tonight's game, not appear automatically every episode.
5. **Season Storylines** (~60-90 sec) — The heart of the show's long-term identity. Use real, computed season stats (points leaders, active streaks, frequent scoring connections, penalty trends) to build a storyline, not just a one-off recap of tonight. Be creative in *how* a real stat gets presented — but never state a number that isn't in the provided season stats data.
6. **Closing Take** (~30 sec) — Casey's optimistic outlook for next game. Gord's grumbling counterpoint.
7. **Next Game Preview** (~20 sec) — Date, time, and opponent for the next scheduled game. If we've already played this opponent this season, recap the last meeting using real data. See `segments.md` for full rules — this segment is skipped entirely if there's no game left on the schedule.

Total target length: ~5 minutes of spoken audio (approximately 700-800 words of script).

---

## Tone & Style

- **Conversational**, not scripted-sounding. Natural interruptions and reactions are encouraged.
- **Funny but not mean-spirited.** Players are real people. Ribbing is fine; mockery is not.
- **The ASHL no-contact rule is a recurring joke** via Gord — see `hosts.md` for the running gag. It should come up when tonight's game naturally opens the door for it, up to 1-2 times per episode at most. It's fine for an episode to not use it at all if nothing calls for it.
- **Casey occasionally mispronounces or misremembers something** that Gord corrects grumpily — only when it arises naturally in the flow of a segment, not forced into every episode.
- **Gord's grudging-compliment beat** is one of the optional Recurring Bits in `recurring-bits.md` ("Gord's Grudging Compliment") — use it when it fits the data, same as any other bit from that bank, not as a mandatory once-per-episode beat.

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
