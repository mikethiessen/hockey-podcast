"""
Converts a podcast script to audio using ElevenLabs TTS.
Parses CASEY: / GORD: lines, generates audio for each,
stitches them together with pydub, and saves to
data/episodes/{game_id}/episode.mp3.
"""

import os
import sys
import random
import requests
from pathlib import Path
from pydub import AudioSegment
import io

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
AUDIO_DIR = ROOT / "audio"

# Fill these in after picking voices at elevenlabs.io
CASEY_VOICE_ID = "dczS3m0UuOM2UHQb1Jtc"
GORD_VOICE_ID = "9oa4l5rZznK9dXRwFpSB"

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

# Voice settings — tweak these to taste
# Model: eleven_turbo_v2_5 optimizes for low latency at the cost of expressiveness.
# This is a batch/offline job — latency doesn't matter here — so eleven_multilingual_v2
# trades a few extra seconds of generation time for noticeably more natural prosody
# and emotional inflection, which was a big part of the "flat" feedback.
TTS_MODEL_ID = "eleven_multilingual_v2"

CASEY_SETTINGS = {
    "stability": 0.50,       # was 0.45 — a touch more grounded, less prone to peaky/strained delivery
    "similarity_boost": 0.80,
    "style": 0.25,           # was 0.35 — high style pushes exaggeration; pulled back to reduce the
                             # pinched/strained "elevated" quality without losing his energy entirely
    "speed": 1.05,
    "use_speaker_boost": True
}
GORD_SETTINGS = {
    "stability": 0.52,
    "similarity_boost": 0.75,
    "style": 0.15,
    "speed": 1.2,
    "use_speaker_boost": True
}

# Silence between lines (milliseconds). A fixed gap every single time reads as
# metronomic/robotic — real back-and-forth conversation has some natural variance
# in beat length, so these are ranges; an actual duration is picked per-transition.
# Same-speaker pause (between sentences in one turn) is per-host: Casey was landing
# each sentence right on top of the last, which read as rushed.
CASEY_LINE_PAUSE_RANGE_MS = (400, 650)   # was shared (250, 450) — widened for Casey specifically
GORD_LINE_PAUSE_RANGE_MS = (250, 450)    # unchanged
SEGMENT_PAUSE_RANGE_MS = (350, 650)      # speaker switch

# Small fade applied to the start/end of every spoken segment. TTS output that's
# butted directly against silence can have an audible hard edge/click; a short
# fade softens that transition so pauses feel like natural conversational beats
# rather than pasted-in gaps.
SEGMENT_EDGE_FADE_MS = 15

# Intro music: trimmed to this length regardless of the source file's length,
# then faded out over the last 2 seconds of that trimmed clip
INTRO_DURATION_MS = 9000
INTRO_FADE_MS = 5000
# How much the first line of dialogue overlaps the tail of the fading intro.
# Should be <= INTRO_FADE_MS so dialogue starts while the music is audibly
# fading, not after it's already silent.
INTRO_OVERLAP_MS = 2000


def parse_script(script_path):
    """Parse script into list of (speaker, text) tuples."""
    lines = []
    current_speaker = None
    current_text = []

    with open(script_path) as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                if current_speaker and current_text:
                    lines.append((current_speaker, " ".join(current_text)))
                    current_speaker = None
                    current_text = []
                continue
            if line.startswith("CASEY:"):
                if current_speaker and current_text:
                    lines.append((current_speaker, " ".join(current_text)))
                current_speaker = "CASEY"
                current_text = [line[len("CASEY:"):].strip()]
            elif line.startswith("GORD:"):
                if current_speaker and current_text:
                    lines.append((current_speaker, " ".join(current_text)))
                current_speaker = "GORD"
                current_text = [line[len("GORD:"):].strip()]
            else:
                if current_speaker:
                    current_text.append(line)

    if current_speaker and current_text:
        lines.append((current_speaker, " ".join(current_text)))

    return [(s, t) for s, t in lines if t.strip()]


