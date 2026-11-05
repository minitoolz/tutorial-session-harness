---
name: explain-math
description: How to introduce equations, symbols and derivations so the reader can follow them.
when-to-use: Whenever a page gains an equation, a new symbol or a derivation.
---

# Explaining math

Match the depth to `audience.math_level` in SETTINGS.md.

## Introducing an equation

1. **Intuition first**, in one or two plain sentences: what the equation computes and why we want it.
2. **Name every symbol** right next to the equation, in words, including shapes or units when
   they help:
   ```
   $$
   p_i = \frac{e^{z_i}}{\sum_{j=1}^{K} e^{z_j}} \label{eq:softmax}
   $$
   where $z_i$ is the score (logit) of class $i$, $K$ is the number of classes,
   and $p_i$ is the resulting probability of class $i$.
   ```
3. **A worked number example**: a tiny case the reader could check by hand, e.g. $z = (2, 1, 0)$
   gives $p \approx (0.67, 0.24, 0.09)$.
4. **Connect back**: one sentence on what the example shows about the general case.

## Derivations

- One transformation per line, in `$$ \begin{align*} ... \end{align*} $$` (or `align` with a
  `\label` on lines you cite). Always wrap display math in `$$`. Put a short reason on lines that
  aren't obvious, e.g. `&= ... && \text{(divide by } e^{c}\text{)}`.
- Don't skip algebra the reader's `math_level` would stumble on.
- Number only the equations you refer to later: add `\label{eq:...}` inside the `$$...$$` block and
  cite it with `\eqref`. Leave the label out for the rest; they stay unnumbered.

## Symbols and notation

- Follow the notation section of SETTINGS.md. Otherwise keep one convention for the whole topic
  and state it in `intro.md`.
- Never reuse a symbol for a different meaning in the same topic.
- If a symbol comes back after a long gap, remind the reader: "recall $K$ is the number of classes".
- **Every section explains its own symbols.** Each single-letter symbol ($\tau$, $K$, $\mathbf{x}$)
  a section page uses is said in words at least once in that same page, even if an earlier
  section already defined it: "threshold $\tau$", "$K$는 결함 영역의 수다", "...를 $\mathbf{m}_i$라 하자".
  A bare symbol in a sentence ("$\alpha = 0.3$을 썼다") is not enough; write "max FP rate $\alpha$".
  `tutor review` flags misses as `[undefined-symbol]`.

## Code next to math

When a formula has a direct implementation, put the code in `codes/` and include it right after
the formula. Variable names should match the symbols or their meaning (`logits`, `probs`), not
`a`, `b`, `x1`.
