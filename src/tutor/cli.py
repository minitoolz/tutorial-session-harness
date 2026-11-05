"""`tutor` command-line entry point. Every agent drives the harness through this."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys

from . import build as build_mod
from . import migrate as migrate_mod
from . import settings as settings_mod
from . import topic as topic_mod
from .lint import lint
from .review import review
from .settings import TutorError

RULES_SUMMARY = """\
- Follow SETTINGS.md: write for the `audience` it describes, in its `language`.
- Topic data lives only in topics/<topic>/: abstract.md, intro.md, index.md, glossary.md, section pages,
  topic.yaml (title/author/date), imgs/{pagename}-{short-name}.{ext}, codes/.
- index.md is the table of contents: a numbered list linking every section page in reading order.
  It sets the PDF order (abstract, intro, sections, glossary). Keep it current.
- When a section page changes, reconcile index.md, intro.md, abstract.md and glossary.md in the same turn.
- Write by skills/clear-writing/SKILL.md; end each turn with `uv run tutor review <topic>`
  (fix the flags) and `uv run tutor lint <topic>` (must pass).
- Full rules: AGENTS.md. Workflows: skills/<name>/SKILL.md."""


def _print_issues(issues, header: str) -> tuple[int, int]:
    errors = sum(i.level == "error" for i in issues)
    warnings = len(issues) - errors
    print(f"== {header}: {errors} error(s), {warnings} warning(s)")
    for i in issues:
        print(i)
    return errors, warnings


def cmd_start(root, args) -> int:
    s = settings_mod.load(root)
    print("== tutor start")
    if not s.exists:
        print("!! ONBOARDING REQUIRED: SETTINGS.md does not exist.")
        print("   Follow skills/onboarding/SKILL.md: interview the user, write SETTINGS.md")
        print("   (based on SETTINGS.example.md), then run `uv run tutor start` again.")
        print("   If you have a tool that asks the user questions (e.g. AskUserQuestion),")
        print("   use it for the background survey.\n")
        print("--- SETTINGS.example.md (template, NOT the user's settings) ---")
        example = root / settings_mod.EXAMPLE_FILE
        print(example.read_text(encoding="utf-8") if example.is_file() else "(missing)")
        return 2
    print(f"--- {settings_mod.SETTINGS_FILE} (read all of it; it overrides skill defaults) ---")
    print(s.raw.rstrip())
    print("--- end of SETTINGS.md ---\n")
    if s.onboarding_required:
        print("!! ONBOARDING REQUIRED: audience fields missing or TODO: "
              + ", ".join(s.missing_audience()))
        print("   Follow skills/onboarding/SKILL.md, update SETTINGS.md, then run `uv run tutor start`.")
        print("   If you have a tool that asks the user questions (e.g. AskUserQuestion),")
        print("   use it for the background survey.")
        return 2
    settings_mod.write_stamp(root, s)
    topics = topic_mod.list_topics(root)
    print("--- topics ---")
    if not topics:
        print("(none yet — `uv run tutor new <kebab-name>`)")
    for name in topics:
        t = topic_mod.Topic(root, name)
        print(f"- {name}: {t.meta().get('title', '')!s}  [sections: {', '.join(t.sections()) or '(none)'}]")
    print("\n--- rules ---")
    print(RULES_SUMMARY)
    print("\nOK: settings acknowledged for this session.")
    return 0


def cmd_new(root, args) -> int:
    s = settings_mod.gate(root)
    t = topic_mod.create(root, args.name, s, title=args.title)
    print(f"Created {t.path.relative_to(root)}/")
    print("Next: interview the user about this topic, then draft index.md (section list) → intro.md →")
    print("section pages (+ glossary.md) → abstract.md")
    print("(see skills/new-topic/SKILL.md).")
    return 0


def cmd_lint(root, args) -> int:
    s = settings_mod.gate(root)
    t = topic_mod.get(root, args.topic)
    errors, _ = _print_issues(lint(t), f"lint {t.name}")
    if not args.no_review:
        rv = review(t, s, root)
        print(f"   (+ {len(rv)} readability warning(s); see `uv run tutor review {t.name}`)")
    return 1 if errors else 0


def cmd_review(root, args) -> int:
    s = settings_mod.gate(root)
    t = topic_mod.get(root, args.topic)
    issues = review(t, s, root, only_page=args.page)
    _print_issues(issues, f"review {t.name}")
    return 1 if (issues and args.strict) else 0


def cmd_order(root, args) -> int:
    t = topic_mod.get(root, args.topic)
    for i, p in enumerate(t.order(), start=1):
        mark = "" if (t.path / p).is_file() else "   <-- missing"
        print(f"{i}. {p}{mark}")
    print("(set the section order by editing index.md)")
    return 0


def cmd_migrate(root, args) -> int:
    t = topic_mod.get(root, args.topic)
    for line in migrate_mod.migrate(t):
        print(line)
    print(f"Next: check index.md titles, then run `uv run tutor lint {t.name}`.")
    return 0


def cmd_build(root, args) -> int:
    s = settings_mod.gate(root)
    t = topic_mod.get(root, args.topic)
    errors = [i for i in lint(t) if i.level == "error"]
    if errors:
        _print_issues(errors, f"lint {t.name}")
        raise TutorError("Fix lint errors before building.")
    out = build_mod.build(t, s, style=args.style, html=args.html)
    print(f"Built {out.relative_to(root)}")
    return 0


def cmd_settings(root, args) -> int:
    s = settings_mod.load(root)
    if not s.exists:
        raise TutorError("SETTINGS.md does not exist (see skills/onboarding/SKILL.md).")
    problems: list[str] = []
    notes: list[str] = []
    if s.missing_audience():
        problems.append(f"audience incomplete: {', '.join(s.missing_audience())}")
    if s.style not in build_mod.styles():
        problems.append(f"style '{s.style}' unknown; available: {', '.join(build_mod.styles())}")
    if not build_mod.xelatex_available():
        problems.append("xelatex not on PATH (install MacTeX / TeX Live)")
    fonts = {k: s.data.get(k) for k in ("mainfont", "sansfont", "monofont", "mathfont", "CJKmainfont") if s.data.get(k)}
    if fonts:
        if shutil.which("fc-list"):
            installed = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True).stdout
            families = {f.strip() for line in installed.splitlines() for f in line.split(",")}
            for key, fam in fonts.items():
                if fam not in families:
                    problems.append(f"{key}: font '{fam}' not installed (see `fc-list : family`)")
        else:
            notes.append("fc-list not found; font check skipped")
    lang = str(s.data.get("language") or s.data.get("lang") or "")
    if lang[:2] in build_mod.CJK_LANGS and not s.data.get("CJKmainfont"):
        problems.append(f"language '{lang}' needs CJKmainfont")
    for n in notes:
        print(f"note: {n}")
    if problems:
        for p in problems:
            print(f"PROBLEM: {p}")
        return 1
    print("SETTINGS.md OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tutor", description="Tutorial co-writing harness.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("start", help="print SETTINGS.md + topics + rules; acknowledge settings (run first)")

    p = sub.add_parser("new", help="create topics/<name>/ from the template")
    p.add_argument("name")
    p.add_argument("--title")

    p = sub.add_parser("lint", help="check directory/naming/reference/math rules")
    p.add_argument("topic")
    p.add_argument("--no-review", action="store_true", help="skip the readability summary line")

    p = sub.add_parser("review", help="readability heuristics (file:line warnings)")
    p.add_argument("topic")
    p.add_argument("page", nargs="?", help="only this page, e.g. softmax.md")
    p.add_argument("--strict", action="store_true", help="exit 1 if anything is flagged")

    p = sub.add_parser("order", help="show the render order (set by index.md)")
    p.add_argument("topic")

    p = sub.add_parser("migrate", help="split an old contents.md into section pages + index.md")
    p.add_argument("topic")

    p = sub.add_parser("build", help="render the topic to PDF (or --html preview)")
    p.add_argument("topic")
    p.add_argument("--style", help=f"override SETTINGS style ({', '.join(build_mod.styles())})")
    p.add_argument("--html", action="store_true", help="HTML preview with MathML instead of PDF")

    sub.add_parser("settings", help="validate SETTINGS.md (keys, style, fonts, xelatex)")

    args = ap.parse_args(argv)
    handlers = {
        "start": cmd_start, "new": cmd_new, "lint": cmd_lint, "review": cmd_review,
        "order": cmd_order, "migrate": cmd_migrate, "build": cmd_build, "settings": cmd_settings,
    }
    try:
        root = settings_mod.find_root()
        return handlers[args.cmd](root, args)
    except TutorError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
