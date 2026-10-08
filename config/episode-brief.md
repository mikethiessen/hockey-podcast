<!--
Editor notes (stripped before the model sees this file):
- This is the per-run task brief sent at the end of every prompt.
- Placeholders filled in by generate_script.py:
    {{game_type}}        e.g. BLOWOUT_LOSS (a tone cue only)
    {{featured_lenses}}  the 2-3 angles chosen for tonight (see lenses.md / lenses.py)
- The output format (CASEY:/GORD: lines) and the PREDICTION/MOMENT/THEORY tag
  grammar are NOT here on purpose: parsers depend on them, so they live in
  generate_script.py.
- Structure rules live in script-construction.md. This file is the short list of
  reminders for this particular run, so keep it from growing into a second copy.
-->

## Your Task

Write tonight's episode, following the Script Construction frame above. Game type: **{{game_type}}** (a tone cue only, not a structure).

{{featured_lenses}}

Requirements:
- The frame: Casey's very first line is a short welcome to the show by name (it plays under the tail of the intro music, so it must work as a standalone opener; vary the exact wording). The final score and who won come right after it. The episode ends on the next-game preview, using the Next Game Preview section above: date, time, opponent, and home or away. If that section says there is no next game, leave the preview out.
- Everything between is yours. Spend most of it on the season: trends, predictions, speculation, and the hosts' own earlier claims. Give tonight's game only the time it earns and use it as evidence for the season story.
- Keep total spoken length around 5 minutes (700-800 words).
- Never state a number, streak, trend, or record that isn't in the data above. Be creative in HOW you present a real number, never in WHAT it is. Frame projections as projections ("on pace for") and opinion as opinion.
- Don't recite exact clock times or walk through periods mechanically. Only call out a time or period when it's genuinely part of the story: a late winner, a flurry of goals, a third-period collapse.
- Do not reuse anything from the Recent Episodes block: jokes, bits, catchphrases, reaction lines, openers, closers, or transitions. If a bit appears there, it is spent.
- Bits are optional, at most one or two, and a bit that only makes sense because of tonight's game beats a stock one.
- Opposing players: only name players listed in a Scouting report block, or in the prior-meeting data in the Next Game Preview section. If neither lists any, name no opposing players. Use only the numbers given.
- Make a prediction only when the data genuinely supports one. If the Relationship Context lists a prediction that real results have now settled, settle it on air.
- Never name the structure out loud: no segment labels or lens names ("our player spotlight", "the Gord Corner", "season storylines").
- If a "Milestones" section is present, weave those real facts in wherever they fit. If a "Special Segment: Guest Coach" section is present, the guest takes over the tactical-analysis moment for this episode only.
- If a Relationship Context section is present, use only what genuinely fits. Never force a callback.
- Do not invent any detail not present in the game stats JSON, the Next Game Preview data, or the Scouting report blocks.
