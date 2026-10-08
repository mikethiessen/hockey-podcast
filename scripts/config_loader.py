"""
Loads human-editable prompt text from config/*.md and fills in {{placeholders}}.

Design rules (so editing a markdown file can't quietly break an episode):
- A missing or empty config file raises immediately.
- A {{placeholder}} in the text with no value supplied raises immediately,
  instead of sending the model a half-built prompt.
- HTML comments (<!-- ... -->) are editor notes and are stripped before the
  text is used, so notes to yourself never reach the model.
- Only plain {{name}} substitution happens here. No logic lives in the
  markdown. Anything conditional is decided in Python.
"""

import re
from pathlib import Path

CONFIG_DIR = Path(__file__).parent.parent / "config"

_PLACEHOLDER = re.compile(r"\{\{\s*(\w+)\s*\}\}")
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def load_config(name, config_dir=None):
    """Read a config file by name (e.g. "episode-brief.md"), comments stripped."""
    path = Path(config_dir or CONFIG_DIR) / name
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    text = _COMMENT.sub("", path.read_text()).strip()
    if not text:
        raise ValueError(f"Config file is empty: {path}")
    return text


def render_template(text, values, source="template"):
    """Replace every {{name}} in text with str(values[name]).

    Raises ValueError if the text uses a placeholder that has no value.
    Extra, unused values are ignored.
    """
    needed = set(_PLACEHOLDER.findall(text))
    missing = sorted(needed - set(values))
    if missing:
        raise ValueError(
            f"{source} uses placeholder(s) with no value supplied: "
            + ", ".join("{{" + m + "}}" for m in missing)
        )
    return _PLACEHOLDER.sub(lambda m: str(values[m.group(1)]), text)


def load_rendered(name, values, config_dir=None):
    """Load a config file and fill its placeholders in one step."""
    return render_template(load_config(name, config_dir), values, source=name)
