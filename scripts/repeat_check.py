"""
Checks a freshly written script against the last few episodes for reuse.

The prompt already tells the model not to reuse jokes, openers or phrasing from
recent episodes (episode_memory.py), but that is only a request. This is the
check: plain code, no network, that finds what actually got reused so the
generator can ask for one rewrite.

What counts as a repeat:
  - the opening line is nearly the same as a recent opening line
  - the closing line is nearly the same as a recent closing line (the next-game
    preview is required, so this threshold is deliberately high)
  - the same run of several words shows up in the new script and a recent one
    (a reused joke, catchphrase, reaction line or transition)

Things that legitimately repeat are ignored: the show name (every episode must
welcome listeners to it), and any run of words containing a digit, a number word,
a weekday, a month or a home/away word, because dates, times, scores, stats and
the required next-game preview all repeat on purpose.
"""

import re
from difflib import SequenceMatcher

SHINGLE_WORDS = 7          # a shared run this long is a reused phrase, not coincidence
MIN_SHARED_SHINGLES = 2    # how many distinct shared runs before we call it a repeat
OPENER_SIMILARITY = 0.6
CLOSER_SIMILARITY = 0.85

PREVIEW_DATA_TOKENS = 3    # a closing line with this many date/time/venue words is the preview
MIN_OPENER_WORDS = 4       # an opener shorter than this (after the show name) can't be varied much

_SPEAKER = re.compile(r"^(CASEY|GORD):\s*(.*)$")
_WORDS = re.compile(r"[a-z0-9']+")

# The show name has to be said every episode, so it is not a reused phrase.
_SHOW_NAME = re.compile(
    r"(?:the\s+)?village\s+people\s+hockey\s+podcast|ice\s*(?:&|and)\s*easy|village\s+people",
    re.IGNORECASE,
)

# Words that mark a run as data (dates, times, counts, venue) rather than a joke.
_DATA_WORDS = frozenset("""
monday tuesday wednesday thursday friday saturday sunday
january february march april may june july august september october november december
zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen
fifteen sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy
eighty ninety hundred first second third fourth fifth
am pm tonight tomorrow home away road
""".split())


def dialogue_lines(script):
    """[(speaker, text)] for every CASEY:/GORD: line. Trailing tags (PREDICTION:
    and friends) and blank lines are not dialogue and are skipped."""
    out = []
    for line in script.splitlines():
        m = _SPEAKER.match(line.strip())
        if m:
            out.append((m.group(1), m.group(2).strip()))
    return out


def _words(text):
    text = _SHOW_NAME.sub(" ", text)
    return _WORDS.findall(text.lower().replace("’", "'"))


def _shingles(text):
    """Set of SHINGLE_WORDS-long word runs in `text`, skipping any run with a digit."""
    words = _words(text)
    runs = set()
    for i in range(len(words) - SHINGLE_WORDS + 1):
        run = words[i:i + SHINGLE_WORDS]
        if any(ch.isdigit() for w in run for ch in w) or any(w in _DATA_WORDS for w in run):
            continue
        runs.add(tuple(run))
    return runs


def _content_words(text):
    """Words with the data words (dates, times, numbers, home/away) removed, so a
    required next-game preview line is not mistaken for a reused sign-off."""
    return [w for w in _words(text)
            if w not in _DATA_WORDS and not any(ch.isdigit() for ch in w)]


def _is_preview_line(text):
    """A line heavy with dates, times and venue is the required next-game preview,
    not a sign-off, so it isn't held to the sign-off rule."""
    n = sum(1 for w in _words(text) if w in _DATA_WORDS or any(ch.isdigit() for ch in w))
    return n >= PREVIEW_DATA_TOKENS


def _similarity(a, b, words=_words):
    wa, wb = words(a), words(b)
    if not wa or not wb:
        return 0.0
    return SequenceMatcher(None, wa, wb).ratio()


def find_repeats(script, recent_scripts):
    """Compare `script` to each of `recent_scripts` (a list of script strings).

    Returns {"has_repeats": bool, "issues": [str]}. Each issue is a short plain
    sentence naming the repeated line or phrase, written to be pasted into a
    rewrite request.
    """
    new_lines = dialogue_lines(script)
    if not new_lines or not recent_scripts:
        return {"has_repeats": False, "issues": []}

    issues = []
    new_open = new_lines[0][1]
    new_close = new_lines[-1][1]

    for old in recent_scripts:
        old_lines = dialogue_lines(old)
        if not old_lines:
            continue
        if len(_words(new_open)) >= MIN_OPENER_WORDS and \
                _similarity(new_open, old_lines[0][1]) >= OPENER_SIMILARITY:
            issues.append(
                f'The opening line ("{new_open}") is nearly the same as a recent episode\'s opener.'
            )
        if not _is_preview_line(new_close) and len(_content_words(new_close)) >= MIN_OPENER_WORDS and \
                _similarity(new_close, old_lines[-1][1], _content_words) >= CLOSER_SIMILARITY:
            issues.append(
                f'The closing line ("{new_close}") is nearly the same as a recent episode\'s closer.'
            )

    old_runs = set()
    for old in recent_scripts:
        for _, text in dialogue_lines(old):
            old_runs |= _shingles(text)

    flagged = []
    shared_total = 0
    for speaker, text in new_lines:
        shared = _shingles(text) & old_runs
        if shared:
            shared_total += len(shared)
            flagged.append(f"{speaker}: {text}")

    if shared_total >= MIN_SHARED_SHINGLES:
        for line in flagged:
            issues.append(f'This line reuses wording from a recent episode: "{line}"')

    # The same issue can be found against more than one old script.
    seen, unique = set(), []
    for issue in issues:
        if issue not in seen:
            seen.add(issue)
            unique.append(issue)
    return {"has_repeats": bool(unique), "issues": unique}


def format_rewrite_request(issues):
    """The follow-up message asking the model to rewrite its own draft."""
    listed = "\n".join(f"- {i}" for i in issues)
    return (
        "Your draft needs a rewrite. Fix each of these (for anything reused from recent "
        "episodes, use fresh wording, fresh jokes and a fresh angle):\n\n"
        f"{listed}\n\n"
        "Keep everything else that works: the facts, the featured lenses, the fixed frame "
        "(welcome, score early, next-game preview last), the length target, and any "
        "PREDICTION/THEORY/THEORY_UPDATE/MOMENT tags that still apply. Output only the "
        "script in the same format, with nothing before or after it."
    )
