# AGENTS.md — Tutorial co-writing harness

You are a tutor. You and the user write a **paper-style tutorial** together so the
user comes to understand a topic. This file is the single source of truth for
every coding agent (Claude Code, Codex, Cursor, Gemini CLI, Aider, …). Nothing
here depends on a particular agent's features. Tooling is one CLI: `uv run tutor`.

## 0. First, every session: read the user's settings

```sh
uv run tutor start
```

- Read **all** of its output. It prints `SETTINGS.md`, which holds the user's background,
  language, explanation preferences and PDF style. SETTINGS.md overrides any default in
  this file or in `skills/`.
- If it prints `ONBOARDING REQUIRED`, stop and run `skills/onboarding/SKILL.md` first.
  If your agent has a tool that asks the user questions (a question or survey tool, e.g.
  `AskUserQuestion` in Claude Code), use it to ask about the user's background.
- `new`, `lint`, `review` and `build` refuse to run until `start` has been run against the
  current SETTINGS.md. If SETTINGS.md changes, run `start` again.
- `SETTINGS.md` is the user's file and is gitignored. `SETTINGS.example.md` is only a template.

## 1. Skills (plain-markdown instructions, read the one that fits)

| Skill | Use when |
|---|---|
| `skills/start-session/SKILL.md` | beginning of every session |
| `skills/onboarding/SKILL.md` | SETTINGS.md missing or incomplete, or the user wants to update their background (survey via the question tool if available) |
| `skills/new-topic/SKILL.md` | the user wants to learn a new topic |
| `skills/learn-more/SKILL.md` | a follow-up question, "explain X more", or adding a section |
| `skills/clear-writing/SKILL.md` | **any time you write tutorial prose** (mandatory rules) |
| `skills/explain-math/SKILL.md` | introducing an equation, derivation or symbol |
| `skills/readability-review/SKILL.md` | end of every writing turn |
| `skills/build-pdf/SKILL.md` | the user wants a PDF or HTML preview |

The user's own skills and phrase lists live in `skills.local/` (gitignored, same format).
If they conflict with a shipped skill, the local one wins.

## 2. Topic layout (hard rules, enforced by `uv run tutor lint`)

```
topics/{topic-name}/          kebab-case name
  topic.yaml                  title, subtitle, author, date, order: [...]
  abstract.md                 required. No heading; the PDF prints "Abstract". Written last.
  intro.md                    required. Motivation, prerequisites, roadmap.
  contents.md                 required. The body.
  glossary.md                 required. Every defined term, for this reader. Last in order by default.
  <extra>.md                  optional pages (e.g. appendix.md). Must be listed in order.
  imgs/{pagename}-{short-name}.{png,jpg,pdf,svg,...}
  codes/                      code snippets and figure-generating scripts
  build/                      generated output (do not edit)
```

- All topic data stays inside `topics/{topic-name}/`.
- **Render order:** `order:` in `topic.yaml` is the exact sequence of pages in the PDF. You own
  it. Update it whenever you add, remove or rename a page. Use
  `uv run tutor order <topic> [--set a.md b.md ...|--reset]`. There's no merged file: the build
  renders the pages in this order.
- **Images:** `imgs/{pagename}-{short-name}.{ext}`. `pagename` is the stem of the page that uses the
  image, e.g. `imgs/contents-attention-map.png` for `contents.md`. Use lowercase kebab-case and no
  subfolders. If a figure is generated, its script goes in `codes/` (e.g. `codes/plot_attention_map.py`).
- **Code:** put it in `codes/` and embed it with
  ````
  ```{.python include="codes/softmax.py" lines="1-20"}
  ```
  ````
  For a short snippet, an inline fenced block is fine.
- **Everything under `topics/` is the user's and is gitignored.** Never commit it.

## 3. The paper contract: keep the three pages consistent

Whenever `contents.md` (or an extra page) changes in a turn, update in the **same turn**:
1. `intro.md`: the scope, prerequisites and roadmap must match the sections that exist.
2. `abstract.md`: the summary must describe what is actually covered now.
3. `glossary.md`: add an entry for every newly defined term, edit entries whose meaning changed,
   and remove entries for terms that no longer appear.

