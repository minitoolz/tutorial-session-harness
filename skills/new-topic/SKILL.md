---
name: new-topic
description: Start a new tutorial topic and write its first draft with the user.
when-to-use: The user wants to understand something that has no topic under topics/ yet.
---

# New topic

1. **Agree on scope first.** Ask what exactly the user wants to understand, what triggered it
   (a paper, a bug, a meeting), and what they'll do with it. Compare that with `audience` in
   SETTINGS.md to decide the starting point.
2. **Create it:** `uv run tutor new <kebab-name> --title "<Readable Title>"`.
3. **Draft in this order:**
   1. `intro.md`: motivation for *this* reader, prerequisites (what is assumed and what will be
      explained), and a roadmap with one sentence per planned section.
   2. `contents.md`: sections under `#` headings. Each section starts concrete (an example or a
      small number case), then generalizes. Follow `skills/clear-writing` and, for equations,
      `skills/explain-math`.
   3. `glossary.md`: one entry per term you marked as defined (`<dfn>` / **bold**), written for
      this reader (format in AGENTS.md §3).
   4. `abstract.md`: written last, 3–6 sentences, no heading. What the reader will understand
      and which sections get them there.
4. **Figures and code:** save as `imgs/<page>-<short-name>.png`. Put the script that makes a
   figure in `codes/`, and run it with `uv run python codes/<script>.py` if it needs only the
   standard library. Otherwise tell the user which packages it needs.
5. **Keep the first turn small.** Write the intro and one or two sections, then stop and check in.
   Ask the user to explain the key idea back in one or two sentences, or ask a quick question that
   shows whether it landed.
6. **End of turn:** `skills/readability-review`, then `uv run tutor lint <topic>`.
