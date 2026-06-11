"""
Converts a podcast script to audio using ElevenLabs TTS.
Parses CASEY: / GORD: lines, generates audio for each,
stitches them together with pydub, and saves to
data/episodes/{game_id}/episode.mp3.
"""

import os
import sys
import requests
from pathlib import Path
from pydub import AudioSegment
import io

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
AUDIO_DIR = ROOT / "audio"

# Fill these in after picking voices at elevenlabs.io
CASEY_VOICE_ID = "CASEY_VOICE_ID_HERE"
GORD_VOICE_ID = "GORD_VOICE_ID_HERE"

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

# Voice settings — tweak these to taste
CASEY_SETTINGS = {
    "stability": 0.40,
    "similarity_boost": 0.80,
    "style": 0.35,
    "use_speaker_boost": True
}
GORD_SETTINGS = {
    "stability": 0.65,
    "similarity_boost": 0.75,
    "style": 0.20,
    "use_speaker_boost": True
}

# Silence between lines (milliseconds)
LINE_PAUSE_MS = 400
SEGMENT_PAUSE_MS = 700


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


def tts_line(text, voice_id, voice_settings, api_key):
    """Call ElevenLabs TTS API and return audio bytes."""
    url = ELEVENLABS_API_URL.format(voice_id=voice_id)
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg"
    }
    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": voice_settings
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
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
    silence_short = AudioSegment.silent(duration=LINE_PAUSE_MS)
    silence_long = AudioSegment.silent(duration=SEGMENT_PAUSE_MS)

    prev_speaker = None
    for i, (speaker, text) in enumerate(lines):
        print(f"  [{i+1}/{len(lines)}] {speaker}: {text[:60]}...")
        voice_id = CASEY_VOICE_ID if speaker == "CASEY" else GORD_VOICE_ID
        settings = CASEY_SETTINGS if speaker == "CASEY" else GORD_SETTINGS

        audio_bytes = tts_line(text, voice_id, settings, api_key)
        segment = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
        segments.append(segment)

        # Add pause — longer when speaker switches
        if i < len(lines) - 1:
            next_speaker = lines[i + 1][0]
            if next_speaker != speaker:
                segments.append(silence_long)
            else:
                segments.append(silence_short)

        prev_speaker = speaker

    # Stitch all segments
    print("  Stitching audio...")
    combined = segments[0]
    for seg in segments[1:]:
        combined += seg

    # Prepend intro music if it exists
    intro_path = AUDIO_DIR / "intro.mp3"
    if intro_path.exists():
        print("  Prepending intro music...")
        intro = AudioSegment.from_mp3(str(intro_path))
        # Fade out intro over last 2 seconds
        intro = intro.fade_out(2000)
        combined = intro + AudioSegment.silent(duration=500) + combined
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
