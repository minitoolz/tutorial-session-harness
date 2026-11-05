---
name: build-pdf
description: Render a topic to PDF (Pandoc + XeLaTeX) or a quick HTML preview, and fix build problems.
when-to-use: The user asks for a PDF, a preview, or a different look.
---

# Build PDF

1. `uv run tutor build <topic>` → `topics/<topic>/build/<topic>.pdf`.
   It runs lint first and stops on errors.
   - The pages are rendered as `intro.md`, the section pages in `index.md` order, then
     `glossary.md` (`uv run tutor order <topic>` shows it). `abstract.md` becomes the abstract
     block. `index.md` itself is not printed; set `toc: true` in SETTINGS.md for a printed
     table of contents.
   - Fonts, language, paper and style come from SETTINGS.md. To try another style once, use
     `--style paper`. To change it permanently, edit `style:` in SETTINGS.md and re-run
     `uv run tutor start`.
2. Quick look without LaTeX: `uv run tutor build <topic> --html` (math rendered with MathML).
3. Open the result for the user (`open <file>` on macOS, `xdg-open` on Linux) if they want.

## Common failures

| Message | Fix |
|---|---|
| `xelatex not found` | install TeX (README) |
| `needs CJKmainfont` | set `CJKmainfont` in SETTINGS.md (`fc-list :lang=ko family`) |
| `Font "X" not found` | `uv run tutor settings` shows which; pick an installed font |
| `Undefined control sequence` | a LaTeX macro isn't loaded; use a standard one, or add the package to a style in `src/tutor/data/pandoc/styles/` (harness change; ask the user first) |
| `[html2latex] WARNING: <iframe> ...` | that HTML can't go in a PDF; use an image or a link instead |
| svg image fails | install `librsvg` (`rsvg-convert`) or export the figure as pdf/png |
