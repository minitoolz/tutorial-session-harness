---
name: onboarding
description: Interview the user about their background and preferences, and write SETTINGS.md.
when-to-use: `tutor start` prints ONBOARDING REQUIRED, or the user wants to update their background, language or PDF style.
---

# Onboarding interview

The point of this interview is so you write for **this** reader. Keep it short: two or three
rounds of questions, not a long form.

## 0. Use the agent's question tool if it has one

Before asking anything, look through your tool list for a tool that **asks the user a
question and waits for the answer**, usually with clickable options. Agents call it different
things: a question tool, survey tool, user-input tool or elicitation tool. In Claude Code it is
`AskUserQuestion`. Match on what the tool does, not on its name.

- **If you have one, you must use it** for the background questions in §1. Don't ask them in
  plain chat. A survey with options is faster to answer and gives you comparable answers.
- **If you don't have one**, ask the same questions in plain chat, grouped as in §1, one round at
  a time. Offer the options as a short list so the user can reply with a letter or a few words.

Rules for the survey:
- Send one round per call, then wait. Use the answers to shape the next round.
- Keep each question to 2–4 options. The options are typical answers, not a complete list:
  the user can always type their own. Most tools add an "Other" choice automatically; if yours
  doesn't, add one.
- Use multi-select where several answers can be true (`strong_in`, `weak_in`,
  `familiar_domains`).
- Skip any question the user has already answered in chat or in an existing SETTINGS.md.
- Treat each answer as the user's own words. When they type "Other", copy their text into
  SETTINGS.md rather than rounding it to the nearest option.
- If the tool has a size limit (e.g. at most 4 questions per call), split a round into calls.

## 1. Ask (in rounds; skip what the user already told you)

Adapt the options to what you already know. For example, after "computer vision engineer",
offer CV-specific options in round 2.

**Round 1: who the reader is**
- What is your main field or major? (→ `field`) Options e.g.: software engineering,
  ML/data science, another science or engineering field, non-technical.
- What best describes your background? (→ `background`) Options e.g.: undergraduate student,
  graduate student/researcher, working engineer (1–5 years), working engineer (5+ years).
  Ask a follow-up in chat for the details (degree, role, years) if the answer is thin.
- How comfortable are you with math? (→ `math_level`) Options e.g.: high-school level,
  calculus and linear algebra, comfortable with probability and proofs, research-level.
- Why are you learning this? (→ `goals`) Options e.g.: read papers in the area, implement or
  use it at work, prepare for a course or interview, general curiosity.

**Round 2: what to build on**
- What are you strong in? (multi-select → `strong_in`) Offer tools, theory and math that fit
  round 1, e.g. Python, PyTorch, linear algebra, CNNs.
- What feels shaky or unfamiliar? (multi-select → `weak_in`) e.g. probability, calculus,
  optimization, low-level systems.
- Which areas do you know well enough that analogies from them would help? (multi-select →
  `familiar_domains`) e.g. image processing, web backends, signal processing, finance.

**Round 3: the output**
- Which language should the tutorial be written in? (→ `language`) Options: English, Korean,
  and the language the user is writing in. For ko/ja/zh, also choose a `CJKmainfont` from
  `fc-list :lang=ko family` (use the matching `:lang=`), and offer the installed fonts as options.
- Which PDF style? (→ `style`) `article` (clean, default), `paper` (academic look, running
  header), `notes` (sans-serif, relaxed). Ask about font size and paper size only if the user
  cares; otherwise keep the defaults.
- How do you like explanations? (multi-select → "How I like explanations") e.g. example first
  then the rule, definition first, step-by-step derivations, lots of code (ask which framework).

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