def tts_line(text, voice_id, voice_settings, api_key, previous_text=None, next_text=None):
    """Call ElevenLabs TTS API and return audio bytes.

    previous_text/next_text give the model surrounding textual context purely for
    intonation prediction (e.g. so a question mark actually produces a rising
    inflection, or a line lands with the right emphasis given what comes next).
    Each line is still a separate audio file — this doesn't stitch audio, it just
    stops every line from sounding like it was recorded in total isolation, which
    was contributing to the flat, disconnected feel between the two hosts' lines.
    """
    url = ELEVENLABS_API_URL.format(voice_id=voice_id)
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    payload = {
        "text": text,
        "model_id": TTS_MODEL_ID,
        "voice_settings": voice_settings
    }
    if previous_text:
        payload["previous_text"] = previous_text[-300:]
    if next_text:
        payload["next_text"] = next_text[:300]
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    if not resp.ok:
        print(f"  ElevenLabs error {resp.status_code}: {resp.text[:300]}")
        resp.raise_for_status()
    return resp.content


def generate_audio(game_id):
    print(f"Generating audio for game {game_id}...")

    api_key = os.environ["ELEVENLABS_API_KEY"]
    episode_dir = DATA_DIR / "episodes" / game_id
    script_path = episode_dir / "script.txt"

    if not script_path.exists():
        print(f"ERROR: Script not found at {script_path}")
        sys.exit(1)

    lines = parse_script(script_path)
    print(f"  Parsed {len(lines)} lines from script.")

    segments = []

    for i, (speaker, text) in enumerate(lines):
        print(f"  [{i+1}/{len(lines)}] {speaker}: {text[:60]}...")
        voice_id = CASEY_VOICE_ID if speaker == "CASEY" else GORD_VOICE_ID
        settings = CASEY_SETTINGS if speaker == "CASEY" else GORD_SETTINGS
        previous_text = lines[i - 1][1] if i > 0 else None
        next_text = lines[i + 1][1] if i < len(lines) - 1 else None

        audio_bytes = tts_line(text, voice_id, settings, api_key, previous_text, next_text)
        segment = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
        segment = segment.fade_in(SEGMENT_EDGE_FADE_MS).fade_out(SEGMENT_EDGE_FADE_MS)
        segments.append(segment)

        # Add pause — longer when speaker switches, with jitter so it doesn't
        # sound like the same silence clip pasted between every line
        if i < len(lines) - 1:
            next_speaker = lines[i + 1][0]
            if next_speaker != speaker:
                pause_ms = random.randint(*SEGMENT_PAUSE_RANGE_MS)
            else:
                line_range = CASEY_LINE_PAUSE_RANGE_MS if speaker == "CASEY" else GORD_LINE_PAUSE_RANGE_MS
                pause_ms = random.randint(*line_range)
            segments.append(AudioSegment.silent(duration=pause_ms))

    # Stitch all segments
    print("  Stitching audio...")
    combined = segments[0]
    for seg in segments[1:]:
        combined += seg

    # Prepend intro music, with the first line of dialogue overlapping the
    # fading tail of the music rather than waiting for it to finish
    intro_path = AUDIO_DIR / "intro.mp3"
    if intro_path.exists():
        print("  Blending intro music with dialogue...")
        intro = AudioSegment.from_mp3(str(intro_path))
        if len(intro) > INTRO_DURATION_MS:
            intro = intro[:INTRO_DURATION_MS]
        intro = intro.fade_out(min(INTRO_FADE_MS, len(intro)))

        overlap = min(INTRO_OVERLAP_MS, len(intro), len(combined))
        total_len = len(intro) + len(combined) - overlap

        blended = AudioSegment.silent(duration=total_len)
        blended = blended.overlay(intro, position=0)
        blended = blended.overlay(combined, position=len(intro) - overlap)
        combined = blended
    else:
        print("  No intro.mp3 found — skipping intro music.")

    # Export
    output_path = episode_dir / "episode.mp3"
    combined.export(str(output_path), format="mp3", bitrate="128k")
    print(f"  Audio saved to {output_path} ({len(combined) / 1000:.1f}s)")

    return str(output_path)


if __name__ == "__main__":
    game_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not game_id:
        print("Usage: python generate_audio.py <game_id>")
        sys.exit(1)
    generate_audio(game_id)
