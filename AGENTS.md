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
  topic.yaml                  title, subtitle, author, date
  index.md                    required. The table of contents: a numbered list of section pages.
  abstract.md                 required. No heading; the PDF prints "Abstract". Written last.
  intro.md                    required. Motivation, prerequisites, roadmap.
  {section}.md                the body, one page per section (e.g. softmax.md), listed in index.md.
  glossary.md                 required. Every defined term, for this reader. Always last.
  imgs/{pagename}-{short-name}.{png,jpg,pdf,svg,...}
  codes/                      code snippets and figure-generating scripts
  build/                      generated output (do not edit)
```

- All topic data stays inside `topics/{topic-name}/`.
- **index.md is the table of contents, and it sets the order.** It holds a numbered list with
  one link per section page, in reading order:
  ```
  # Contents

  1. [Logits](logits.md)
  2. [Softmax](softmax.md)
  3. [Appendix: numerical stability](appendix-stability.md)
  ```
  The PDF renders `abstract.md`, `intro.md`, the listed pages in list order, then `glossary.md`.
  `index.md` itself is not printed. You own it: update it in the same turn whenever you add,
  remove, rename or reorder a section page. `uv run tutor order <topic>` shows the resulting order.
- **Section pages:** one top-level topic per page, starting with a `#` heading that matches its
  title in `index.md`. Name them in lowercase kebab-case after the subject (`softmax.md`), not by
  number; the order lives in `index.md`. Every page in the topic folder other than the four fixed
  ones must be listed in `index.md` exactly once.
- **Old topics** with a single `contents.md`: `uv run tutor migrate <topic>` splits it at its `#`
  headings into section pages and writes `index.md`.
- **Images:** `imgs/{pagename}-{short-name}.{ext}`. `pagename` is the stem of the page that uses the
  image, e.g. `imgs/attention-map-heatmap.png` for `attention-map.md`. Use lowercase kebab-case and no
  subfolders. If a figure is generated, its script goes in `codes/` (e.g. `codes/plot_attention_map.py`).
- **Code:** put it in `codes/` and embed it with
  ````
  ```{.python include="codes/softmax.py" lines="1-20"}
  ```
  ````
  For a short snippet, an inline fenced block is fine.
- **Everything under `topics/` is the user's and is gitignored.** Never commit it.

## 3. The paper contract: keep the fixed pages consistent

Whenever a section page changes in a turn, update in the **same turn**:
1. `index.md`: lists every section page, in reading order, with its current title.
2. `intro.md`: the scope, prerequisites and roadmap must match the sections that exist.
3. `abstract.md`: the summary must describe what is actually covered now.
4. `glossary.md`: add an entry for every newly defined term, edit entries whose meaning changed,
   and remove entries for terms that no longer appear.

Never leave the index, intro, abstract or glossary describing content that isn't there.

### Glossary format

