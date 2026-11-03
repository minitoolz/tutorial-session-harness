"""Readability heuristics for tutorial prose (no LLM involved).

Flags: long sentences, long paragraphs, phrase-list hits, defensive hedges,
opaque index labels (E1/E2/E3), and terms used before they are defined.
Phrase lists: skills/clear-writing/phrases.yaml + skills.local/**/phrases.yaml.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import yaml

from . import mdscan
from .lint import Issue
from .settings import Settings
from .topic import GLOSSARY, Topic

ABBREV_RE = re.compile(r"\b(e\.g|i\.e|etc|vs|cf|et al|Fig|Eq|Sec|approx|resp)\.", re.IGNORECASE)
SENT_SPLIT_RE = re.compile(r"(?<=[.!?。？！])\s+")
CJK_RE = re.compile(r"[ᄀ-ᇿ぀-ヿ㄰-㆏一-鿿가-힯]")
LABEL_RE = re.compile(r"\b([A-Z][A-Za-z]{0,5})[-_]?(\d{1,2})\b")


def load_rules(root: Path) -> dict:
    rules: dict = {"phrases": [], "hedges": [], "label_allowlist": []}
    files = [root / "skills" / "clear-writing" / "phrases.yaml"]
    local = root / "skills.local"
    if local.is_dir():
        files += sorted(local.rglob("phrases.yaml"))
    for f in files:
        if not f.is_file():
            continue
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for key in rules:
            rules[key].extend(data.get(key) or [])
    rules["label_allowlist"] = {str(x) for x in rules["label_allowlist"]}
    return rules


def _is_cjk(s: str) -> bool:
    chars = [c for c in s if not c.isspace()]
    return bool(chars) and sum(bool(CJK_RE.match(c)) for c in chars) / len(chars) > 0.3


def _sentences(par: str) -> list[str]:
    protected = ABBREV_RE.sub(lambda m: m.group(0).replace(".", "\x00"), par)
    return [s.replace("\x00", ".").strip() for s in SENT_SPLIT_RE.split(protected) if s.strip()]


def _sentence_too_long(sent: str, limits: dict) -> str | None:
    if _is_cjk(sent):
        n = len([c for c in sent if not c.isspace()])
        if n > limits["max_sentence_chars_cjk"]:
            return f"{n} chars (limit {limits['max_sentence_chars_cjk']})"
    else:
        n = len(sent.split())
        if n > limits["max_sentence_words"]:
            return f"{n} words (limit {limits['max_sentence_words']})"
    return None


def _pattern_hits(page: str, text: str, entries: list[dict], tag: str) -> list[Issue]:
    issues = []
    compiled = []
    for e in entries:
        try:
            compiled.append((re.compile(e["pattern"], re.IGNORECASE), e))
        except (re.error, KeyError, TypeError):
            issues.append(Issue("warning", "phrases.yaml", 0, f"bad pattern entry: {e!r}"))
    for ln in mdscan.scan(text):
        if ln.kind == "blank":
            continue
        s = mdscan.strip_inline(ln.text)
        for rx, e in compiled:
            m = rx.search(s)
            if m:
                msg = f"[{tag}] '{m.group(0)}'"
                if e.get("why"):
                    msg += f" — {e['why']}"
                if e.get("suggest"):
                    msg += f" → {e['suggest']}"
                issues.append(Issue("warning", page, ln.no, msg))
    return issues


def _opaque_labels(page: str, text: str, allow: set[str]) -> list[Issue]:
    seen: dict[str, dict[str, int]] = defaultdict(dict)  # prefix -> {token: first line}
    for ln in mdscan.scan(text):
        if ln.kind == "blank":
            continue
        for m in LABEL_RE.finditer(mdscan.strip_inline(ln.text)):
            tok = m.group(0)
            if tok in allow or m.group(1) + m.group(2) in allow:
                continue
            seen[m.group(1)].setdefault(tok, ln.no)
    issues = []
    for prefix, toks in seen.items():
        if len(toks) >= 2:
            names = ", ".join(sorted(toks))
            first = min(toks.values())
            issues.append(Issue("warning", page, first,
                                f"[opaque-label] {names} — name compared items by what they are "
                                f"(e.g. {prefix}-conv, {prefix}-transformer), not by index"))
    return issues


def _structure(page: str, text: str, limits: dict) -> list[Issue]:
    issues = []
    for start, par in mdscan.paragraphs(text):
        clean = mdscan.strip_inline(par)
        sents = _sentences(clean)
        if len(sents) > limits["max_paragraph_sentences"]:
            issues.append(Issue("warning", page, start,
                                f"[long-paragraph] {len(sents)} sentences "
                                f"(limit {limits['max_paragraph_sentences']}) — split by idea"))
        for s in sents:
            why = _sentence_too_long(s, limits)
            if why:
                preview = s if len(s) <= 70 else s[:67] + "..."
                issues.append(Issue("warning", page, start,
                                    f"[long-sentence] {why}: \"{preview}\" — one idea per sentence"))
    return issues


def _undefined_terms(topic: Topic, order: list[str]) -> list[Issue]:
    """A term marked as defined (<dfn> / first **bold**) must not appear earlier in reading order."""
    issues = []
    pages = [pg for pg in order if pg not in ("abstract.md", GLOSSARY) and (topic.path / pg).is_file()]
    # Gather (page index, line, text) of prose, and definition sites.
    flow: list[tuple[int, int, str, str]] = []
    defs: dict[str, tuple[int, int, str]] = {}
    for pi, page in enumerate(pages):
        text = (topic.path / page).read_text(encoding="utf-8")
        for ln in mdscan.scan(text):
            if ln.kind != "blank":
                flow.append((pi, ln.no, page, ln.text))
        for line, term in mdscan.definitions(text):
            defs.setdefault(term.lower(), (pi, line, term))
    for key, (dpi, dline, term) in defs.items():
        boundary_end = "" if _is_cjk(term) else r"\b"
        rx = re.compile(r"(?<![\w])" + re.escape(term) + boundary_end, re.IGNORECASE)
        for pi, line, page, raw in flow:
            if (pi, line) >= (dpi, dline):
                break
            if rx.search(mdscan.strip_inline(raw)):
                issues.append(Issue("warning", page, line,
                                    f"[undefined-term] '{term}' is used here but defined later "
                                    f"({pages[dpi]}:{dline}) — define it on first use or reorder"))
                break
    return issues


def review(topic: Topic, settings: Settings, root: Path, only_page: str | None = None) -> list[Issue]:
    rules = load_rules(root)
    limits = settings.review_limits()
    order = topic.order() or topic.pages()
    pages = [only_page] if only_page else order
    issues: list[Issue] = []
    for page in pages:
        f = topic.path / page
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8")
        issues += _structure(page, text, limits)
        issues += _pattern_hits(page, text, rules["phrases"], "phrase")
        issues += _pattern_hits(page, text, rules["hedges"], "hedge")
        issues += _opaque_labels(page, text, rules["label_allowlist"])
    issues += [i for i in _undefined_terms(topic, order) if not only_page or i.file == only_page]
    issues.sort(key=lambda i: (order.index(i.file) if i.file in order else 99, i.line))
    return issues
