<!--
Editor notes (stripped before the model sees this file):
- A "format" is the SHAPE of the episode's middle: how the hosts talk about the
  material, not what the material is. Lenses (lenses.md) decide the topics; a
  format decides the way the conversation moves. scripts/formats.py picks one
  shape, one host dynamic and one length per episode, rotating away from recent ones.
- Three kinds of section, told apart by the heading prefix. The heading must match
  an id in scripts/formats.py:
    ## shape_<name>     how the middle of the episode is organized
    ## dynamic_<name>   who drives the conversation and the energy between the hosts
    ## length_<name>    how long the episode runs
- Describe the shape, never exact lines. Jokes belong to the hosts.
- The facts rules in core-rules.md and the fixed frame in script-construction.md
  (welcome, score early, next-game preview last) always win over anything here.
-->

# Shapes

## shape_debate
Build the middle around ONE real disagreement between the hosts and let it run. They stake out opposite sides of a single question the data raises, trade specific points, interrupt each other, and don't settle it neatly. Everything else in the episode orbits that argument.

## shape_rapid_fire
The middle is a run of short takes: several quick exchanges, each one a single data point and a verdict, then on to the next. Nobody lingers. The energy comes from pace, not depth, so keep each take to a few lines.

## shape_single_thread
Pick the one thing in the data that is most worth talking about and follow it all the way down. Resist the urge to cover the lenses evenly. A lens that doesn't connect to the thread can be skipped or given a single line.

## shape_what_if
One host builds a "what if" from real numbers (what if the top scorers had been together, what if the team had kept its early pace) and the other pokes holes in it. Keep it clearly hypothetical and say so, with no invented numbers.

## shape_one_host_holds_court
One host takes a long run at a point he cares about while the other mostly reacts in short interjections, then they swap for a different point. The long turns should sound like a person talking, not a list.

## shape_tangent_and_return
Start on the season material, let the hosts wander into a tangent that grows out of the data (a player, a habit, a bit of dressing-room color), and have them find their way back. The tangent must be built from what is in the prompt, never from invented facts.

# Dynamics

## dynamic_casey_drives
Casey sets the agenda and keeps pulling the conversation toward the bigger season picture. Gord reacts, undercuts, and occasionally takes the wheel for a line or two.

## dynamic_gord_drives
Gord leads: he has opinions to air and a point to prove, and Casey is the one reacting, defending, and trying to steer back to the positives.

## dynamic_sparring
Neither host drives. They disagree, a lot, and the back-and-forth itself is the energy. Each should concede something at least once.

## dynamic_in_sync
The hosts are unusually on the same page tonight and build on each other's points, finishing each other's thoughts. The tension comes from the team, not from them.

# Lengths

## length_short
A tight episode of roughly 3.5 to 4 minutes (about 450-600 words). Fewer threads, less warm-up. A short episode is a complete episode, not a trimmed one: the welcome, the score and the next-game preview all still happen.

## length_standard
Around 5 minutes (700-800 words).

## length_long
Up to about 5.5 minutes (roughly 800-900 words), never more than 6 minutes, only because there is genuinely more worth saying. Do not stretch to fill it: if the material runs out sooner, stop sooner.
