---
name: readability-review
description: Self-review checklist run at the end of every writing turn.
when-to-use: Before you finish any turn in which you wrote or changed tutorial pages.
---

# Readability review

1. Run `uv run tutor review <topic>`. Optionally pass a page: `uv run tutor review <topic> softmax.md`.
2. Fix every flag in the text you wrote this turn:
   - `[long-sentence]`: split it into one idea per sentence.
   - `[long-paragraph]`: split it by topic.
   - `[undefined-term]`: define the term at first use, or move the definition earlier.
   - `[opaque-label]`: rename E1/E2/… after what each item is, everywhere (tables, figures, code).
   - `[hedge]`: delete it, unless it carries new, specific information (see clear-writing §6).
   - `[phrase]`: apply the suggestion.
   If a flag is a false positive (e.g. "L1 norm"), leave the text alone. If the false positive keeps
   coming back, add the token to `label_allowlist` in `skills.local/clear-writing/phrases.yaml`.
3. Then reread your new text **as the reader in SETTINGS.md** and check what the tool can't:
   - Would this person know every word? (Check `audience.field` and `weak_in`.)
   - Can each sentence be understood from the few before it?
   - Does every new symbol have a plain-words definition next to its equation?
   - Is there a concrete example before each general statement?
   - Do any analogies come from a field the reader doesn't know?
   - In ko/ja/zh: does it read like a native author wrote it, or like a translation?
4. Run `uv run tutor lint <topic>`. It must report 0 errors. Resolve its glossary warnings (a
   defined term with no entry, or an entry that isn't used anywhere) by editing `glossary.md`.
