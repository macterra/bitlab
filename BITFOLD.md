# Bit-by-bit combinator experiment

**This experiment did not beat the 174-bit functional baseline.** The baseline
Jot self-interpreter is 1,799 bits in Jot. The smallest emitted self-interpreter
in the bounded neighboring search is **1,339 bits in its own language**.

That best evaluator is only 157 bits when expressed in BLC. Counting those 157
bits as its self-interpreter would be wrong: that is a cross-language description,
not a program in the candidate's own language.

The input/output contract is held fixed with [the functional candidate](FUNCTIONAL.md):
raw program and input are separate boolean-pair lists, and output is observed
as a bit list. Both use the same `functional.py` evaluator and framing functions.
The comparison therefore avoids the interface mismatch with Tromp's 168-bit
parser, which takes an additional continuation argument.

## Execution without a structured source parser

The starting point is Chris Barker's Jot, existing prior art rather than a new
invention. Barker's original *Iota and Jot: the simplest languages?* is also
recorded in the bibliography of Michael Stay's
[2005 thesis](https://math.ucr.edu/~mike/mscthesis/thesis.pdf).

Use the standard combinators:

```text
I x = x
K x y = x
S x y z = x z (y z)
B f x y = f (x y)
```

Begin with state `I`. For each source bit, left to right:

```text
0: state = state S K
1: state = B state = S (K state)
```

The resulting state is the program's meaning, and it is applied to the external
input. Each transition constructs a finite closed expression from the previous
one. Thus every finite bitstring has a meaning, including empty. There are no
variable indices, instruction boundaries, syntax errors, or EOF repairs. Folding
the source into an expression always finishes; reducing that expression need not.

The neighboring family replaces `S K` in the zero rule with a chosen sequence
of constants, such as `K S K`. It also permits swapping the bit labels or reading
the source right to left. All of these definitions give meaning to every finite
string; universality must be established separately for each constant sequence.

## Constructive universality certificates

Write `F_word(a)` for folding a word starting from an arbitrary accumulator `a`.
The search looks for words satisfying, by beta reduction:

```text
F_k(a) = a K
F_s(a) = a S
```

It checks full normal forms of terms with a symbolically bound accumulator,
not a few concrete accumulator values. Successful finite reductions provide
recheckable witnesses. The certificates found were:

| Zero-rule constants | K word | S word |
| --- | --- | --- |
| `S K` | `11100` | `11111000` |
| `K S K` | `1111100` | `110` |

For example, three `1` steps transform `a` into a function taking four arguments
and passing their left-associated application to `a`. In the first row, `11100`
then supplies `S K S K`, which reduces to `K`. In the second row, `110` supplies
`K S K` after two `1` steps, giving `a ((K S) K) = a S`.

These witnesses extend to a compiler for all SK terms:

```text
encode(K)   = k
encode(S)   = s
encode(M N) = 1 ++ encode(M) ++ encode(N)
```

For the application case, the leading `1` changes `a` into `B a`. By induction,
the rest produces `(B a) M N = a (M N)`. With initial accumulator `I`, every SK
term is therefore reproduced. Standard bracket abstraction translates every
closed lambda term to SK, giving a constructive universality argument.

Swapped-bit languages flip the compiled bits. Reverse-scan languages reverse
the compiled string. These transformations preserve the same simulation proof;
they are not new unproved universality claims.

## Self-interpreters and native encoding

The emitted interpreter folds the raw source's boolean list. Its recursion,
initial accumulator, bit choice, and constant definitions are included in the
generated program. No host callback interprets guest instructions. Python
provides only the fixed reference reduction machine and raw-list framing.

The left-to-right version threads an accumulator through the list. The reverse
version interprets the tail first and then applies the head bit's transformation.
For the latter we compare duplicating the recursive expression with binding it
once in the source expression. This binding does not add memoization to the
call-by-name reference machine.

Each interpreter is compiled to S/K/application with bracket abstraction and
then encoded using the certified native words. Both a basic compiler and a
locally costed compiler with expanded B/C alternatives are measured. No eta
contraction or hidden primitive combinator is used. B and C are expanded into
S and K before the native bit count is taken.

The fixed-point combinator is explicitly included. All initializer and helper
code is counted; external raw input framing is unchanged from the functional
baseline. The larger report also measures the full reference modules
`functional.py` and `bitfold.py`, concatenated in that order, with their hash.
Those file sizes include development utilities and are not semantic lower bounds.

## Bounded search and results

The search covered the nine ordered pairs over `{S,K,I}` and the eight ordered
triples over `{S,K}`: **17 constant sequences**. It tried witness words through
length ten, stopping a sequence's search after finding both witnesses. Across
the sequences it checked **31,461 words**, with a normalization budget of 10,000
reference steps per word. Eight checks hit a normalization/resource limit.

Two sequences were certified. The other fifteen are **uncertified within this
search**, not proved nonuniversal. For the two certified sequences, bit polarity
and scan direction give eight languages. The implementation choices produce
24 measured configurations and 12 distinct emitted bitstrings.

| Zero-rule constants | Scan direction | Evaluator in BLC | Native self-interpreter |
| --- | --- | ---: | ---: |
| `S K` | Left to right | 161 bits | 1,799 bits |
| `S K` | Right to left, shared recursive expression | 148 bits | 1,529 bits |
| `K S K` | Left to right | 170 bits | 1,555 bits |
| `K S K` | Right to left, shared recursive expression | 157 bits | **1,339 bits** |

Swapping the bit labels did not change these lengths. Neither compiler option
improved the scores in this run. The best artifact is about 7.7 times the size
of the existing 174-bit candidate, despite the simpler source-processing rule.

Artifacts:

- [`jot_self.bits`](jot_self.bits) and [`jot_metrics.json`](jot_metrics.json): baseline.
- [`bitfold_self.bits`](bitfold_self.bits): best measured configuration, using
  `K S K`, ordinary bit polarity, and right-to-left scanning.
- [`bitfold_metrics.json`](bitfold_metrics.json): all certificates, configurations,
  scores, settings, and hashes.

## Validation and use

```sh
python3 bitfold.py --run '' --input 101
python3 bitfold.py --emit jot_self.bits --report jot_metrics.json
python3 bitfold.py --survey --emit bitfold_self.bits --report bitfold_metrics.json
python3 -m unittest -v test_bitfold
```

`--run` alone executes baseline Jot; combined with `--survey`, it executes the
best measured variant. Neither runner interprets artifact filenames as source:
the option accepts literal program bits. The best artifact must be evaluated
with its recorded constants, polarity, and direction.

The tests verify the symbolic universality witnesses, compositional application,
bracket abstraction, and all 24 emitted interpreters executing their own encoded
source language. They also cover all 511 strings through eight bits for both
certified constant choices and compare the functional fold against the native
rule on all strings through five bits in all eight certified languages.

The best self-interpreter completes a program that flips the first input bit:
`101` becomes `001`, matching direct execution. Through self-interpretation that
case takes 9,814,530 reference-machine steps. A separate two-level nesting
experiment exhausted five million steps without finishing; that observation is
not a proof of divergence. No runtime speedup is claimed.

## What this tells us

Eliminating parsing made the evaluator's lambda description smaller, but did
not make its native representation small. The cost moved into expressing the
recursive evaluator with the candidate's own primitive words. This experiment
therefore fails the proposed under-174-bit success criterion.

The results are upper bounds from particular compilers and witness words, not
minimum program sizes for these languages. The bounded search omits longer
witnesses, other bases, eta-based compilation, alternative fixed points, and
native superoptimization. A short native interpreter could still exist.

The next useful optimization target is the native encoding and compiler,
especially recursion and abstraction, rather than the apparent size of a fold
written in another language. The 174-bit candidate remains the smallest measured
self-interpreter at that stage under the separate-list contract.

The later [Nought construction](REFLECTIVE_FOLD.md) improves the ordinary
SK/KSK kernels to 114/123 BLC bits and their native self-interpreters to
1,169/1,035 bits. An explicitly measured empty-source reflection extension gives
a zero-bit self-interpreter with a 155-bit kernel; the earlier artifacts above
remain unchanged as reproducible baselines.
