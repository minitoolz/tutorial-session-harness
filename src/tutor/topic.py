"""Topic directory model: paths, topic.yaml, render order."""

from __future__ import annotations

import datetime as _dt
import re
import shutil
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import yaml

from .settings import Settings, TutorError

REQUIRED_PAGES = ("abstract.md", "intro.md", "contents.md", "glossary.md")
GLOSSARY = "glossary.md"
TOPIC_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
IMG_EXTS = ("png", "jpg", "jpeg", "svg", "pdf", "gif", "webp")


def default_order(pages: list[str]) -> list[str]:
    """abstract, intro, contents, extra pages A→Z, glossary last."""
    head = [p for p in ("abstract.md", "intro.md", "contents.md") if p in pages]
    rest = sorted(p for p in pages if p not in REQUIRED_PAGES)
    tail = [GLOSSARY] if GLOSSARY in pages else []
    return head + rest + tail


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

    def order(self) -> list[str]:
        return list(self.meta().get("order") or [])

    def set_order(self, order: list[str]) -> None:
        meta = self.meta()
        meta["order"] = order
        self.yaml_path.write_text(
            yaml.safe_dump(meta, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )


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
