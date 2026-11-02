# Nought: a smaller kernel and zero-bit self-interpretation

**A binary language whose empty program interprets the language.**

**Nought is a reflective, reverse-scanning dialect of Chris Barker's Jot.**
Its nonempty programs use Jot's construction rules in reverse source order;
empty source denotes the decoder itself. See the [Jot definitions and attribution](experiments/bitfold.md#execution-without-a-structured-source-parser).
The name identifies this dialect and its implementation, not a new underlying
computation model or a claim of priority for reflection or reversed scanning.

Nought names the reflective SK reverse-fold language described here. The KSK
construction is a comparison variant. The implementation is `languages/nought.py`,
with saved programs and reports under `artifacts/nought/`.

Nought has a **zero-bit native self-interpreter
and a 155-bit closed lambda decoder kernel**. Both measurements improve on the
original functional candidate's 174/174 pair, under the same external raw-list
interface and the same reference lambda machine. The source language is different:
it is a reflective extension of the reverse-scanning bitfold language, not BLC.

The ordinary bitfold kernels also improve without changing their languages:

| Language | Native self-interpreter | Raw-list decoder kernel in BLC |
| --- | ---: | ---: |
| Original functional/BLC-derived language | 174 | 174 |
| Earlier SK reverse fold | 1,529 | 148 |
| Optimized SK reverse fold | **1,169** | **114** |
| Earlier KSK reverse fold | 1,339 | 157 |
| Optimized KSK reverse fold | **1,035** | **123** |
| Nought (reflective SK reverse fold) | **0** | **155** |
| Reflective KSK reverse fold | 0 | 164 |

The ordinary and reflective variants expose different tradeoffs. A 114-bit kernel
is not itself a 114-bit native bitfold program. Conversely, the zero-bit program
does not make the runtime definition disappear. Every row counts both quantities.

## Ordinary fold semantics and universality

The ordinary languages retain the [previous bitfold definitions](experiments/bitfold.md).
Start at identity I, scan source right to left, and update the accumulator:

```text
0: a -> a S K       (or a K S K for the second language)
1: a -> S (K a)
```

The original arbitrary-accumulator certificates still apply. In left-to-right
notation they give words that transform every accumulator `a` into `a K` or `a S`:

| Basis | K word | S word |
| --- | --- | --- |
| SK | `11100` | `11111000` |
| KSK | `1111100` | `110` |

Applications compile as `1 ++ code(left) ++ code(right)`, and the whole result
is reversed for the right-to-left language. Induction on SK terms gives every
closed lambda computation a native program. All such compiled programs are
nonempty, which matters for the reflective extension below.

Every other finite source also denotes a closed computation by the fold rule.
There are no source syntax errors. The fold uses the whole supplied source;
there is no complete-prefix/ignored-suffix rule as in the BLC-derived candidate.

## Why the kernels became smaller

The earlier implementation expanded a general fixed-point combinator around the
fold body. The new construction writes the recursion directly in self-application
form. A certificate checks that both presentations beta-reduce to exactly the
same expression, so this is not merely a finite testing claim.

Beta contraction reduces the directly expressed kernels to 115 and 124 BLC bits.
A two-round equivalence search then saves one additional bit in each by introducing
a helper and contracting a different redex. This is an actual improvement found
by inverse beta rewriting; the older search on the 174-bit parser had no such
success. The selected searches use beam 64, growth allowance 32 bits, and a
20,000-candidate cap, generating 6,722 and 8,922 candidates respectively.

The complete paths from the old fold kernels to the new ones are replayable with
the existing independent beta-step checker. The native self-interpreter programs
are obtained by bracket abstraction to SK and the certified native encoding.
Their helpers are fully expanded, and no eta rewrite or interpreter opcode is
used in that compiler.

## Matched comparison with left-to-right Jot

The later optimizations also help the forward fold. Applying the same pipeline
to both directions gives:

| Basis | Direction | Ordinary kernel in BLC | Native self-interpreter | Reflective kernel in BLC |
| --- | --- | ---: | ---: | ---: |
| SK (Jot) | Left to right | 127 | 1,355 | 168 |
| SK (Nought's ordinary fold) | Right to left | **114** | **1,169** | **155** |
| KSK | Left to right | 136 | 1,187 | 177 |
| KSK | Right to left | **123** | **1,035** | **164** |

All four reflective variants have a zero-bit native self-interpreter. Both
directions use the same raw boolean-pair lists, expanded constants, compiler,
and reflection wrapper. Right-to-left scanning still saves **13 kernel bits**
for each basis, including after reflection. Nought retains its scan direction.

The forward fold passes an accumulator into each recursive call; the reverse
fold instead uses the recursively decoded tail as the accumulator. Each seed
expresses recursion by direct self-application, with a replayable common-reduct
proof connecting it to the original evaluator. Both receive 16 contraction
rounds, beam 128, and 100 bits of growth allowance, followed by two equivalence
rewrite rounds, beam 64, allowance 32, and a 20,000-candidate cap. Reflection
receives the same 16-round contraction search for every candidate.

The forward kernels contract to 129/138 bits and then rewrite to 127/136.
Their rewrite searches generate 10,683/13,600 candidates; all four searches
finish at the round limit, without reaching the candidate cap. These are
matched bounded searches, not a proof that reverse scanning is inherently
smaller or that either direction has reached its minimum.

Reproduce the comparison and its tests with:

```sh
python3 -m experiments.direction_search --report artifacts/searches/direction/metrics.json
python3 -m unittest -v tests.test_direction_search tests.test_reflective_fold
```

[`artifacts/searches/direction/metrics.json`](../artifacts/searches/direction/metrics.json) records all four kernels,
native self-interpreters, replayable proofs, settings, and implementation hashes.
Tests compare both directions on every nonempty source through six bits after
source reversal. Both forward native self-interpreters complete a bit-flip guest
from raw source, returning `001` for input `101`, with a 100-million-step budget.
The initial 10-million-step budget was insufficient for the SK version; the
size comparison is not a runtime comparison. Both forward reflective variants
also complete that guest through eight nested empty-program interpretation
levels. Existing reverse-fold tests remain in place.

## Explicit reflection at empty source

Let `F` be one of the optimized ordinary fold decoders. Define `R` by ordinary
lambda recursion:

```text
R []     = R
R (b:bs) = F (b:bs)
```

The implementation is the expanded closed term:

```text
(lambda s. s s)
(lambda s bits. bits (lambda head tail ignored. F bits) (s s))
```

With the unchanged pair-list representation, an empty list selects `s s`. A
nonempty list invokes the three-argument branch, which discards the empty-case
argument and evaluates `F` on the original list. The wrapper costs 41 BLC bits,
all included in the 155/164-bit kernel scores. There is no host `eval` primitive,
pre-parsing of input, or uncounted native-code dictionary.

For every finite raw source `p`, `R(bitlist(p))` is a closed lambda computation.
Every compiled SK program is nonempty, so the universal embedding is preserved.
Only the empty source changes its meaning.

If `epsilon` is the empty bitstring, then:

```text
meaning_R(epsilon) = R
meaning_R(epsilon) (bitlist(p)) (bitlist(x))
    = R (bitlist(p)) (bitlist(x))
    = run_R(p, x)
```

This holds for all raw guests, including epsilon. Thus epsilon is a native
self-interpreter, of length zero. Since finite bitstrings cannot have negative
length, this reaches the literal program-length minimum. The remaining research
question is how simple the language definition can be and what other costs its
representation imposes; zero is not a proof that the 155-bit kernel is minimal.

This construction deliberately includes empty-source reflection. It should not
be advertised as a shorter BLC interpreter, an improved universal Chaitin machine,
or a world record against Tromp. The ordinary bitfold compiler has substantial
encoding overhead for general programs. The result improves the explicit
measurements used here, while making the architectural tradeoff visible.

## Reproduction and validation

```sh
python3 -m languages.nought --report artifacts/nought/metrics.json --kernel artifacts/nought/kernel.blc --emit artifacts/nought/self.bits
python3 -m unittest -v tests.test_reflective_fold
```

[`artifacts/nought/kernel.blc`](../artifacts/nought/kernel.blc) contains all 155 bits of the
best language definition. [`artifacts/nought/self.bits`](../artifacts/nought/self.bits) is
intentionally empty. [`artifacts/nought/metrics.json`](../artifacts/nought/metrics.json) includes
both ordinary native self-interpreters, both ordinary and reflective kernels,
universality witnesses, rewrite proofs, search settings, and hashes. The source
hash and byte count are provenance for the full implementation and utilities,
not a substitute for the kernel's BLC measurement.

Tests replay the fixed-point and reduction proofs, verify preservation of all
nonempty sources through six bits, check constructive encodings of closed lambda
terms, and execute both ordinary native self-interpreters from raw source lists.
The reflective interpreters complete up to eight nested empty-program levels
while running a compiled bit-list transformation from `101` to `001`. Exhaustive
short-source checks verify closed construction and bounded execution; suspension
does not mean invalid syntax or prove divergence.
