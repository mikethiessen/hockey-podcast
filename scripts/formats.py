"""
Picks the SHAPE of tonight's episode: its format, the host dynamic, and the length.

Why this exists: lenses (lenses.py) vary WHAT the hosts talk about, but every
lens is a stats angle, so episodes can still feel alike in how they move. Here
code picks three independent knobs, the same way it picks lenses:

  shape    how the middle is organized (a debate, rapid-fire takes, one long thread...)
  dynamic  who drives the conversation and the energy between the hosts
  length   short, standard or long

Each knob avoids what the previous episodes used, and the choice is a random one
seeded by the game id plus a per-knob salt, so a re-run of the same game with the
same history picks the same things (testing stays predictable) and the knobs vary
independently of each other and of the lens choice.

Nothing here decides content or facts. The descriptions live in config/formats.md
so they can be edited without touching Python; the ids and the rotation rules live
here.
"""

import random

from config_loader import load_config

SHAPES = (
    "shape_debate",
    "shape_rapid_fire",
    "shape_single_thread",
    "shape_what_if",
    "shape_one_host_holds_court",
    "shape_tangent_and_return",
)

DYNAMICS = (
    "dynamic_casey_drives",
    "dynamic_gord_drives",
    "dynamic_sparring",
    "dynamic_in_sync",
    "dynamic_off_their_game",
)

# Standard is the default feel of the show, so it gets the most weight. A short
# or long episode is the exception that keeps the show from feeling metronomic.
LENGTH_WEIGHTS = (
    ("length_short", 3),
    ("length_standard", 5),
    ("length_long", 2),
)

# How many most-recent episodes a knob avoids repeating.
SHAPE_LOOKBACK = 2
DYNAMIC_LOOKBACK = 1
LENGTH_LOOKBACK = 1

# A short episode shouldn't be paired with a shape that needs room to breathe.
_NEEDS_ROOM = ("shape_tangent_and_return", "shape_one_host_holds_court")


def _recent(past_episodes, key, lookback):
    used = []
    for ep in (past_episodes[-lookback:] if lookback else []):
        value = ep.get(key)
        if value:
            used.append(value)
    return used


def _pick(options, avoid, seed, salt):
    """One of `options` not in `avoid` (falls back to all of them if every option
    is recent), chosen by a seeded random choice."""
    rng = random.Random(f"{seed}:{salt}")
    fresh = [o for o in options if o not in avoid]
    return rng.choice(fresh or list(options))


def pick_length(past_episodes, seed):
    avoid = _recent(past_episodes, "length", LENGTH_LOOKBACK)
    rng = random.Random(f"{seed}:length")
    pool = [(l, w) for l, w in LENGTH_WEIGHTS if l not in avoid] or list(LENGTH_WEIGHTS)
    names = [l for l, _ in pool]
    weights = [w for _, w in pool]
    return rng.choices(names, weights=weights, k=1)[0]


def pick_shape(past_episodes, seed, length=None):
    avoid = _recent(past_episodes, "shape", SHAPE_LOOKBACK)
    options = [s for s in SHAPES if not (length == "length_short" and s in _NEEDS_ROOM)]
    return _pick(options, avoid, seed, "shape")


def pick_dynamic(past_episodes, seed):
    avoid = _recent(past_episodes, "dynamic", DYNAMIC_LOOKBACK)
    return _pick(DYNAMICS, avoid, seed, "dynamic")


def pick_format(past_episodes, seed):
    """Choose all three knobs for one episode. Returns
    {"shape": id, "dynamic": id, "length": id}."""
    length = pick_length(past_episodes, seed)
    return {
        "length": length,
        "shape": pick_shape(past_episodes, seed, length=length),
        "dynamic": pick_dynamic(past_episodes, seed),
    }


def load_format_descriptions(config_dir=None):
    """Parse config/formats.md into {id: description}. Sections start with
    '## <id>'; '# ' headings and anything before the first '## ' are ignored."""
    text = load_config("formats.md", config_dir)
    descriptions, current, buf = {}, None, []
    for line in text.splitlines():
        if line.startswith("## "):
            if current is not None:
                descriptions[current] = " ".join(" ".join(buf).split())
            current, buf = line[3:].strip(), []
        elif line.startswith("# "):
            if current is not None:
                descriptions[current] = " ".join(" ".join(buf).split())
            current, buf = None, []
        elif current is not None:
            buf.append(line.strip())
    if current is not None:
        descriptions[current] = " ".join(" ".join(buf).split())
    return descriptions


def _describe(chosen, descriptions):
    missing = [v for v in chosen.values() if not descriptions.get(v)]
    if missing:
        raise KeyError(
            "config/formats.md has no description for: " + ", ".join(missing)
        )
    return {k: descriptions[v] for k, v in chosen.items()}


def format_format_guidance(chosen, descriptions):
    """Text for the brief's {{format_guidance}} placeholder (shape + dynamic)."""
    d = _describe(chosen, descriptions)
    return (
        "This episode's shape. It changes how the conversation moves, not what is "
        "true: the facts rules and the fixed frame (welcome, score early, next-game "
        "preview last) still apply, and the featured lenses are still your material. "
        "Don't name the shape out loud.\n\n"
        f"- **Shape:** {d['shape']}\n"
        f"- **Host dynamic:** {d['dynamic']}"
    )


def format_length_guidance(chosen, descriptions):
    """Text for the brief's {{length_guidance}} placeholder."""
    return _describe(chosen, descriptions)["length"]
