---
name: onboarding
description: Interview the user about their background and preferences, and write SETTINGS.md.
when-to-use: `tutor start` prints ONBOARDING REQUIRED, or the user wants to update their background, language or PDF style.
---

# Onboarding interview

The point of this interview is so you write for **this** reader. Keep it short: one or two
rounds of questions, not a form. If your agent has a structured question tool, use it.
Otherwise ask in plain chat.

## 1. Ask (group the questions; skip what the user already told you)

About the reader:
- What is your main field or major? What do you do day to day? (→ `field`, `background`)
- What are you comfortable with? Which tools, theory or math? (→ `strong_in`, `math_level`)
- What feels shaky or unfamiliar? (→ `weak_in`)
- Which areas do you know well enough that analogies from them would help? (→ `familiar_domains`)
- Why do you want to learn this kind of material? What should you be able to do afterwards? (→ `goals`)

About the output:
- Which language should the tutorial be written in? (→ `language`; for ko/ja/zh also choose a
  `CJKmainfont` from `fc-list :lang=ko family`)
- Which PDF style: `article` (clean, default), `paper` (academic look, running header) or
  `notes` (sans-serif, relaxed)? Font size and paper size?
- Any explanation preferences: example-first or definition-first, how much code and which
  framework, notation habits?

## 2. Write SETTINGS.md

- If SETTINGS.md doesn't exist, copy `SETTINGS.example.md` to `SETTINGS.md`. Otherwise edit
  the existing file. Never edit SETTINGS.example.md for a user.
- Fill every `audience` field. Use the user's own words where you can. Remove every `TODO`.
- Put the free-text preferences in the body sections.
- Run `uv run tutor settings`. It checks the style, the fonts and xelatex. Fix the problems
  together with the user.
- Run `uv run tutor start` again. It must end with `OK: settings acknowledged`.

## 3. Keep it current

During later sessions, when you learn something durable about the reader, ask first: "Should I
note in your settings that you'd like X explained from scratch?" If they agree, update `audience`
or "Things that confused me before" and re-run `uv run tutor start`. Examples of durable facts:
they didn't know what a Jacobian is, or they prefer JAX.

When the user says an **expression** confused them, also add it to
`skills.local/clear-writing/phrases.yaml` (create it if needed; same format as
`skills/clear-writing/phrases.yaml`), so `tutor review` flags it from then on.
