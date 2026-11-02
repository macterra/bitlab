# nand

Exploring a minimal universal language where every finite bitstring is a valid
program. Our main benchmark is the length of a language's self-interpreter,
measured in bits, with explicit input framing and a companion measurement of
the reference implementation.

The current [reflective bitfold construction](REFLECTIVE_FOLD.md) has a **zero-bit
native self-interpreter and a 155-bit decoder kernel**, under the original raw-list
interface. Its ordinary version has a 114-bit kernel and a 1,169-bit native
self-interpreter. These are distinct measurements, both reported explicitly.

The earlier [174-bit functional candidate](FUNCTIONAL.md)
gives every finite bitstring a defined lambda-calculus computation and
completes nested self-interpretation. It is a six-bit adapter around Tromp's
168-bit parser, **not a new smallest-interpreter record**. Its input contract is
explicit and differs from a single-stream universal machine.

The [open research direction](RESEARCH.md) now allows changes to architecture,
representations, and interfaces. Its first benchmark diagnostic constructs a
**zero-bit self-interpreter with a 215-bit decoder kernel**: empty source denotes
the decoder itself. This reaches the literal program-length floor while making
the language definition larger, so we track both measurements instead of
treating self-interpreter length alone as language simplicity.

The [triage-calculus prototype](TRIAGE.md) explores a different runtime with one
native tree operator and five rewrite rules. Its self-interpreters measure 329
bits with quoted-tree input and 987 bits with raw binary input; both execute their
own source. The input contracts and parser cost are recorded separately.

The initial [bit-by-bit combinator experiment](BITFOLD.md) tested a different
execution rule with no structured source parser. Its best emitted self-interpreter
was 1,339 native bits across 24 measured configurations, so it did not improve on
174 bits. Universality certificates and the negative result are preserved.

The [equivalence-rewrite search](REWRITE_SEARCH.md) explores helper
factoring and larger intermediate expressions with replayable beta proofs.
Three bounded runs generated 912,292 candidates (overlapping between runs)
without improving that experiment's 174-bit baseline.

The earlier [joint encoding/decoder experiment](ENCODING_SEARCH.md) tests all 24
assignments of short constructor tags and unary-index polarities. Its 728,254
generated candidates also found nothing below 174 bits in that family, with a native interpreter
and decoding checks for every variant.

```sh
python3 functional_candidates.py --run 0010 --input 101101
python3 functional_candidates.py --run '' --input 101101
python3 -m unittest -v test_nand_tape test_self_host test_compact_tape test_functional test_bitfold test_functional_rewrites test_encoding_search test_empty_interpreter test_triage test_reflective_fold
```

| Candidate | Self-interpreter | Documentation |
| --- | ---: | --- |
| Reflective bitfold | **0 bits**; 155-bit kernel | [Construction and both size measurements](REFLECTIVE_FOLD.md) |
| Total functional decoder | **174 bits** | [Contract, provenance, and search results](FUNCTIONAL.md) |
| Empty-program boundary case | **0 bits**; 215-bit kernel | [Why both measurements matter](RESEARCH.md) |
| Triage raw-bit interpreter | 987 bits | [Native tree runtime and input contracts](TRIAGE.md) |
| Optimized ordinary bitfold (KSK) | 1,035 bits; 123-bit kernel | [Certificates and optimizations](REFLECTIVE_FOLD.md) |
| Compact binary addresses | **25,260 bits** | [Specification and comparison](COMPACT_TAPE.md) |
| Original unary addresses | 741,267 bits | [Language](NAND_TAPE.md), [self-interpreter](SELF_INTERPRETER.md) |

These models have different execution and input/output contracts; the table is
an inventory of measured artifacts, not a controlled ranking. The functional
candidate uses application and binding, while the tape languages use NAND,
movement, and branching. None is claimed to be globally minimal.

The tape dialects remain available through `nand_tape.py` and `compact_tape.py`;
their bitstrings are not generally interchangeable. Their self-interpreters and
measurements are preserved as baselines.

Regenerate the functional artifact and its measurement report:

```sh
python3 functional_candidates.py --search --emit functional_self.blc --report functional_metrics.json
```

The 77 tests cover differential execution, exhaustive short sources, large tape
branch addresses, and reproducible artifacts. The functional suite completes two
nested interpretation levels; the tape suites check bounded self-application
prefixes. The functional search found no reduction below 174 bits within its
recorded limits. Beating Tromp under a genuinely comparable contract remains an
open research question in this project.

## Original expression-language experiment

The notation below belongs to the earlier `nand.py` interpreter. It is separate
from the NAND tape prototype.

```
00 = 0
01 = 1
1xy = (nand x y) = (not (and x y))
```

```
101x = (nand 1 x) = (not (and 1 x)) = (not x)
100x = (nand 0 x) = (not (and 0 x)) = (not 0) = 1

10000 = (not (and 0 0)) = (not 0) = 1
10001 = (not (and 0 1)) = (not 0) = 1
10100 = (not (and 1 0)) = (not 0) = 1
10101 = (not (and 1 1)) = (not 1) = 0

101100x = (not (nand 0 x) = (not 1) = 0
101101x = (not (nand 1 x) = (not (not x) = x

1011xy = (not (nand x y) = (and x y)
1101x101y = (nand (not x) (not y)) = (or x y)

1x101y = (nand x (not y)) = (not (and x (not y))) = (or (not x) y) = x -> y
1101xy = (nand (not x) y) = (not (and (not x) y)) = (or x (not y)) = x <- y

1011100xy = (not 1100xy) = (not (nand 100x y)) = (and 1 y) = y
```
