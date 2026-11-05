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
   - `[low-cohesion]`: link each sentence to the one before with a connective that states the
     relation (so, but, for example, 그래서, 반면, 예를 들어) or a reference back (이 방법은).
     If no connective fits, the sentences don't belong together as written: reorder them, move
     one to another paragraph, or add the missing step (clear-writing §2).
   - `[undefined-term]`: define the term at first use, or move the definition earlier.
   - `[opaque-label]`: rename E1/E2/… after what each item is, everywhere (tables, figures, code).
   - `[hedge]`: delete it, unless it carries new, specific information (see clear-writing §6).
   - `[phrase]`: apply the suggestion.
   - `[term]` (from `tutor lint`): replace the form with the one `terms.yaml` names.
   If a flag is a false positive (e.g. "L1 norm"), leave the text alone. If the false positive keeps
   coming back, add the token to `label_allowlist` in `skills.local/clear-writing/phrases.yaml`.
3. Run `uv run tutor review <topic> <page> --agreement` for each page you changed. For every
   `subject → complement` pair it lists, check by meaning that the subject can really BE the
   complement ("판정 → 거리" fails: a decision is based on a distance). Rewrite the ones that
   fail (clear-writing §2, "Subject and predicate must agree").
4. Then reread your new text **as the reader in SETTINGS.md** and check what the tool can't:
   - Would this person know every word? (Check `audience.field` and `weak_in`.)
   - Can each sentence be understood from the few before it?
   - Can the reader tell what kind of sentence comes next (a result, a contrast, an example)?
   - Does every new symbol have a plain-words definition next to its equation?
   - Is there a concrete example before each general statement?
   - Do any analogies come from a field the reader doesn't know?
   - Did you introduce a technical term? Is it in `terms.yaml` with the forms to avoid, and is
     it written in that one form everywhere (clear-writing §8)?
   - In ko/ja/zh: does it read like a native author wrote it, or like a translation?
   - Does every predicate fit its subject, including verbs and adjectives the agreement list
     doesn't show ("determinant가 쉽다" → "determinant 계산이 쉽다")?
5. Run `uv run tutor lint <topic>`. It must report 0 errors. Resolve its glossary warnings (a
   defined term with no entry, or an entry that isn't used anywhere) by editing `glossary.md`.
