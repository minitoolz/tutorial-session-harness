"""Topic directory model: paths, topic.yaml, index.md and the render order derived from it."""

from __future__ import annotations

import datetime as _dt
import re
import shutil
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import yaml

from .settings import Settings, TutorError

ABSTRACT, INTRO, INDEX, GLOSSARY = "abstract.md", "intro.md", "index.md", "glossary.md"
REQUIRED_PAGES = (ABSTRACT, INTRO, INDEX, GLOSSARY)
TOPIC_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
IMG_EXTS = ("png", "jpg", "jpeg", "svg", "pdf", "gif", "webp")
# One list item per section page: `1. [Title](page.md)` (or `- [Title](page.md)`).
INDEX_ITEM_RE = re.compile(r"^\s*(?:\d+[.)]|[-*+])\s+\[([^\]]*)\]\(\s*<?([^)\s>]+)>?\s*\)")


def parse_index(text: str) -> list[tuple[int, str, str]]:
    """(line, title, target) for each list item in index.md, skipping comments and code."""
    out: list[tuple[int, str, str]] = []
    in_comment = in_fence = False
    for i, raw in enumerate(text.splitlines(), start=1):
        s = raw.strip()
        if in_comment:
            in_comment = "-->" not in s
            continue
        if s.startswith("<!--"):
            in_comment = "-->" not in s
            continue
        if s.startswith("```") or s.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = INDEX_ITEM_RE.match(raw)
        if m:
            out.append((i, m.group(1).strip(), m.group(2)))
    return out


@dataclass
class Topic:
    root: Path
    name: str

    @property
    def path(self) -> Path:
        return self.root / "topics" / self.name

    @property
    def yaml_path(self) -> Path:
        return self.path / "topic.yaml"

    @property
    def build_dir(self) -> Path:
        return self.path / "build"

    def exists(self) -> bool:
        return self.path.is_dir()

    def pages(self) -> list[str]:
        """Markdown pages on disk (top level of the topic dir)."""
        return sorted(p.name for p in self.path.glob("*.md"))

    def meta(self) -> dict:
        if not self.yaml_path.is_file():
            return {}
        data = yaml.safe_load(self.yaml_path.read_text(encoding="utf-8")) or {}
        return data if isinstance(data, dict) else {}

    def index_entries(self) -> list[tuple[int, str, str]]:
        f = self.path / INDEX
        return parse_index(f.read_text(encoding="utf-8")) if f.is_file() else []

    def sections(self) -> list[str]:
        """Section pages in the order index.md lists them (duplicates dropped)."""
        seen: list[str] = []
        for _, _, target in self.index_entries():
            if target not in seen:
                seen.append(target)
        return seen

    def order(self) -> list[str]:
        """Render order: abstract, intro, the sections from index.md, glossary.

        index.md itself is the table of contents and is not rendered."""
        fixed = set(REQUIRED_PAGES)
        return [ABSTRACT, INTRO] + [p for p in self.sections() if p not in fixed] + [GLOSSARY]


def get(root: Path, name: str) -> Topic:
    t = Topic(root, name)
    if not t.exists():
        existing = ", ".join(list_topics(root)) or "(none)"
        raise TutorError(f"Topic '{name}' not found under topics/. Existing: {existing}")
    return t


def list_topics(root: Path) -> list[str]:
    d = root / "topics"
    return sorted(p.name for p in d.iterdir() if p.is_dir()) if d.is_dir() else []


def create(root: Path, name: str, settings: Settings, title: str | None = None) -> Topic:
    if not TOPIC_NAME_RE.match(name):
        raise TutorError(f"Topic name '{name}' must be kebab-case (e.g. 'attention-basics').")
    t = Topic(root, name)
    if t.exists():
        raise TutorError(f"Topic '{name}' already exists at {t.path}.")
    template = resources.files("tutor") / "data" / "templates" / "topic"
    with resources.as_file(template) as src:
        shutil.copytree(src, t.path)
    text = t.yaml_path.read_text(encoding="utf-8")
    text = (
        text.replace("__TITLE__", title or name.replace("-", " ").title())
        .replace("__AUTHOR__", settings.author)
        .replace("__DATE__", _dt.date.today().isoformat())
    )
    t.yaml_path.write_text(text, encoding="utf-8")
    return t
