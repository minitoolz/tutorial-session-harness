"""Structural checks for a topic directory."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import mdscan
from . import terms as terms_mod
from .topic import GLOSSARY, IMG_EXTS, INDEX, REQUIRED_PAGES, TOPIC_NAME_RE, Topic

MD_IMG_RE = re.compile(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)")
HTML_SRC_RE = re.compile(r"""\bsrc\s*=\s*["']([^"']+)["']""")
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(\s*<?([^)\s>]+)")
INCLUDE_RE = re.compile(r"""\binclude\s*=\s*["']([^"']+)["']""")
NOTE_MARK_RE = re.compile(r"^(\\\*|※)")  # a paragraph that opens with an escaped * or ※ is a side note
BARE_ENV_RE = re.compile(r"^\s*\\begin\{(equation|align|gather|multline|flalign|alignat|eqnarray)\*?\}")


@dataclass
class Issue:
    level: str   # error | warning | info
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
        if not dollars_open_at and not n_display and BARE_ENV_RE.match(s):
            issues.append(Issue("warning", page, i,
                                "display math environment outside $$; wrap it in $$ ... $$ so "
                                "Markdown previews render it (the build keeps it numbered)"))
        if n_display % 2:
            dollars_open_at = 0 if dollars_open_at else i
        single = s.replace("$$", "").count("$")
        if single % 2 and not dollars_open_at:
            issues.append(Issue("error", page, i, "unbalanced inline math '$' on this line"))
    if dollars_open_at:
        issues.append(Issue("error", page, dollars_open_at, "display math '$$' opened but never closed"))
    return issues


def _notes(page: str, text: str) -> list[Issue]:
    """Side notes (paragraphs opened by an escaped * or ※) must be `>` notes."""
    issues, prev_blank = [], True
    for ln in mdscan.scan(text):
        if prev_blank and ln.kind == "prose" and not ln.quote and NOTE_MARK_RE.match(ln.text.strip()):
            issues.append(Issue("warning", page, ln.no,
                                "side note outside a '>' block; start every line of the note with '>'"))
        prev_blank = ln.kind == "blank"
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


def _index(topic: Topic, pages: list[str]) -> list[Issue]:
    """index.md lists every section page once, in reading order, and nothing else."""
    if not (topic.path / INDEX).is_file():
        return []  # reported as a missing required page
    issues: list[Issue] = []
    entries = topic.index_entries()
    if not entries:
        issues.append(Issue("warning", INDEX, 0,
                            "lists no section pages yet (format: `1. [Title](page-name.md)`)"))
    seen: set[str] = set()
    for line, _title, target in entries:
        if target in seen:
            issues.append(Issue("error", INDEX, line, f"'{target}' is listed twice"))
            continue
        seen.add(target)
        if target in REQUIRED_PAGES:
            issues.append(Issue("error", INDEX, line,
                                f"'{target}' has a fixed place in the PDF; list only section pages"))
        elif "/" in target or not target.endswith(".md"):
            issues.append(Issue("error", INDEX, line,
                                f"'{target}' must be a .md page in the topic folder (no subfolders)"))
        elif target not in pages:
            issues.append(Issue("error", INDEX, line, f"'{target}' does not exist"))
        elif not TOPIC_NAME_RE.match(Path(target).stem):
            issues.append(Issue("error", INDEX, line,
                                f"'{target}': page names are lowercase kebab-case, e.g. softmax.md"))
    for page in pages:
        if page in REQUIRED_PAGES or page in seen:
            continue
        hint = (" Run `uv run tutor migrate <topic>` to split it into section pages."
                if page == "contents.md" else " Add it to index.md, or move it out of the topic root.")
        issues.append(Issue("error", page, 0, "page is not listed in index.md." + hint))
    return issues


def term_issues(topic: Topic, pages: list[str]) -> list[Issue]:
    """Every technical term in one written form, as terms.yaml (shared by all topics) sets it."""
    terms = terms_mod.load(topic.root)
    if not terms:
        return []
    issues = [Issue("error", terms_mod.TERMS_FILE, 0, msg) for msg in terms_mod.problems(terms)]
    compiled = terms_mod.compile_terms(terms)
    for page in pages:
        text = (topic.path / page).read_text(encoding="utf-8")
        for h in terms_mod.check_text(text, compiled):
            issues.append(Issue("error", page, h.line,
                                f"[term] '{h.found}': write '{h.canonical}' ({terms_mod.TERMS_FILE})"))
    return issues


def lint(topic: Topic) -> list[Issue]:
    issues: list[Issue] = []
    p = topic.path

    for req in REQUIRED_PAGES:
        if not (p / req).is_file():
            hint = (" (old layout: run `uv run tutor migrate <topic>`)"
                    if req == INDEX and (p / "contents.md").is_file() else "")
            issues.append(Issue("error", req, 0, "required page is missing" + hint))
    for d in ("imgs", "codes"):
        if not (p / d).is_dir():
            issues.append(Issue("error", d + "/", 0, "required directory is missing"))

    if not topic.yaml_path.is_file():
        issues.append(Issue("error", "topic.yaml", 0, "missing (title, subtitle, author, date)"))
    elif "order" in topic.meta():
        issues.append(Issue("warning", "topic.yaml", 0,
                            "`order` is no longer used: index.md sets the section order. Remove it."))
    pages = topic.pages()
    issues.extend(_index(topic, pages))

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
        issues.extend(_notes(page, text))

    for f in img_files:
        rel = f.relative_to(p).as_posix()
        if rel not in referenced:
            issues.append(Issue("warning", rel, 0, "image is not referenced by any page"))

    issues.extend(_glossary(topic, [pg for pg in pages if pg != INDEX]))
    issues.extend(term_issues(topic, pages))
    return issues
