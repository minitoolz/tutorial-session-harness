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

# ── Readability limits used by `tutor review` (optional) ─────────────────────
review:
  max_sentence_words: 25
  max_sentence_chars_cjk: 60
  max_paragraph_sentences: 5
---

# Preferences (free text — the agent reads all of this)

## How I like explanations
- TODO: e.g. "Start with a concrete example, then the general rule."
- TODO: e.g. "Show the derivation step by step; don't skip algebra."
- TODO: e.g. "Prefer PyTorch for code."

## Notation
- TODO: e.g. "Vectors bold lowercase ($\mathbf{x}$), matrices bold uppercase."

## Things that confused me before
<!-- The agent appends here (after asking) when you say something was unclear. -->
