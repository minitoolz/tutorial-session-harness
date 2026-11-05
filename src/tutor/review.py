"""Readability heuristics for tutorial prose (no LLM involved).

Flags: long sentences, long paragraphs, sentences not linked to the one before
(no connective), phrase-list hits, defensive hedges, opaque index labels
(E1/E2/E3), terms used before they are defined, and single-letter math
symbols a section uses without ever saying what they are.
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
# HTML blocks hold captions and cells, not running prose; inline tags like <dfn> don't count.
HTML_BLOCK_RE = re.compile(r"^<(figure|figcaption|img|table|thead|tbody|tr|td|th|details|summary|div)\b", re.I)
LABEL_RE = re.compile(r"\b([A-Z][A-Za-z]{0,5})[-_]?(\d{1,2})\b")


def load_rules(root: Path) -> dict:
    rules: dict = {"phrases": [], "hedges": [], "connectives": [], "label_allowlist": []}
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
        if HTML_BLOCK_RE.match(par.lstrip()):
            continue  # table cells and captions are not running prose
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


def _compile(entries: list[dict]) -> list[re.Pattern]:
    out = []
    for e in entries:
        try:
            out.append(re.compile(e["pattern"], re.IGNORECASE))
        except (re.error, KeyError, TypeError):
            pass  # _pattern_hits already reports bad entries for phrases/hedges
    return out


def _cohesion(page: str, text: str, limits: dict, connectives: list[re.Pattern]) -> list[Issue]:
    """Flag a paragraph where too many sentences in a row have no link to the one before.

    A link is a connective ("so", "however", "그래서", "반면") or a reference back ("this",
    "이 방법은"). A missing link usually means the two sentences are not cohesive: the fix is to
    restructure (reorder, split the paragraph, add the missing step), not to paste in "또한".
    """
    issues = []
    limit = limits["max_unlinked_sentences"]
    if not connectives or limit is None or limit < 0:
        return issues
    for start, par in mdscan.paragraphs(text):
        if HTML_BLOCK_RE.match(par.lstrip()):
            continue
        sents = _sentences(mdscan.strip_inline(par))
        run: list[str] = []
        for s in sents[1:]:
            if any(rx.search(s) for rx in connectives):
                run = []
                continue
            run.append(s)
            if len(run) == limit + 1:
                first = run[0] if len(run[0]) <= 50 else run[0][:47] + "..."
                issues.append(Issue("warning", page, start,
                                    f"[low-cohesion] {len(run)}+ sentences in a row with no link to the "
                                    f"one before, from \"{first}\" — open each with a connective that "
                                    f"states the relation (so / but / for example / 그래서 / 반면 / 예를 "
                                    f"들어); if none fits, restructure the paragraph"))
                break  # one flag per paragraph
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


# Subject-predicate agreement audit. Whether "A는 B다" makes sense (a decision is not a distance)
# is a question of meaning that no regex can answer, so this only lists the copula sentences
# ("A is B") for the writer to check one by one; it raises no warnings.
HANGUL_RE = re.compile(r"[가-힣]")
KO_SUBJ_RE = re.compile(r"(?:^|\s)([^\s,()]+?)\)?(?:은|는)(?=\s)")
KO_SUBJ_SKIP_RE = re.compile(r"(에서|에게|에도|에|으로|로|까지|부터|보다|처럼|하|되|있|없|않)$")  # locatives, verb adnominals
KO_COPULA_RE = re.compile(
    r"([^\s,()]+?(?:이다|이므로|이고|이며|이지만|인데|였다|이었다|이라서|이라))(?=[\s,.]|$)"
    r"|([A-Za-z0-9%)\]]+(?:다|였다|므로|이므로|고|며|지만|인데))(?=[\s,.]|$)"
)
EN_COPULA_RE = re.compile(
    r"\b([A-Za-z][\w-]*)\s+(?:is|are|was|were)\s+(?:not\s+)?(?:(?:an?|the)\s+)?([A-Za-z][\w-]*)", re.I
)


def agreement_pairs(topic: Topic, only_page: str | None = None) -> list[Issue]:
    """List each copula sentence as 'subject → complement' for a by-meaning check."""
    order = topic.order() or topic.pages()
    pages = [only_page] if only_page else [p for p in order if p != GLOSSARY]
    out: list[Issue] = []
    for page in pages:
        f = topic.path / page
        if not f.is_file():
            continue
        for start, par in mdscan.paragraphs(f.read_text(encoding="utf-8")):
            if HTML_BLOCK_RE.match(par.lstrip()):
                continue
            for s in _sentences(mdscan.strip_inline(par)):
                pair = None
                if HANGUL_RE.search(s):  # mixed Korean/English sentences are Korean here
                    for ms in KO_SUBJ_RE.finditer(s):
                        subj = ms.group(1).strip("*")
                        if KO_SUBJ_SKIP_RE.search(subj) or (len(subj) == 1 and CJK_RE.match(subj)):
                            continue
                        mc = KO_COPULA_RE.search(s, ms.end())
                        if mc:
                            pair = (subj, mc.group(1) or mc.group(2))
                        break
                else:
                    me = EN_COPULA_RE.search(s)
                    if me:
                        pair = (me.group(1), me.group(2))
                if pair:
                    preview = s if len(s) <= 90 else s[:87] + "..."
                    out.append(Issue("info", page, start,
                                     f"[agreement] {pair[0]} → {pair[1]}: \"{preview}\""))
    return out


# Single-letter symbols ($\tau$, $K$, $\mathbf{x}$) must be explained at least once in the
# section page that uses them, so a reader who jumps into the section can read it alone.
# "Explained" is judged from the words around the math span:
#   threshold $\tau$ / 대문자($\mathbf{I}$)      a noun right before it (apposition)
#   $K$는 ... / $\mu$과 $\sigma$은 ...           the symbol is the topic of the sentence
#   ...를 $\mathbf{m}_i$, ...를 $\bar m$라 하자    named in a "let ... be" sentence
#   $k$번째 / $K$개 / $n$차원 / $H \times W$ 크기   a counting or size word right after it
#   크기는 $H \times W \times d$이다               it is the value of a described quantity
_GREEK = ("alpha beta gamma delta epsilon varepsilon zeta eta theta vartheta iota kappa lambda mu nu "
          "xi rho sigma tau upsilon phi varphi chi psi omega Gamma Delta Theta Lambda Xi Pi Sigma Phi "
          "Psi Omega").split()
_DECOR = r"(?:mathbf|boldsymbol|bm|symbf|hat|bar|tilde|mathcal|vec|mathit)"
_ATOM_RE = re.compile(
    r"\\" + _DECOR + r"\{\s*(?:\\[A-Za-z]+|[A-Za-z])\s*\}"
    r"|\\(?:" + "|".join(_GREEK) + r")(?![A-Za-z])"
    r"|(?<![\\A-Za-z])[A-Za-z](?![A-Za-z])")
_MATH_DROP_RE = re.compile(r"\\(?:text|operatorname|mathrm|mathbb|label|eqref|ref)\{[^{}]*\}")
_SUBSUP_RE = re.compile(r"[_^](?:\{(?:[^{}]|\{[^{}]*\})*\}|\\[A-Za-z]+|.)")
_SIMPLE_REST_RE = re.compile(r"^(?:[\s,()\d]|\\times|\\dots|\\ldots|\\cdots|\;|\\,)*$")
_PARTICLE_END_RE = re.compile(r"(은|는|이|가|을|를|에|의|로|와|과|도|만|면|고|며|서|며)$")
_PREV_WORD_RE = re.compile(r"([A-Za-z가-힣][\w가-힣\-]*)\s?\(?$")
_PREV_STOP = {"이때", "여기서", "또", "즉", "그리고", "반면", "및", "또는", "그래서", "따라서", "다만",
              "먼저", "이", "그", "예", "예를", "들어", "그러면", "만약", "각각", "모두"}
_NAMING_RE = re.compile(r"^(?:이?라\s*(?:하|부르|두|고)|로\s*(?:쓰|쓴|두|둔|표기|나타))")
_COUNT_RE = re.compile(r"^\s?(?:번째|개|차원|크기|배|장|단계|번)")
_CHAIN_RE = re.compile(r"^\s*(?:과|와|,)\s*$")


def _symbol_atoms(tex: str) -> tuple[list[str], bool]:
    """Single-letter symbols in a math span (sub/superscripts dropped), and whether the span
    is just those symbols (a tuple or a product like H \times W) rather than an expression."""
    t = _SUBSUP_RE.sub(" ", _MATH_DROP_RE.sub(" ", tex))
    atoms = [re.sub(r"\s+", "", m.group(0)) for m in _ATOM_RE.finditer(t)]
    if "e^" in tex.replace(" ", ""):
        atoms = [a for a in atoms if a != "e"]  # Euler's number
    simple = bool(_SIMPLE_REST_RE.match(_ATOM_RE.sub("", t)))
    return atoms, simple


def _undefined_symbols(page: str, text: str) -> list[Issue]:
    first_use: dict[str, int] = {}
    explained: set[str] = set()
    for ln in mdscan.scan(text):
        if ln.kind in ("blank", "heading", "table"):
            continue
        line = ln.text
        spans = list(mdscan.INLINE_MATH_RE.finditer(line))
        info = [_symbol_atoms(m.group(0)[1:-1]) for m in spans]
        for atoms, _ in info:
            for a in atoms:
                first_use.setdefault(a, ln.no)
        for sent_start, sent in _sentence_spans(line):
            idx = [k for k, m in enumerate(spans) if sent_start <= m.start() < sent_start + len(sent)]
            naming = any(_NAMING_RE.match(line[spans[k].end():]) for k in idx)
            for pos, k in enumerate(idx):
                m, (atoms, simple) = spans[k], info[k]
                if not atoms:
                    continue
                targets = atoms if simple else atoms[:1]
                before, after = line[:m.start()], line[m.end():]
                ok = False
                # topic of the sentence, possibly the last of a chain "$a$과 $b$은"
                j = pos
                while j + 1 < len(idx) and _CHAIN_RE.match(line[spans[idx[j]].end():spans[idx[j + 1]].start()]):
                    j += 1
                if re.match(r"^(?:은|는)\s", line[spans[idx[j]].end():]):
                    ok = True
                if _NAMING_RE.match(after) or (naming and re.search(r"(?:을|를)\s$", before)):
                    ok = True
                if _COUNT_RE.match(after):
                    ok, targets = True, atoms
                if re.search(r"(?:은|는)\s$", before) and re.match(r"^(?:이)?(?:다|고|며|므로)(?:\s|[.,]|$)", after):
                    ok, targets = True, atoms
                w = _PREV_WORD_RE.search(before)
                if w and w.group(1) not in _PREV_STOP and not _PARTICLE_END_RE.search(w.group(1)):
                    ok = True
                if ok:
                    explained.update(targets)
    issues = []
    for sym, line in sorted(first_use.items(), key=lambda kv: kv[1]):
        if sym not in explained:
            issues.append(Issue("warning", page, line,
                                f"[undefined-symbol] ${sym}$ is never said in words in this section "
                                f"— explain it once here, e.g. \"threshold $\\tau$\" or \"$K$는 ...의 수다\""))
    return issues


def _sentence_spans(line: str) -> list[tuple[int, str]]:
    out, pos = [], 0
    for sent in _sentences(line):
        start = line.find(sent, pos)
        if start < 0:
            start = pos
        out.append((start, sent))
        pos = start + len(sent)
    return out or [(0, line)]


def review(topic: Topic, settings: Settings, root: Path, only_page: str | None = None) -> list[Issue]:
    rules = load_rules(root)
    limits = settings.review_limits()
    connectives = _compile(rules["connectives"])
    order = topic.order() or topic.pages()
    pages = [only_page] if only_page else order
    issues: list[Issue] = []
    for page in pages:
        f = topic.path / page
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8")
        issues += _structure(page, text, limits)
        if page != GLOSSARY:  # definition lists are reference entries, not running prose
            issues += _cohesion(page, text, limits, connectives)
        issues += _pattern_hits(page, text, rules["phrases"], "phrase")
        issues += _pattern_hits(page, text, rules["hedges"], "hedge")
        issues += _opaque_labels(page, text, rules["label_allowlist"])
        if page != GLOSSARY:
            issues += _undefined_symbols(page, text)
    issues += [i for i in _undefined_terms(topic, order) if not only_page or i.file == only_page]
    issues.sort(key=lambda i: (order.index(i.file) if i.file in order else 99, i.line))
    return issues
