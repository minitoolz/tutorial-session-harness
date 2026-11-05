---
# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS.example.md — template for SETTINGS.md (your personal, gitignored copy).
# The agent fills this in with you during onboarding (skills/onboarding/SKILL.md).
# Values containing "TODO" count as unset: `tutor` refuses to work until the
# `audience` block is filled in.
# ─────────────────────────────────────────────────────────────────────────────

# ── Who is reading (the agent writes FOR this person) ────────────────────────
audience:
  field: "TODO"            # main field / major, e.g. "computer vision engineering"
  background: "TODO"       # degree, role, years, e.g. "MS in EE, 4 years as ML engineer"
  strong_in: []            # TODO e.g. ["PyTorch", "linear algebra", "CNNs"]
  weak_in: []              # TODO e.g. ["probability theory", "compilers"]
  math_level: "TODO"       # e.g. "comfortable with calculus & linear algebra, rusty on measure theory"
  familiar_domains: []     # where analogies may come from, e.g. ["image processing", "web backends"]
  goals: "TODO"            # why you are learning, e.g. "read diffusion-model papers without getting stuck"

# ── Writing ─────────────────────────────────────────────────────────────────
language: en               # writing + PDF language: en, ko, ja, zh, de, ...
author: ""                 # default author for new topics

# ── PDF typesetting (passed to pandoc / XeLaTeX) ────────────────────────────
style: article             # article | paper | notes   (src/tutor/data/pandoc/styles/)
fontsize: 11pt
# codefontsize: 9pt        # code blocks only (default: same as the body)
# tablefontsize: 8pt       # tables only (default: the style's own size)
papersize: a4
geometry: margin=2.5cm
linestretch: 1.25
numbersections: true
toc: false
colorlinks: true
# mainfont: "Latin Modern Roman"    # any installed font: `fc-list : family`
# sansfont: "Helvetica Neue"
# monofont: "Menlo"
# CJKmainfont: "Apple SD Gothic Neo" # REQUIRED for ko/ja/zh, e.g. "Noto Serif CJK KR"
# CJKoptions: [AutoFakeBold=2, AutoFakeSlant=0.15]  # for a CJK font with one weight (e.g. AppleMyungjo)

# ── Readability limits used by `tutor review` (optional) ─────────────────────
review:
  max_sentence_words: 50
  max_sentence_chars_cjk: 120
  max_paragraph_sentences: 5
  max_unlinked_sentences: 1    # sentences in a row with no connective; -1 turns the check off
---

# Preferences (free text — the agent reads all of this)

## How I like explanations
- TODO: e.g. "Start with a concrete example, then the general rule."
- TODO: e.g. "Show the derivation step by step; don't skip algebra."
- TODO: e.g. "Prefer PyTorch for code."

## Technical terms
<!-- How terms are written. Each term then gets ONE form, used in every topic (terms.yaml). -->
- TODO: e.g. "Keep English technical terms as they are (layer, fine-tuning); translate everyday words."
- TODO: e.g. "Use the established translation when one exists; otherwise the English term."

## Notation
- TODO: e.g. "Vectors bold lowercase ($\mathbf{x}$), matrices bold uppercase."

## Things that confused me before
<!-- The agent appends here (after asking) when you say something was unclear. -->
