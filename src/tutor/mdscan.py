"""Light-weight Markdown scanning shared by lint and review.

Not a full parser: it only needs to tell prose apart from code, display math
and comments, and to strip inline code/math/tags from a prose line.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator

FENCE_RE = re.compile(r"^\s*(```|~~~)")
MATH_ENV_BEGIN = re.compile(r"\\begin\{(equation|align|gather|multline|eqnarray|split|cases)\*?\}")
MATH_ENV_END = re.compile(r"\\end\{(equation|align|gather|multline|eqnarray|split|cases)\*?\}")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
INLINE_MATH_RE = re.compile(r"(?<![\\$])\$(?!\$)(?:[^$\\]|\\.)+?\$")
TAG_RE = re.compile(r"<[^>]+>")
LINK_URL_RE = re.compile(r"\]\([^)]*\)")
DFN_RE = re.compile(r"<dfn>(.+?)</dfn>|\*\*([^*\n]{2,40}?)\*\*")


@dataclass
class Line:
    no: int          # 1-based line number
    text: str
    kind: str        # prose | heading | table | list | blank
    quote: bool = False  # inside a `>` note; `text` has the markers stripped


def scan(text: str) -> Iterator[Line]:
    """Yield the lines that a reader sees as text, skipping code/math/comments."""
    in_fence = in_dmath = in_env = in_comment = False
    for i, raw in enumerate(text.splitlines(), start=1):
        s = raw.strip()
        if in_comment:
            if "-->" in s:
                in_comment = False
            continue
        if in_fence:
            if FENCE_RE.match(raw):
                in_fence = False
            continue
        if in_env:
            if MATH_ENV_END.search(s):
                in_env = False
            continue
        if in_dmath:
            if s.endswith("$$"):
                in_dmath = False
            continue
        if FENCE_RE.match(raw):
            in_fence = True
            continue
        if s.startswith("<!--"):
            if "-->" not in s:
                in_comment = True
            continue
        if s.startswith("$$"):
            if not (len(s) > 2 and s.endswith("$$")):
                in_dmath = True
            continue
        if MATH_ENV_BEGIN.search(s):
            if not MATH_ENV_END.search(s):
                in_env = True
            continue
        quote = s.startswith(">")
        if quote:
            raw = re.sub(r"^\s*(>\s?)+", "", raw)
            s = raw.strip()
        if not s:
            yield Line(i, raw, "blank", quote)
        elif s.startswith("#"):
            yield Line(i, raw, "heading", quote)
        elif s.startswith("|"):
            yield Line(i, raw, "table", quote)
        elif re.match(r"^([-*+]|\d+[.)])\s", s):
            yield Line(i, raw, "list", quote)
        else:
            yield Line(i, raw, "prose", quote)


def strip_inline(s: str, keep_math: bool = False) -> str:
    s = INLINE_CODE_RE.sub(" ", s)
    if not keep_math:
        s = INLINE_MATH_RE.sub(" X ", s)
    s = LINK_URL_RE.sub("]", s)
    s = TAG_RE.sub(" ", s)
    return s


def paragraphs(text: str) -> Iterator[tuple[int, str]]:
    """Yield (first line number, joined text) for each prose paragraph / list item."""
    buf: list[str] = []
    start = 0
    for ln in scan(text):
        if ln.kind in ("prose",) and buf:
            buf.append(ln.text.strip())
            continue
        if buf:
            yield start, " ".join(buf)
            buf = []
        if ln.kind in ("prose", "list"):
            start = ln.no
            buf = [re.sub(r"^([-*+]|\d+[.)])\s+", "", ln.text.strip())]
    if buf:
        yield start, " ".join(buf)


def definitions(text: str) -> Iterator[tuple[int, str]]:
    """(line, term) for each term marked as defined: <dfn>term</dfn> or **term** (<= 4 words).

    Bold inside table rows (markdown or HTML cells) is a label, not a definition.
    """
    for ln in scan(text):
        if ln.kind in ("blank", "table", "heading"):
            continue
        is_cell = re.search(r"<t[dh][\s>]", ln.text) is not None
        for m in DFN_RE.finditer(ln.text):
            if is_cell and not m.group(1):
                continue
            term = (m.group(1) or m.group(2)).strip()
            if term and len(term.split()) <= 4:
                yield ln.no, term


def glossary_entries(text: str) -> list[tuple[int, str]]:
    """(line, term) for each pandoc definition-list term in glossary.md.

        Term
        :   Definition ...
    """
    lines = text.splitlines()
    out = []
    in_fence = False
    for i, line in enumerate(lines):
        if FENCE_RE.match(line):
            in_fence = not in_fence
        s = line.strip()
        if in_fence or not s or s.startswith((":", "#", "<!--", "-->")) or line.startswith((" ", "\t")):
            continue
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j < len(lines) and re.match(r"^\s{0,3}[:~]\s", lines[j]):
            term = TAG_RE.sub("", s).replace("**", "").replace("*", "").strip()
            out.append((i + 1, term))
    return out


def term_aliases(term: str) -> set[str]:
    """'어텐션 (attention)' / 'logit, score' → {'어텐션 (attention)', '어텐션', 'attention', ...}."""
    t = term.strip().lower()
    parts = {t}
    for p in re.split(r"[()/,;]", t):
        if p.strip():
            parts.add(p.strip())
    return parts
