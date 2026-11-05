"""One written form per technical term, shared by every topic.

terms.yaml (repo root, the user's file, gitignored) maps the form to write to the
forms that must not appear, in any language:

    layer: [neural network layer, 층, 레이어, couche]
    Schicht: [layer]
    re-ranking: [reranking, re:\bre ranking\b]

Any avoided form in a page (outside code and math) is a lint error.

Matching is language-neutral. In scripts that separate words with spaces (Latin, Cyrillic,
Greek, Hangul, ...) a form matches at the start of a word and may run on into it, which
catches plurals, inflections and attached particles (layers, Schichten, 레이어는) without
matching inside other words (층 does not match 계층). In scripts written without spaces
(Han, kana, Thai, ...) a form matches anywhere. Case is ignored. An entry that starts with
`re:` is a Python regex, for when that rule is too loose.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import yaml

from . import mdscan
from .settings import TutorError

TERMS_FILE = "terms.yaml"
UNSPACED_SCRIPTS = ("CJK", "HIRAGANA", "KATAKANA", "THAI", "LAO", "KHMER", "MYANMAR", "TIBETAN")


@dataclass
class Hit:
    line: int
    found: str
    canonical: str


def load(root: Path) -> dict[str, list[str]]:
    """{canonical: [avoided forms]}; empty when terms.yaml doesn't exist."""
    f = root / TERMS_FILE
    if not f.is_file():
        return {}
    try:
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise TutorError(f"{TERMS_FILE} is not valid YAML: {e}") from e
    if not isinstance(data, dict):
        raise TutorError(f"{TERMS_FILE} must map each term to a list of forms to avoid.")
    out: dict[str, list[str]] = {}
    for canon, avoid in data.items():
        if avoid is None:
            avoid = []
        if isinstance(avoid, str):
            avoid = [avoid]
        if not isinstance(avoid, list):
            raise TutorError(f"{TERMS_FILE}: '{canon}' must map to a list, e.g. {canon}: [a, b]")
        out[str(canon).strip()] = [str(a).strip() for a in avoid if str(a).strip()]
    return out


def problems(terms: dict[str, list[str]]) -> list[str]:
    """Contradictions inside terms.yaml itself."""
    out = []
    canon_lower = {c.lower(): c for c in terms}
    owner: dict[str, str] = {}
    for canon, avoid in terms.items():
        for a in avoid:
            key = a.lower()
            if key in canon_lower:
                out.append(f"'{a}' is both a term to write and a form to avoid (under '{canon}')")
            if key in owner and owner[key] != canon:
                out.append(f"'{a}' is listed under both '{owner[key]}' and '{canon}'")
            owner[key] = canon
    return out


def _unspaced(ch: str) -> bool:
    return unicodedata.name(ch, "").startswith(UNSPACED_SCRIPTS)


def _pattern(form: str) -> str:
    """Regex for one form (see the module docstring for the rule)."""
    if form.startswith("re:"):
        return form[3:]
    body = r"\s+".join(re.escape(w) for w in form.split())
    left = "" if _unspaced(form[0]) else r"(?<![\w])"
    return left + body + r"\w*" if not _unspaced(form[-1]) else left + body


def compile_terms(terms: dict[str, list[str]]):
    """[(regex, canonical, is_avoided)], longest form first.

    Canonical forms are in the list too, so that a canonical form containing an avoided one
    ("layer norm" vs avoided "layer") is consumed first, and an avoided form containing a
    canonical one ("neural network layer" vs "layer") still wins over it."""
    forms = [(a, c, True) for c, al in terms.items() for a in al]
    forms += [(c, c, False) for c in terms]
    forms.sort(key=lambda x: -len(x[0]))
    out = []
    for form, canon, avoided in forms:
        try:
            out.append((re.compile(_pattern(form), re.IGNORECASE), canon, avoided))
        except re.error as e:
            raise TutorError(f"{TERMS_FILE}: bad regex '{form}' under '{canon}': {e}") from e
    return out


def check_text(text: str, compiled) -> list[Hit]:
    hits: list[Hit] = []
    for ln in mdscan.scan(text):
        if ln.kind == "blank":
            continue
        s = mdscan.strip_inline(ln.text)
        for pattern, canon, avoided in compiled:
            if avoided:
                hits += [Hit(ln.no, m.group(0), canon) for m in pattern.finditer(s)]
            s = pattern.sub(lambda m: "\x00" * len(m.group(0)), s)
    return sorted(hits, key=lambda h: h.line)
