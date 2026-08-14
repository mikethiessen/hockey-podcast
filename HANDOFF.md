# Hockey Podcast Project — Handoff Brief

## What this project is
Fully automated podcast pipeline for a recreational hockey team called **the Village People** (Winnipeg ASHL Men's 18+ E division). After every game, the system automatically detects the game ended, fetches stats, generates a ~5-minute podcast script with two fictional hosts, converts it to audio via ElevenLabs TTS, and uploads it to Buzzsprout — all via GitHub Actions, no manual steps.

**Status: fully built and working.** Currently in a testing/refinement phase — being used for real starting next season.

---

## Config files (`/config`)

- **`hosts.md`** — Casey Bright (young, optimistic lead host — background as a recent rec player plus a sports-media "underdog storyline" worldview, an offensive-stats analytical lens, a rare "crack in the armor" beat on bad losses) and Gord Slapshot (grizzled veteran colour commentator — 20+ years playing contact hockey, postgame-beers-in-the-dressing-room background, a PIM "power ranking" running bit, and the core "suggests something illegal, catches himself" running gag). Both hosts have an explicit "opinion vs. fact" guardrail so color and interpretation never drift into invented game facts.
- **`podcast-guidelines.md`** — core rules on what the AI can/can't say, episode structure (7 segments including `next_game_preview`), tone/style, script format, and how season resets work in code, not just in the prompt.
- **`segments.md`** — segment list, game-type-based structural flexing (blowout/shutout/close game emphasis), and optional special segments (`guest_coach`, `milestone_watch`, `rivalry_alert`).
- **`recurring-bits.md`** — a bank of optional callbacks (Nickname Mill, Back In My Day, Standings Tangent, Callback to Last Episode, Casey's Disco Detour, Gord's Grudging Compliment). The model picks 1-2 that genuinely fit each episode's real data — nothing here is mandatory per episode.
- **`variety-guidelines.md`** — phrase banks and structural variety rules (what opens the recap, reaction order, multi-point/assist-chain/penalty-clustering treatment) so scripts don't sound formulaic even though every game only produces goals/assists/penalties.
- **`players.md`** — full roster with notes.

---

## Scripts (`/scripts`)

- **`sync_schedule.py`** — fetches the SportNinja schedule API, adds new games to `schedule.json`.
- **`check_schedule.py`** — checks if a Village People game finished recently and hasn't had an episode generated. Note: `SCHEDULE_ID` is hardcoded and must be updated manually when Canlan starts a new schedule instance (e.g. regular season → playoffs) — there's no auto-discovery endpoint.
- **`fetch_stats.py`** — fetches and parses full game data (goals, assists, penalties, roster, period-by-period).
- **`season_stats.py`** — computes real season-long aggregates (points leaders, active point streaks, frequent scoring connections, penalty leaders) and `recent_form` (real win/loss signal over the last 5 games, used to nudge the host dynamic dial). Everything here is scoped to the current game's `season` field, so it resets automatically at season boundaries.
- **`relationship_log.py`** — maintains `data/relationship_log.json`, a season-scoped log of real, checkable predictions hosts make and notable moments they have. Resolves predictions against real results/stats in code (never guessed by the model) and matches prior moments to tonight's opponent/game type. Entries only get created when the model actually tags something worth logging (`PREDICTION:`/`MOMENT:` trailing lines, stripped before the script is saved) — nothing is forced every episode.
- **`generate_script.py`** — the core generation script. Loads game stats, all config files, past episode summaries, next-game preview context, season stats, recent form, and relationship context, then calls the Anthropic API (`claude-sonnet-4-6`) to write the script. Strips relationship tags, updates `data/relationship_log.json`, saves `script.txt` and `summary.json`, marks `episode_generated: true`.
- **`generate_audio.py`** — converts the script to audio via ElevenLabs TTS, alternating Casey/Gord voice IDs, stitches with `pydub`, blends in intro music from `audio/intro.mp3`.
- **`upload_episode.py`** — uploads the finished mp3 to Buzzsprout with a formatted title/description.

---

## GitHub Actions workflow (`.github/workflows/podcast-pipeline.yml`)

- Triggered by an external cron poller (cron-job.org) via `workflow_dispatch`, roughly every 1-2 minutes, plus a `schedule` cron every 15 minutes as backup.
- Job 1: `check-for-game` — syncs schedule, checks for a recently completed game.
- Job 2: `generate-episode` — runs only if a game was found; calls `generate_script.py` → `generate_audio.py` → `upload_episode.py`, then commits updated `data/` back to the repo.
- Supports `workflow_dispatch` with an optional `game_id` input for manual testing.

---

## Key API details

**SportNinja API** (public, no auth needed):
- Schedule: `GET https://canlan2-api.sportninja.net/v1/schedules/{SCHEDULE_ID}/games` — `SCHEDULE_ID` is hardcoded in `check_schedule.py` and `sync_schedule.py` and must be updated manually when Canlan issues a new schedule instance (e.g. playoffs).
- Game stats: `GET https://canlan2-api.sportninja.net/v1/games/{game_id}`
- Must send `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36` or you get 403.
- Team ID for Village People: `Nz7BgbzbxfrhWtft`
- `game_status_id: 9` means the game is final.

**GitHub Actions secrets required:** `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`, `BUZZSPROUT_API_TOKEN`, `BUZZSPROUT_PODCAST_ID`.

---

## Data integrity notes for whoever picks this up next season

- `data/schedule.json`'s `season` field is the single source of truth for season-scoping. `season_stats.py`, `relationship_log.py`, and `load_past_episodes()` in `generate_script.py` all key off it. Changing the season value for new games is what triggers the "start fresh" behavior described in `podcast-guidelines.md`.
- The relationship log (`data/relationship_log.json`) resets to empty automatically the first time it's loaded with a new season value — no manual cleanup needed between seasons.
- Before relying on `recent_form` or season storylines for real broadcast use, make sure episodes are being generated for every completed game in order — gaps in `episode_generated` don't break the numbers (which pull live from the API regardless), but they do create gaps in `load_past_episodes()`'s context and in the relationship log's callback material, since those only read from games that actually got a script written.
