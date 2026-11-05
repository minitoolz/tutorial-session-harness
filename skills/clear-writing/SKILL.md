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
- Default limits (from `review:` in SETTINGS.md): about 50 words per English sentence, about 120
  characters per Korean/Japanese/Chinese sentence, and at most 5 sentences per paragraph.
  The sentence limits are a ceiling, not a target. They leave room for a sentence to carry its
  connective and a short reason ("A이므로 B다"), not for packing in a second new idea.
- **One topic per paragraph.** The first sentence says what the paragraph is about.
- Prefer active voice with a clear subject: "The encoder maps..." rather than "A mapping is performed...".

### Connect each sentence to the one before

Short sentences in a row read like a list of facts unless the reader can see how each one
follows from the last. A connective tells the reader what kind of sentence comes next, so they
can predict it instead of working it out.

- Open every sentence after the first in a paragraph with a link to the previous one:
  - a connective that names the relation: result (so, 그래서, 따라서), contrast (but, however,
    그러나, 반면), example (for example, 예를 들어), restatement (that is, 즉), sequence
    (first/next/finally, 먼저/다음으로/마지막으로), condition (이때, 이 경우);
  - or an explicit reference back: "This step...", "이 방법은", "두 값은";
  - or a reason ending that explains the previous sentence: "~때문이다".
- **Use the connective as a test.** Before writing a sentence, ask which connective joins it to
  the one before. If none fits honestly, the two sentences are not cohesive, and adding a
  connective would only hide that. Restructure instead:
  - reorder so that each sentence builds on the previous one;
  - move the sentence to the paragraph it belongs to, or start a new paragraph;
  - add the missing step that makes the second sentence follow from the first.
- Don't paste in an empty "also / 또한 / 그리고" to silence the check. The connective must state
  the real relation; "또한" fits only when the sentence adds a parallel item.
- Announce structure before it arrives: "두 가지를 바꿨다." followed by "첫째, …", "둘째, …"
  lets the reader know how many items to expect.
- `tutor review` flags `[low-cohesion]` when more than `review.max_unlinked_sentences`
  sentences in a row have none of these links. The marker lists are `connectives:` in
  `phrases.yaml` (extend them in `skills.local/clear-writing/phrases.yaml`).

### Subject and predicate must agree

Check that the predicate fits its subject by meaning, not only by grammar. The commonest slip is
a copula sentence ("A is B", "A는 B다") whose subject cannot actually *be* the complement:

| Wrong | Why | Right |
|---|---|---|
| 판정은 Gaussian 거리이므로 | a decision is not a distance | 판정은 Gaussian 거리에 기반하므로 |
| 이 loss는 두 힘의 균형이다 | a loss is not a balance | 이 loss에는 서로 반대로 작용하는 두 항이 있다 |
| 학습은 feature 추출뿐이다 | training is not an extraction | 학습 단계에서 하는 일은 feature 추출뿐이다 |
| The decision is a distance | same | The decision is based on a distance |

The same holds for verbs and adjectives: "determinant가 쉽다" says the determinant is easy, when
the computation is (write "determinant 계산이 쉽다"). Name the operation, the property or the
relation ("is based on", "consists of", "is measured by") that the subject really has.

`uv run tutor review <topic> [page] --agreement` lists every copula sentence as
`subject → complement`. Read each pair and ask: can this subject really BE this complement?
The list is an aid, not a verdict: it cannot judge meaning, and it misses non-copula slips.

### Side notes

Background the reader may skip, such as what a tool or term used in passing is, goes in a note
so it doesn't break the main line. A note is a blockquote: **every line starts with `>`**, and the
PDF draws it as a shaded box. Mark the term it explains with `\*` and start the note with
`> \* ` (AGENTS.md §4). A note follows the same writing rules as the body. Keep it short; a
recap the reader needs to follow the section is a subsection, not a note.

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
  "~되어지다".
- Technical terms follow §8: one form each, used everywhere.

## 8. One written form per technical term

A technical term is written in exactly one form, in one language, in every page of every topic:
headings, prose, captions, `index.md` titles and the glossary. If one page says "layer", no page
says "neural network layer", "Schicht", "층" or "レイヤー" for the same thing. Switching forms
makes the reader wonder whether two different things are meant. This holds in every language.

- **Choose the form once**, from the user's preference in SETTINGS.md ("Technical terms"):
  usually the form practitioners in the reader's field write. If there is no preference and the
  choice isn't obvious, ask the user.
- **Record it in `terms.yaml`** (repo root, the user's file, shared by all topics) the moment you
  introduce the term. List the forms you might drift into: translations, transliterations,
  spelled-out or abbreviated forms, spacing and hyphenation variants.
  ```yaml
  layer: [neural network layer, 층, 레이어]
  fine-tuning: [finetuning, fine tuning, 미세 조정]
  ```
  `tutor start` prints the list each session. `tutor lint` fails on any listed form, and
  `tutor terms` checks every topic at once.
- **Don't pair forms.** No "layer (층)" or "층(layer)" glosses, in the text or in the glossary.
  If the reader needs a bridge to a form they know, define the term in plain words instead.
- **Matching:** a listed form matches at the start of a word and covers its plurals, inflections
  and attached particles. In scripts written without spaces (Chinese, Japanese, Thai) it matches
  anywhere. Code, math and diagram source are not checked. If a form is too short and matches
  too much, write it as a regex: `re:\bnet\b`.
- **When the user changes a term**, update `terms.yaml`, run `uv run tutor terms`, and fix every
  topic it reports, not only the one you're working on.

## 9. Check yourself

Before ending a turn, follow `skills/readability-review/SKILL.md`. See `examples.md` for
before/after rewrites, and `phrases.yaml` for the phrases `tutor review` flags.
