"""Structural checks for a topic directory."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import mdscan
from .topic import GLOSSARY, IMG_EXTS, REQUIRED_PAGES, Topic

MD_IMG_RE = re.compile(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)")
HTML_SRC_RE = re.compile(r"""\bsrc\s*=\s*["']([^"']+)["']""")
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(\s*<?([^)\s>]+)")
INCLUDE_RE = re.compile(r"""\binclude\s*=\s*["']([^"']+)["']""")


@dataclass
class Issue:
    level: str   # error | warning
    file: str
    line: int
    msg: str

    def __str__(self) -> str:
        loc = f"{self.file}:{self.line}" if self.line else self.file
        return f"{self.level.upper():7} {loc}  {self.msg}"


def _local(ref: str) -> bool:
    return not re.match(r"^[a-z]+:", ref) and not ref.startswith("#")


def references(text: str) -> list[tuple[int, str, str]]:
    """(line, kind, path) for every local image/code reference in a page."""
    out = []
    for i, line in enumerate(text.splitlines(), start=1):
        for m in MD_IMG_RE.finditer(line):
            out.append((i, "img", m.group(1)))
        for m in HTML_SRC_RE.finditer(line):
            out.append((i, "img", m.group(1)))
        for m in INCLUDE_RE.finditer(line):
            out.append((i, "code", m.group(1)))
        for m in LINK_RE.finditer(line):
            if m.group(1).startswith("codes/"):
                out.append((i, "code", m.group(1)))
    return [r for r in out if _local(r[2])]


def _math_balance(page: str, text: str) -> list[Issue]:
    issues: list[Issue] = []
    in_fence = False
    dollars_open_at = 0
    for i, line in enumerate(text.splitlines(), start=1):
        if re.match(r"^\s*(```|~~~)", line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        s = re.sub(r"`[^`]*`", "", line).replace(r"\$", "")
        n_display = s.count("$$")
        if n_display % 2:
            dollars_open_at = 0 if dollars_open_at else i
        single = s.replace("$$", "").count("$")
        if single % 2 and not dollars_open_at:
            issues.append(Issue("error", page, i, "unbalanced inline math '$' on this line"))
    if dollars_open_at:
        issues.append(Issue("error", page, dollars_open_at, "display math '$$' opened but never closed"))
    return issues


def _glossary(topic: Topic, pages: list[str]) -> list[Issue]:
    """glossary.md must define every term the pages mark as defined, and nothing unused."""
    gpath = topic.path / GLOSSARY
    if not gpath.is_file():
        return []
    issues: list[Issue] = []
    entries = mdscan.glossary_entries(gpath.read_text(encoding="utf-8"))
    if not entries:
        issues.append(Issue("warning", GLOSSARY, 0,
                            "no entries yet (format: `Term` line, then `:   definition`)"))
    known: dict[str, tuple[int, str]] = {}
    for line, term in entries:
        if term.lower() in known:
            issues.append(Issue("error", GLOSSARY, line, f"duplicate entry '{term}'"))
        known[term.lower()] = (line, term)
    aliases = {a for t in known for a in mdscan.term_aliases(t)}

    body = ""
    for page in pages:
        if page == GLOSSARY:
            continue
        text = (topic.path / page).read_text(encoding="utf-8")
        body += "\n" + mdscan.strip_inline(text, keep_math=True).lower()
        for line, term in mdscan.definitions(text):
            if term.lower() not in aliases:
                issues.append(Issue("warning", page, line,
                                    f"'{term}' is marked as a definition but has no entry in {GLOSSARY}"))
    for key, (line, term) in known.items():
        if not any(a in body for a in mdscan.term_aliases(term)):
            issues.append(Issue("warning", GLOSSARY, line, f"'{term}' is not used in any page"))
    return issues


def lint(topic: Topic) -> list[Issue]:
    issues: list[Issue] = []
    p = topic.path

    for req in REQUIRED_PAGES:
        if not (p / req).is_file():
            issues.append(Issue("error", req, 0, "required page is missing"))
    for d in ("imgs", "codes"):
        if not (p / d).is_dir():
            issues.append(Issue("error", d + "/", 0, "required directory is missing"))

    if not topic.yaml_path.is_file():
        issues.append(Issue("error", "topic.yaml", 0, "missing (run `uv run tutor order <topic> --reset`)"))
    pages = topic.pages()
    order = topic.order()
    for entry in order:
        if entry not in pages:
            issues.append(Issue("error", "topic.yaml", 0, f"order lists '{entry}' but the file does not exist"))
    for page in pages:
        if page not in order:
            issues.append(Issue("error", "topic.yaml", 0,
                                f"'{page}' exists but is not in order (add it, or move it out of the topic root)"))
    if len(set(order)) != len(order):
        issues.append(Issue("error", "topic.yaml", 0, "order contains duplicates"))

    stems = {Path(pg).stem for pg in pages}
    img_re = re.compile(r"^([a-z0-9]+(?:-[a-z0-9]+)*?)-([a-z0-9]+(?:-[a-z0-9]+)*)\.(" + "|".join(IMG_EXTS) + r")$")
    imgs_dir = p / "imgs"
    img_files = sorted(f for f in imgs_dir.rglob("*") if f.is_file() and f.name != ".gitkeep") if imgs_dir.is_dir() else []
    for f in img_files:
        rel = f.relative_to(p).as_posix()
        if f.parent != imgs_dir:
            issues.append(Issue("error", rel, 0, "images must sit directly in imgs/ (no subdirectories)"))
            continue
        m = img_re.match(f.name)
        page_ok = m and any(f.name.startswith(stem + "-") for stem in stems)
        if not page_ok:
            issues.append(Issue("error", rel, 0,
                                f"name must be {{pagename}}-{{short-name}}.{{ext}} with pagename in "
                                f"{sorted(stems)} (lowercase, kebab-case)"))
        elif f.suffix.lower() in (".gif", ".webp"):
            issues.append(Issue("warning", rel, 0, f"{f.suffix} cannot be embedded in PDF; prefer png/jpg/pdf"))
        elif f.suffix.lower() == ".svg":
            issues.append(Issue("warning", rel, 0, "svg needs `rsvg-convert` on PATH for PDF builds; prefer pdf/png"))

    referenced: set[str] = set()
    for page in pages:
        text = (p / page).read_text(encoding="utf-8")
        for line, kind, ref in references(text):
            ref_clean = ref.split("#")[0]
            referenced.add(Path(ref_clean).as_posix())
            target = (p / ref_clean)
            if not target.exists():
                issues.append(Issue("error", page, line, f"referenced {kind} '{ref}' does not exist"))
            elif kind == "img" and not ref_clean.startswith("imgs/"):
                issues.append(Issue("error", page, line, f"image '{ref}' must live in imgs/"))
            elif kind == "img":
                stem = Path(page).stem
                if not Path(ref_clean).name.startswith(stem + "-"):
                    issues.append(Issue("warning", page, line,
                                        f"image '{ref}' is used in {page} but named for another page"))
        issues.extend(_math_balance(page, text))

    for f in img_files:
        rel = f.relative_to(p).as_posix()
        if rel not in referenced:
            issues.append(Issue("warning", rel, 0, "image is not referenced by any page"))

    issues.extend(_glossary(topic, pages))
    return issues
