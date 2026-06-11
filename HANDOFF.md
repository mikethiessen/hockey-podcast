# Hockey Podcast Project — Handoff Brief

## What this project is
Fully automated podcast pipeline for a recreational hockey team called **the Village People** (Winnipeg ASHL Men's 18+ E division). After every game, the system automatically detects the game ended, fetches stats, generates a ~5-minute podcast script with two fictional hosts, converts it to audio via ElevenLabs TTS, and uploads it to Buzzsprout — all via GitHub Actions, no manual steps.

---

## What's already built

**Config files** (in `/config`):
- `hosts.md` — defines the two hosts: Casey Bright (young, optimistic lead host) and Gord Slapshot (grizzled veteran who thinks violence solves everything — running gag is he keeps suggesting illegal hits then remembers it's a no-contact league)
- `podcast-guidelines.md` — strict rules on what the AI can/can't say, episode structure (cold_open → game_recap → player_spotlight → gord_corner → season_storylines → closing_take), and script format (`CASEY: ...` / `GORD: ...`)
- `segments.md` — segment config including optional special segments (guest_coach, milestone_watch, rivalry_alert)
- `players.md` — full roster of 24 players with notes

**Data** (`/data/schedule.json`) — all 10 games for the 2026 summer season, each with `episode_generated: false` flag

**Scripts** already written:
- `scripts/sync_schedule.py` — fetches the SportNinja schedule API and auto-adds new games to schedule.json
- `scripts/check_schedule.py` — checks if a Village People game finished within the last 20 minutes (game_status_id == 9, ended_at within window)
- `scripts/fetch_stats.py` — fetches and parses full game data into a clean dict (goals, assists, penalties, roster, period-by-period scores)

**GitHub Actions workflow** (`.github/workflows/podcast-pipeline.yml`):
- Runs on cron every 15 minutes
- Job 1: `check-for-game` — syncs schedule, checks for recently completed game, outputs `found` and `game_id`
- Job 2: `generate-episode` — runs only if `found == true`, calls generate_script.py → generate_audio.py → upload_episode.py, then commits updated data/ back to repo
- Supports `workflow_dispatch` with optional `game_id` input for manual testing

---

## What still needs to be built

### Phase 4 — `scripts/generate_script.py`

Calls the Anthropic Claude API to generate the podcast script.

Inputs it should load:
- Game stats: call `fetch_stats.get_game_stats(game_id)` — returns a dict with game_id, date, venue, our_team, opponent, home_or_away, our_score, opp_score, result, went_to_overtime, periods[], our_goals[], their_goals[], penalties[], players_present[], players_absent[], goalie
- Past game context: read `data/schedule.json` and load episode summaries from any previously generated games (to enable season storylines)
- Config files: read `config/hosts.md`, `config/podcast-guidelines.md`, `config/segments.md`, `config/players.md`

Output: save the script to `data/episodes/{game_id}/script.txt`

Also update `data/schedule.json` to set `episode_generated: true` for the game after success.

The script format must be strictly:
```
CASEY: [dialogue]

GORD: [dialogue]
```

Use `claude-opus-4-8` or `claude-sonnet-4-6` via the Anthropic Python SDK. API key comes from `ANTHROPIC_API_KEY` env var.

---

### Phase 5 — `scripts/generate_audio.py`

Calls ElevenLabs TTS API to convert the script to audio.

- Parse the script line by line, splitting on `CASEY:` and `GORD:` labels
- Call ElevenLabs `/v1/text-to-speech/{voice_id}` for each line, alternating between two voice IDs
- Voice IDs are not yet chosen — store them as constants at the top of the file (`CASEY_VOICE_ID` and `GORD_VOICE_ID`) so the user can fill them in after picking voices at elevenlabs.io
- Stitch audio clips together using `pydub`
- Optionally prepend intro music if a file exists at `audio/intro.mp3`
- Save final audio to `data/episodes/{game_id}/episode.mp3`

API key from `ELEVENLABS_API_KEY` env var.

---

### Phase 6 — `scripts/upload_episode.py`

Uploads the episode to Buzzsprout.

- POST to `https://www.buzzsprout.com/api/{podcast_id}/episodes.json`
- Auth header: `Authorization: Token token={BUZZSPROUT_API_TOKEN}`
- Episode title format: `"vs. {opponent} — {date}"` (e.g. "vs. Dusters — June 9")
- Description: short summary pulled from the script or a generic template
- Attach the mp3 file from `data/episodes/{game_id}/episode.mp3`

Env vars: `BUZZSPROUT_API_TOKEN`, `BUZZSPROUT_PODCAST_ID`

---

## Key API details

**SportNinja API** (public, no auth needed):
- Schedule: `GET https://canlan2-api.sportninja.net/v1/schedules/wkh2BQJfxrHuziPq/games`
- Game stats: `GET https://canlan2-api.sportninja.net/v1/games/{game_id}`
- Must send `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36` or you get 403
- Team ID for Village People: `Nz7BgbzbxfrhWtft`
- `game_status_id: 9` means the game is final

**GitHub Actions secrets needed** (not yet added to the repo):
- `ANTHROPIC_API_KEY`
- `ELEVENLABS_API_KEY`
- `BUZZSPROUT_API_TOKEN`
- `BUZZSPROUT_PODCAST_ID`

---

## Accounts the user still needs to set up
- **Anthropic API** — needs account at console.anthropic.com
- **ElevenLabs** — needs account, then pick 2 voices (one for Casey, one for Gord) and copy their voice IDs
- **Buzzsprout** — needs free account, then grab the Podcast ID and API token from the dashboard