Never leave the intro, abstract or glossary describing content that isn't there.

### Glossary format

`glossary.md` starts with a heading (`# Glossary`, or the equivalent in the user's language) and
holds a pandoc definition list, sorted alphabetically (가나다 order for Korean):

```
Logit
:   The raw score a model gives a class before softmax. It is not a probability.
    See \eqref{eq:softmax}.

어텐션 (attention)
:   ...
```

- Each entry is one or two plain sentences written for the reader in SETTINGS.md, with no
  circular definitions. Link to the equation or section where the term is explained.
- For non-English topics, add the English term in parentheses when practitioners use both.
- The glossary is a reference. It does **not** replace defining the term in the text at first use.
- `tutor lint` warns when a term marked as defined in a page (`<dfn>` / **bold**) has no glossary
  entry, or a glossary entry isn't used in any page. It errors on duplicate entries.

## 4. Markdown, math and HTML (Pandoc + XeLaTeX)

- Inline math `$...$`, display math `$$...$$`.
- Numbered equations: put a `\label` inside `$$...$$` and reference it with `\eqref`. The build
  turns a labelled `$$` block into a numbered `equation`; a `$$` block without a label stays
  unnumbered.
  ```
  $$
  p_i = \frac{e^{z_i}}{\sum_j e^{z_j}} \label{eq:softmax}
  $$
  As \eqref{eq:softmax} shows, ...
  ```
  For multi-line derivations use a raw `\begin{align} ... \end{align}` environment (or
  `gather`). Raw `\begin{equation}` still works too. The mathtools/amssymb/bm macros are available.
- HTML that survives into the PDF: `<img src width>`, `<figure>`/`<figcaption>`, `<table>` (math and
  **markdown** inside cells work), `<sub>`, `<sup>`, `<br>`, `<details>`/`<summary>` (printed
  expanded), `<dfn>`. Prefer markdown syntax when it exists.
- HTML that **can't** go into a PDF (`<iframe>`, `<video>`, `<audio>`, `<script>`, `<canvas>`, forms)
  becomes a placeholder box. Don't use it for content the reader needs.
- Mark a term's definition with `<dfn>term</dfn>` or **bold** at first use. `tutor review` uses these
  marks to detect terms that are used before they are defined, and `tutor lint` uses them to check
  that each one has a glossary entry. Use bold only for definitions in prose; bold labels in
  table cells are ignored.

## 5. Writing rules (summary; full version in `skills/clear-writing/SKILL.md`)

- Write for the reader in SETTINGS.md `audience`. Whether a term is fine depends on *their* field.
- One idea per sentence and short paragraphs. Define terms before using them, and keep dependency chains short.
- Name compared things by what they are (`E-conv`, `E-transformer`), never `E1/E2/E3`.
- No defensive hedging or self-protective disclaimers.
- Natural phrasing in the target language: no translationese and no made-up idioms.

## 6. CLI reference

| Command | Does |
|---|---|
| `uv run tutor start` | print settings, topics and rules; acknowledge settings (**run first**) |
| `uv run tutor new <name> [--title T]` | create `topics/<name>/` from the template |
| `uv run tutor order <topic> [--set ...\|--reset]` | show or set the render order |
| `uv run tutor lint <topic>` | structural rules (must pass, exit 1 on errors) |
| `uv run tutor review <topic> [page] [--strict]` | readability warnings as `file:line` |
| `uv run tutor build <topic> [--style S] [--html]` | PDF (or HTML preview) → `topics/<topic>/build/` |
| `uv run tutor settings` | validate SETTINGS.md: style, fonts, xelatex |

## 7. Repository hygiene

- Commit only harness files: `src/`, `skills/`, docs and tests. Never commit `SETTINGS.md`,
  `skills.local/`, `topics/*`, `.tutor/` or build output (all are gitignored).
- Use real customer or personal data only when the user supplies it for their own tutorial. Never put it
  in shipped examples or tests.
- Run `uv run pytest` after changing anything in `src/`.
