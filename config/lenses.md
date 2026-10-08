<!--
Editor notes (stripped before the model sees this file):
- A "lens" is an angle on the season that the hosts can build the middle of an
  episode around. Each episode features a few of them, chosen by scripts/lenses.py.
- Python decides which lenses have real data behind them tonight and rotates away
  from ones used recently. This file only describes what each lens is for.
- The heading (## name) must match a lens id in scripts/lenses.py. Add a new lens
  here AND in lenses.py (with its "has real data" rule), or it will never be chosen.
- Keep each description about the angle, not about exact lines to say. Specific
  jokes belong to the hosts, not this file.
-->

# Lenses

## accountability
A prediction one of the hosts made in an earlier episode has now been settled by real results (see "Relationship Context"). Settle it on air. The host who made it owns the result, the other host gets to react, and how each handles being right or wrong should come from who they are. Make it a moment, not a scoreboard read-out.

## theory_check
One of the hosts' open theories (see "Relationship Context") deserves a revisit against tonight's real result. Does tonight support it, complicate it, or blow it up? The host who floated it reacts honestly: doubling down, hedging, and quietly dropping it are all fair. Record the verdict with a THEORY_UPDATE tag.

## new_theory
One host floats a new season-long theory, built only on the real numbers in the season stats and framed as what he believes, not what the data proves. The other host pushes back. Make it specific enough that a later episode can test it, and record it with a THEORY tag.

## prediction
One host calls a specific, checkable shot about the next game, backed by the real numbers (the season stats, the Season Outlook block, the matchup), and the other host fades it. Record it with a PREDICTION tag. If the data doesn't really support a call, skip this and speculate instead.

## trajectory
Someone is climbing or sliding in the productivity order compared with a few games ago. What changed, and is it real or a blip? The hosts should disagree about whether it lasts. Use only the ranks and numbers listed in the season stats.

## chemistry
Two names keep showing up together on the scoresheet. Is this a partnership the team should build around, or a coincidence opponents will solve? Use only the real pair counts listed.

## streaks
A streak is the story: a player's run of games with a point, or the team's current run of results. How long might it last, what would break it, and what does it say about the team? Use only the streaks listed.

## discipline
Penalties as a season-long theme: who takes them, whether things are getting better or worse over time, and what they cost. Gord's penalty-minutes power ranking fits naturally here when the numbers earn it.

## goaltending
The goalie's season: shots faced per game, goals against, and what a typical night looks like back there. Credit or sympathy, but grounded in the listed numbers.

## period_splits
The team's season shape by period: where it scores, where it leaks, where games get won or lost. Offer a theory for why, clearly as opinion.

## leads_and_shots
The gap between shots and results, or between games led and games won: a team that outshoots opponents and still loses, or leads and can't hold it. What does that say about how this team plays?

## home_road
Home versus road. Is there a real difference, and what would each host blame it on? Opinion, grounded in the listed records.

## pace_outlook
Look down the road using the Season Outlook block: what the season could look like if the current rate holds, what would have to change, and which player is on pace for what. Always "on pace for", never "will finish with".

## matchup
The next opponent's record next to ours (see the Season Outlook block): what it suggests about the next game, who has the edge, and what each host is excited or nervous about.

## rivalry
We have already played the next opponent this season (see the Next Game Preview). Revisit that meeting with the real numbers: what happened, what is different now, and who owes whom.

## lineup
Players are back from missing games (see "Back in the lineup tonight"). What does the lineup look like with them, and what did the team look like without them? Opinion only; never speculate about why anyone was out.

## firsts
Something happened tonight for the first time this season, or at a season high (see "Rare / first-time events"). What does it mean in the context of the season so far?

## season_outlook
There isn't enough data yet for statistical trends, so the hosts speak from tonight's game and from belief: what they hope or fear about the season and what they'll be watching for. Opinion only, with no invented numbers.
