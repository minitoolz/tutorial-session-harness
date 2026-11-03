"""SETTINGS.md loading, onboarding checks, and the session gate.

SETTINGS.md = YAML frontmatter (machine-readable) + free prose (for agents).
The session gate forces every agent to re-read SETTINGS.md after it changes:
`tutor start` records its hash; other commands refuse to run if it drifted.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

SETTINGS_FILE = "SETTINGS.md"
EXAMPLE_FILE = "SETTINGS.example.md"
STAMP_FILE = Path(".tutor") / "session"

AUDIENCE_REQUIRED = ("field", "background", "strong_in", "weak_in", "math_level", "goals")

# Frontmatter keys passed straight through to pandoc as metadata/variables.
PANDOC_KEYS = (
    "lang", "mainfont", "sansfont", "monofont", "mathfont", "CJKmainfont",
    "fontsize", "papersize", "geometry", "linestretch", "numbersections",
    "toc", "toc-depth", "colorlinks", "linkcolor", "urlcolor", "documentclass",
)

REVIEW_DEFAULTS = {
    "max_sentence_words": 25,       # latin-script sentences
    "max_sentence_chars_cjk": 60,   # CJK sentences, non-space characters
    "max_paragraph_sentences": 5,
}


class TutorError(Exception):
    """A user-facing error; the CLI prints it and exits non-zero."""


def find_root() -> Path:
    env = os.environ.get("TUTOR_ROOT")
    if env:
        return Path(env).resolve()
    cur = Path.cwd().resolve()
    for p in (cur, *cur.parents):
        if (p / "AGENTS.md").is_file() and (p / "topics").is_dir():
            return p
    raise TutorError(
        "Cannot find the project root (a directory with AGENTS.md and topics/). "
        "Run from inside the project or set TUTOR_ROOT."
    )


def split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("\n---", 1)
    if len(parts) != 2:
        return {}, text
    head = parts[0][3:]
    body = parts[1].split("\n", 1)[1] if "\n" in parts[1] else ""
    data = yaml.safe_load(head) or {}
    if not isinstance(data, dict):
        raise TutorError("SETTINGS.md frontmatter must be a YAML mapping.")
    return data, body


def _blank(v) -> bool:
    if v is None:
        return True
    if isinstance(v, str):
        return not v.strip() or "TODO" in v
    if isinstance(v, (list, dict)):
        return len(v) == 0
    return False


@dataclass
class Settings:
    path: Path
    exists: bool
    data: dict = field(default_factory=dict)
    body: str = ""
    raw: str = ""

    @property
    def audience(self) -> dict:
        a = self.data.get("audience") or {}
        return a if isinstance(a, dict) else {}

    def missing_audience(self) -> list[str]:
        return [k for k in AUDIENCE_REQUIRED if _blank(self.audience.get(k))]

    @property
    def onboarding_required(self) -> bool:
        return not self.exists or bool(self.missing_audience())

    @property
    def style(self) -> str:
        return str(self.data.get("style") or "article")

    @property
    def author(self) -> str:
        return str(self.data.get("author") or "")

    def review_limits(self) -> dict:
        limits = dict(REVIEW_DEFAULTS)
        limits.update(self.data.get("review") or {})
        return limits

    def pandoc_metadata(self) -> dict:
        meta = {k: self.data[k] for k in PANDOC_KEYS if self.data.get(k) not in (None, "")}
        # `language` is the friendly name in SETTINGS; pandoc calls it `lang`.
        if "lang" not in meta and self.data.get("language"):
            meta["lang"] = self.data["language"]
        return meta

    def digest(self) -> str:
        return hashlib.sha256(self.raw.encode()).hexdigest() if self.exists else ""


def load(root: Path) -> Settings:
    path = root / SETTINGS_FILE
    if not path.is_file():
        return Settings(path=path, exists=False)
    raw = path.read_text(encoding="utf-8")
    data, body = split_frontmatter(raw)
    return Settings(path=path, exists=True, data=data, body=body, raw=raw)


def write_stamp(root: Path, s: Settings) -> None:
    stamp = root / STAMP_FILE
    stamp.parent.mkdir(exist_ok=True)
    stamp.write_text(json.dumps({"settings_sha256": s.digest()}))


def gate(root: Path) -> Settings:
    """Return settings, or raise if the agent hasn't (re)read them via `tutor start`."""
    s = load(root)
    if not s.exists:
        raise TutorError(
            "ONBOARDING REQUIRED: SETTINGS.md does not exist.\n"
            "Follow skills/onboarding/SKILL.md (interview the user), then run `uv run tutor start`."
        )
    if s.onboarding_required:
        raise TutorError(
            "ONBOARDING REQUIRED: SETTINGS.md audience is incomplete "
            f"(missing: {', '.join(s.missing_audience())}).\n"
            "Follow skills/onboarding/SKILL.md, then run `uv run tutor start`."
        )
    stamp = root / STAMP_FILE
    try:
        recorded = json.loads(stamp.read_text()).get("settings_sha256")
    except (OSError, ValueError):
        recorded = None
    if recorded != s.digest():
        raise TutorError(
            "SETTINGS NOT READ: run `uv run tutor start` and read its output before continuing "
            "(SETTINGS.md is new or changed since the last start)."
        )
    return s
