---
name: clear-writing
description: Mandatory rules for every paragraph of tutorial prose. Keeps text readable for the specific user in SETTINGS.md.
when-to-use: Any time you write or rewrite text in a topic page (abstract, intro, section pages).
---

# Clear writing

Generated prose often goes wrong in the same ways. It packs too much into one sentence and
leans on terms from three paragraphs back. It borrows words from fields the reader never
worked in, and it pads with disclaimers. These rules prevent that. The settings in
SETTINGS.md (especially `audience` and the free-text preferences) **override** the numbers here.

## 1. Know the reader before choosing words

Read `audience` in SETTINGS.md: `field`, `background`, `strong_in`, `weak_in`, `math_level`,
`familiar_domains`, `goals`.

- A term is fine without explanation if it is common in the **reader's field**, in the
  **topic's own field** at the level they're learning, or in **everyday language**.
- Anything else is either defined in plain words on first use or replaced with a simpler word.
- Words are judged against the reader, not against a fixed blacklist. "A/B test" is ordinary for
  most engineers. "Experiment arm" is clinical-trial vocabulary. It confuses an ML engineer
  who has never read a trial protocol, so write "variant" or "configuration" instead.
- **Analogies** should come from `familiar_domains` or `strong_in`. An analogy from a field the reader
  doesn't know adds a second thing to learn.
- If you are unsure whether the reader knows a term, ask once and record the answer in
  SETTINGS.md (see skills/onboarding).

## 2. Sentence and paragraph shape

- **One idea per sentence.** Split a sentence when it has two "and/which/so" clauses carrying new
  information.
- Default limits (from `review:` in SETTINGS.md): about 25 words per English sentence, about 60
  characters per Korean/Japanese/Chinese sentence, and at most 5 sentences per paragraph.
- **One topic per paragraph.** The first sentence says what the paragraph is about.
- Prefer active voice with a clear subject: "The encoder maps..." rather than "A mapping is performed...".

## 3. Short dependency chains

- **Define before use.** Every term and symbol is explained at or before its first appearance in
  reading order (intro, then the section pages in `index.md` order). Mark the definition with `<dfn>term</dfn>` or **bold** so
  `tutor review` can check it, and add the term to `glossary.md`. The glossary entry is a
  reminder for the reader. It never replaces the definition in the text.
- A sentence should depend only on the last few sentences, or on something it names explicitly
  ("the loss in \eqref{eq:ce}", "the toy example in Section 2").
- Don't write vague forward references ("as we will see later"). Either say what will be shown and
  where, or leave it out.
- Re-state a key quantity briefly when it returns after a gap. Don't make the reader scroll back.

## 4. Concrete before abstract

Use this order: a small concrete example (numbers, a picture, a 3-element vector) → the general
statement → the formal definition. A general rule is easier to read once the reader has seen
one case of it.

## 5. Meaningful labels, never opaque indices

When you compare experiments, methods, variants, datasets or cases, name each one by what it *is*:

| Don't | Do |
|---|---|
| E1, E2, E3 | E-conv, E-transformer, E-mixed |
| M1 / M2 | M-baseline / M-ours |
| Setting A / Setting B | fp32 / bf16 |
| Case 1, Case 2 | small-batch case, large-batch case |

This applies to prose, table rows and columns, figure legends, and variable names in `codes/`.
Numbers are fine only when the order itself is the meaning (step 1, 2, 3; layer index $\ell$;
epoch 10).

## 6. No defensive hedging

Don't add sentences whose only job is to protect the writer. The reader already has the context
you stated, so repeating it as a warning reads as condescending filler.

Delete on sight:
- After a benchmark that names the GPU: "These results were measured on the host machine and may
  not apply to other GPUs."
- "Results may vary depending on your environment." / "환경에 따라 결과가 다를 수 있습니다."
- "This is a simplification." / "It's important to note that…" / "Please consult the official
  documentation for details."

A caveat is allowed only if it adds **new, specific, actionable** information:
- OK: "On A100 this kernel is memory-bound, so the speedup drops to about 1.2×."
- OK: "This derivation assumes the logits are bounded; Section 4 removes that assumption."

When in doubt, delete it.

## 7. Natural language, no translationese

- Write the way a fluent author in the target language writes, not a word-by-word translation
  from English.
- Don't invent idioms. "버그를 밟았다" isn't something Korean developers say. Write "버그를
  만났다" or "버그가 있었다".
- Korean: avoid stacking "~의 ~의", "~에 대한 ~에 대한" and the constructions "~를 가지다" and
  "~되어지다". Use technical terms the way Korean practitioners do. Keep the English term in
  parentheses on first use when practitioners use both, e.g. 어텐션(attention).

## 8. Check yourself

Before ending a turn, follow `skills/readability-review/SKILL.md`. See `examples.md` for
before/after rewrites, and `phrases.yaml` for the phrases `tutor review` flags.
