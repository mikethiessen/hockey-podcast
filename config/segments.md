# Episode Segments

This file controls the segment structure for each episode.
Edit this file to add, remove, reorder, or introduce special segments.

---

## Standard Segments (run every episode)

- cold_open
- game_recap
- player_spotlight
- gord_corner
- season_storylines
- closing_take

---

## Special Segments (activate per-episode by adding to `active_special_segments` below)

### guest_coach
A mystery guest coach character joins for one segment to offer tactical advice.
Define the character in the episode's game entry in `data/schedule.json` under `special_guest`.
Example: `"special_guest": "Coach Boudreau, a retired AHL coach who takes rec hockey way too seriously"`
Replaces: `gord_corner` for that episode.

### milestone_watch
Use when a player is close to a season milestone (e.g. 5th goal, 10th point).
Requires: milestone data to be manually noted in `data/schedule.json` for that game.
Slot: inserted after `player_spotlight`.

### rivalry_alert
Use when the opponent is a team the Village People have a notable record against.
Requires: at least 2 prior games against this opponent in the season log.
Slot: inserted before `closing_take`.

---

## Active Special Segments This Episode

active_special_segments: []

<!-- 
To activate a special segment for the next episode, edit the list above. Example:
active_special_segments: [guest_coach]
Then add the guest details to the game entry in data/schedule.json.
After the episode generates, clear this list.
-->