`glossary.md` starts with a heading (`# Glossary`, or the equivalent in the user's language) and
holds a pandoc definition list, sorted alphabetically (가나다 order for Korean):

```
Logit
:   The raw score a model gives a class before softmax. It is not a probability.
    See \eqref{eq:softmax}.

Fine-tuning
:   ...
```

- Each entry is one or two plain sentences written for the reader in SETTINGS.md, with no
  circular definitions. Link to the equation or section where the term is explained.
- The headword is the term's one written form (§5, `terms.yaml`). Don't add a second form in
  parentheses.
- The glossary is a reference. It does **not** replace defining the term in the text at first use.
- `tutor lint` warns when a term marked as defined in a page (`<dfn>` / **bold**) has no glossary
  entry, or a glossary entry isn't used in any page. It errors on duplicate entries.

## 4. Markdown, math and HTML (Pandoc + XeLaTeX)

- Inline math `$...$`. **Display math is always `$$...$$`**, never a bare `\begin{...}`
  environment. Markdown previews (e.g. VS Code, which uses KaTeX) only render math inside `$`
  or `$$`; the build turns each `$$` block into the right LaTeX environment.
  - Unnumbered: `$$ ... $$`.
  - Numbered: put a `\label` inside and cite it with `\eqref`. The build makes it an `equation`.
    ```
    $$
    p_i = \frac{e^{z_i}}{\sum_j e^{z_j}} \label{eq:softmax}
    $$
    As \eqref{eq:softmax} shows, ...
    ```
  - Multi-line, one number: `aligned` inside `$$`, label after it:
    `$$ \begin{aligned} a &= b \\ &= c \end{aligned} \label{eq:x} $$`.
  - Multi-line, a number per line: `align` (or `gather`, `multline`) inside `$$`, with a
    `\label` on each line you cite: `$$ \begin{align} a &= b \label{eq:y} \\ c &= d \end{align} $$`.
    Use `align*` for no numbers.
  - The mathtools/amssymb/bm macros are available.
  - The VS Code Markdown preview (KaTeX) has no `\label`/`\eqref`. To render labelled equations
    there, add these macros to your own `.vscode/settings.json` (gitignored). The label then
    shows as the tag, e.g. "(eq:softmax)":
    ```json
    "markdown.math.macros": { "\\label": "\\tag{#1}", "\\eqref": "\\text{(#1)}" }
    ```
    For the "Markdown All in One" extension, use the key `markdown.extension.katex.macros`.
- **Mermaid diagrams:** a fenced `mermaid` block. The build renders it to a vector image with
  mermaid-cli (`mmdc`). Add an id, caption and width to make it a numbered figure:
  ````
  ```{.mermaid #fig:pipeline caption="Inspection pipeline" width="70%"}
  flowchart LR
    A[Image] --> B{Defect?} -->|yes| C[Reject]
  ```
  ````
  Use mermaid for flowcharts, sequences and state machines; plot data with a script in `codes/`
  instead. Cite a captioned diagram as `Figure \ref{fig:pipeline}`. Diagrams
  are cached in `build/mermaid/`. The VS Code preview needs the "Markdown Preview Mermaid
  Support" extension to show them.
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
- Link each sentence to the one before with a connective (so, but, for example, 그래서, 반면) or a
  reference back. If no connective fits, the sentences aren't cohesive: restructure, don't pad.
- Make each predicate fit its subject by meaning: "판정은 거리에 기반한다", not "판정은 거리다".
  `tutor review <topic> --agreement` lists the copula sentences to check.
- Name compared things by what they are (`E-conv`, `E-transformer`), never `E1/E2/E3`.
- No defensive hedging or self-protective disclaimers.
- Natural phrasing in the target language: no translationese and no made-up idioms.
- **One written form per technical term**, in one language, across every page of every topic.
  Record each term's form and the forms to avoid in `terms.yaml` (repo root, the user's file);
  `tutor lint` fails on an avoided form. Never pair forms like "layer (층)". Full rules:
  `skills/clear-writing/SKILL.md` §8.

## 6. CLI reference

| Command | Does |
|---|---|
| `uv run tutor start` | print settings, topics and rules; acknowledge settings (**run first**) |
| `uv run tutor new <name> [--title T]` | create `topics/<name>/` from the template |
| `uv run tutor order <topic>` | show the render order (edit `index.md` to change it) |
| `uv run tutor migrate <topic>` | split an old `contents.md` into section pages + `index.md` |
| `uv run tutor terms` | check every topic against `terms.yaml` (one form per term) |
| `uv run tutor lint <topic>` | structural rules (must pass, exit 1 on errors) |
| `uv run tutor review <topic> [page] [--strict]` | readability warnings as `file:line` |
| `uv run tutor review <topic> [page] --agreement` | list copula sentences (subject → complement) to check by meaning |
| `uv run tutor build <topic> [--style S] [--html]` | PDF (or HTML preview) → `topics/<topic>/build/` |
| `uv run tutor settings` | validate SETTINGS.md: style, fonts, xelatex |

## 7. Repository hygiene

- Commit only harness files: `src/`, `skills/`, docs and tests. Never commit `SETTINGS.md`, `terms.yaml`,
  `skills.local/`, `topics/*`, `.tutor/` or build output (all are gitignored).
- Use real customer or personal data only when the user supplies it for their own tutorial. Never put it
  in shipped examples or tests.
- Run `uv run pytest` after changing anything in `src/`.
