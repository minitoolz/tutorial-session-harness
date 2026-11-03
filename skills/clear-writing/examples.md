# Before / after rewrites

## Dense sentence with a long dependency chain

**Before**

> Since the normalizer couples every logit, which means the gradient of each output with respect
> to any input involves all others as discussed above, temperature scaling, which divides the
> logits by $T$ before exponentiation, changes not only the entropy but also the effective
> learning rate of the upstream layers.

**After**

> The softmax output for one class depends on *every* logit, because the denominator sums over
> all of them. So changing one logit moves all the probabilities.
>
> <dfn>Temperature scaling</dfn> divides the logits by a number $T$ before the softmax. A large
> $T$ flattens the distribution, and a small $T$ sharpens it.
>
> Dividing by $T$ also divides the gradients by $T$. Raising $T$ therefore acts like lowering
> the learning rate of the layers before the softmax.

## Vocabulary from the wrong field (reader: ML engineer, no clinical background)

**Before**

> We ran three experiment arms and the treatment arm outperformed control.

**After**

> We trained three configurations: `E-conv`, `E-transformer` and `E-mixed`. `E-mixed` had the
> lowest validation loss.

## Opaque labels

**Before**

| | E1 | E2 | E3 |
|---|---|---|---|
| Top-1 | 76.1 | 79.4 | 80.2 |

**After**

| | E-conv | E-transformer | E-mixed |
|---|---|---|---|
| Top-1 | 76.1 | 79.4 | 80.2 |

## Defensive hedge

**Before**

> On an RTX 4090 the fused kernel reaches 1.8× the throughput of the baseline. Note that these
> results were measured on the host machine and may not apply to other GPUs.

**After**

> On an RTX 4090 the fused kernel reaches 1.8× the throughput of the baseline.

(Add a caveat only when you know something specific: "On A100 the kernel becomes memory-bound
and the gain drops to about 1.2×.")

## Korean: idiom and translationese

**Before**

> 학습 중에 버그를 밟았는데, 이 모델은 많은 파라미터를 가지고 있기 때문에 디버깅이 어렵게 되어진다.

**After**

> 학습 중에 버그를 만났다. 이 모델은 파라미터가 많아서 디버깅이 어렵다.
