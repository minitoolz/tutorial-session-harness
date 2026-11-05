# tutor: co-write tutorials with a coding agent

You learn a topic by writing a paper-style tutorial (abstract, intro, section pages listed in an index, glossary) together with a
coding agent. Pages are Markdown with LaTeX math and inline HTML, and they render to PDF with
Pandoc + XeLaTeX.

It works with any agent: Claude Code, Codex, Cursor, Gemini CLI, Aider, and so on. The rules live
in [`AGENTS.md`](AGENTS.md), the workflows in [`skills/`](skills/), and the tooling in one CLI,
`uv run tutor`.

## Setup

1. Install [uv](https://docs.astral.sh/uv/) and a TeX distribution with XeLaTeX:
   - macOS: `brew install --cask mactex-no-gui` (or full MacTeX)
   - Debian/Ubuntu: `sudo apt install texlive-xetex texlive-latex-extra texlive-lang-cjk`
2. `uv sync`. This installs everything else, including the pandoc binary (via `pypandoc-binary`).
   - Optional, for mermaid diagrams: Node.js and `npm install -g @mermaid-js/mermaid-cli`
     (or point `TUTOR_MMDC` at an `mmdc` binary).
3. Open your agent in this directory and say hello. On its first `uv run tutor start` it will
   interview you about your background, language and preferred PDF style, and then write
   `SETTINGS.md`. To do it by hand instead, copy `SETTINGS.example.md` to `SETTINGS.md` and fill it in.

## Daily use

Talk to the agent: "I want to understand softmax temperature", "explain the gradient step
again", "make the PDF". It follows the skills. You can also run the CLI yourself:

```sh
uv run tutor start                    # always first; prints your settings
uv run tutor new softmax-basics       # topics/softmax-basics/
uv run tutor review softmax-basics    # readability warnings
uv run tutor lint softmax-basics      # structure rules
uv run tutor build softmax-basics     # → topics/softmax-basics/build/softmax-basics.pdf
uv run tutor build softmax-basics --html   # quick preview, no LaTeX needed
```

## What's yours vs. what's shared

| Path | Committed? | What |
|---|---|---|
| `AGENTS.md`, `skills/`, `src/`, `tests/` | yes | the harness |
| `SETTINGS.example.md` | yes | template |
| `SETTINGS.md` | **no** | your background and preferences |
| `skills.local/` | **no** | your own skills and phrase lists (same format as `skills/`) |
| `topics/*` | **no** | your tutorials, images, code, PDFs |
| `.tutor/` | **no** | session state |

## Customizing

- **PDF look:** set `style:` (`article`, `paper` or `notes`), the fonts, `fontsize`, `geometry` and so
  on in SETTINGS.md. To add a style, put a LaTeX header file in `src/tutor/data/pandoc/styles/`.
- **Phrases that confuse you:** add them to `skills.local/clear-writing/phrases.yaml`, and
  `tutor review` will flag them.
- **Your own workflows:** put them in `skills.local/<name>/SKILL.md`.

## Dependencies and licenses

| Dependency | License | Notes |
|---|---|---|
| PyYAML | MIT | |
| pypandoc-binary | MIT (wrapper) / **GPL-2.0+ (bundled pandoc)** | pandoc runs as a separate CLI process for internal authoring. It isn't linked into or shipped with any product. If this repo ever becomes product code, have the ISO review it. |
| pytest (dev) | MIT | |
| TeX Live / MacTeX | LPPL & others | system install, not managed by uv |
| @mermaid-js/mermaid-cli (optional) | MIT (bundles Puppeteer, Apache-2.0, and Chromium, BSD) | system install via npm, run as a CLI; only needed for mermaid diagrams |

## Development

```sh
uv run pytest
```
