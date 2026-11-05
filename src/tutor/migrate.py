"""Upgrade a topic from the old layout (one contents.md body + `order` in topic.yaml)
to the current one (index.md listing one page per section).

contents.md is split at its top-level `#` headings. Each section becomes a page
named after its heading id (`# Title {#sec:setup}` -> setup.md) or, failing that,
`section-N.md`. Images named `imgs/contents-*` are renamed for the page that uses them.
"""

from __future__ import annotations

import re

from .settings import TutorError
from .topic import INDEX, REQUIRED_PAGES, TOPIC_NAME_RE, Topic

OLD_BODY = "contents.md"
HEADING_RE = re.compile(r"^#\s+(.*?)\s*$")
ATTR_RE = re.compile(r"\s*\{[^}]*\}\s*$")
ID_RE = re.compile(r"\{[^}]*#([^\s}]+)[^}]*\}\s*$")
IMG_REF_RE = re.compile(r"imgs/contents-([A-Za-z0-9._-]+)")


def _split(text: str) -> list[tuple[str, str]]:
    """[(heading line, section text)] split at top-level `#` headings outside code/math/comments."""
    sections: list[list[str]] = []
    preamble: list[str] = []
    in_fence = in_dmath = in_comment = False
    for raw in text.splitlines(keepends=True):
        s = raw.strip()
        is_heading = False
        if in_comment:
            in_comment = "-->" not in s
        elif in_fence:
            in_fence = not (s.startswith("```") or s.startswith("~~~"))
        elif in_dmath:
            in_dmath = not s.endswith("$$")
        elif s.startswith("<!--"):
            in_comment = "-->" not in s
        elif s.startswith("```") or s.startswith("~~~"):
            in_fence = True
        elif s.startswith("$$"):
            in_dmath = not (len(s) > 2 and s.endswith("$$"))
        elif HEADING_RE.match(raw.rstrip("\n")):
            is_heading = True
        if is_heading:
            sections.append([raw])
        elif sections:
            sections[-1].append(raw)
        else:
            preamble.append(raw)
    if not sections:
        raise TutorError(f"{OLD_BODY} has no top-level `#` heading to split at.")
    # keep text before the first heading (minus template comments) with the first section
    pre = re.sub(r"<!--.*?-->", "", "".join(preamble), flags=re.S).strip()
    if pre:
        sections[0][1:1] = ["\n", pre + "\n"]
    return [(sec[0].strip(), "".join(sec).rstrip() + "\n") for sec in sections]


def _page_name(heading: str, n: int, taken: set[str]) -> str:
    m = ID_RE.search(heading)
    base = ""
    if m:
        base = m.group(1).split(":")[-1]
    else:
        base = HEADING_RE.match(heading).group(1)
    base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
    if not base or not TOPIC_NAME_RE.match(base):
        base = f"section-{n}"
    name, k = f"{base}.md", 2
    while name in taken or name in REQUIRED_PAGES:
        name, k = f"{base}-{k}.md", k + 1
    taken.add(name)
    return name


def _drop_order(yaml_text: str) -> str:
    """Remove the `order:` block and its old comment from topic.yaml, keeping the rest verbatim."""
    yaml_text = re.sub(r"(?m)^order:\s*\n(?:[ \t]+-[^\n]*\n?)*", "", yaml_text)
    yaml_text = re.sub(r"(?m)^order:\s*\[[^\]]*\]\s*\n?", "", yaml_text)
    yaml_text = yaml_text.replace(
        "# Filled in by `tutor new`. The agent keeps `order` up to date: it is the\n"
        "# exact sequence of pages rendered into the PDF.\n",
        "# Filled in by `tutor new`. The section order lives in index.md.\n",
    )
    return yaml_text


def migrate(topic: Topic) -> list[str]:
    p = topic.path
    old = p / OLD_BODY
    if not old.is_file():
        raise TutorError(f"{topic.name} has no {OLD_BODY}; nothing to migrate.")
    if (p / INDEX).is_file():
        raise TutorError(f"{topic.name} already has {INDEX}; migrate it by hand.")

    taken = set(topic.pages())
    plan = []  # (page, title, text)
    for n, (heading, text) in enumerate(_split(old.read_text(encoding="utf-8")), start=1):
        page = _page_name(heading, n, taken)
        title = ATTR_RE.sub("", HEADING_RE.match(heading).group(1))
        plan.append((page, title, text))

    for page, _, _ in plan:
        if (p / page).exists():
            raise TutorError(f"{page} already exists; rename it and run migrate again.")

    log: list[str] = []
    # images: rename contents-X for the first page that uses it
    renamed: dict[str, str] = {}
    stems = {}
    for page, _, text in plan:
        stem = page[:-3]
        for m in IMG_REF_RE.finditer(text):
            renamed.setdefault(m.group(1), f"{stem}-{m.group(1)}")
        stems[page] = stem
    imgs = p / "imgs"
    for f in sorted(imgs.glob("contents-*")) if imgs.is_dir() else []:
        rest = f.name[len("contents-"):]
        new = renamed.setdefault(rest, f"{plan[0][0][:-3]}-{rest}")
        if (imgs / new).exists():
            raise TutorError(f"imgs/{new} already exists; can't rename imgs/{f.name}.")

    for page, _, text in plan:
        text = IMG_REF_RE.sub(lambda m: "imgs/" + renamed[m.group(1)], text)
        (p / page).write_text(text, encoding="utf-8")
        log.append(f"wrote {page}")
    for f in sorted(imgs.glob("contents-*")) if imgs.is_dir() else []:
        new = renamed[f.name[len("contents-"):]]
        f.rename(imgs / new)
        log.append(f"renamed imgs/{f.name} -> imgs/{new}")

    index = "# Contents\n\n" + "".join(
        f"{i}. [{title}]({page})\n" for i, (page, title, _) in enumerate(plan, start=1)
    )
    (p / INDEX).write_text(index, encoding="utf-8")
    log.append(f"wrote {INDEX} ({len(plan)} sections)")

    if topic.yaml_path.is_file():
        topic.yaml_path.write_text(_drop_order(topic.yaml_path.read_text(encoding="utf-8")),
                                   encoding="utf-8")
        log.append("removed `order` from topic.yaml")
    old.unlink()
    log.append(f"removed {OLD_BODY}")
    return log
