# A 174-bit total functional candidate

The new candidate has a **174-bit self-interpreter**. Every finite source
bitstring denotes a closed lambda-calculus computation, including empty,
truncated, and conventionally unbound source strings. Some computations may
diverge, and some return values other than bit lists.

This is **not a new smallest-interpreter record**. It is an explicit total-domain
extension built around Tromp's existing 168-bit parser, with a six-bit adapter.
The contribution here is the implemented contract, independent execution checks,
completed nested interpretation, and reproducible local-search experiment.
Credit for the optimized parser belongs to Tromp, 50_ft_lock, and Sean Palmer.

The candidate is no longer NAND-based. The tape languages remain benchmarks.

## Definition and accounting

Let `E` be the 168-bit parser reconstructed from
[Tromp's intL, at a pinned revision](https://github.com/tromp/AIT/blob/2cfa384f11d462e77dfe96d3c5fefbecfa7ff432/ait/int.lam).
Let `I = lambda x. x`, and define:

```text
D = E I
meaning(p) = D (bits_as_list(p))
run(p, x) = meaning(p) (bits_as_list(x))
```

Programs are functions and may take further arguments by ordinary application.
The two-input self-interpreter contract uses this currying directly. `p` and `x`
are separately delimited finite bitstrings, not a single combined input stream.

The encoding of lambda terms is standard BLC:

| Term | Encoding |
| --- | --- |
| Abstraction `lambda body` | `00` followed by the body |
| Application `f x` | `01` followed by `f`, then `x` |
| Zero-based variable index `n` | `n+1` ones followed by zero |

Therefore `D` occupies two application bits, 168 parser bits, and the four-bit
identity `0010`: **174 bits in total**. All macros in the development notation
are expanded before measuring. The artifact is
[`artifacts/functional/self.blc`](../../artifacts/functional/self.blc); it has no ignored suffix or padding.

The parser's source construction initially measures 187 bits. A replayable
sequence of beta contractions reduces it to the published 168-bit size. This
calibrates both our encoding and our reconstruction; it is not counted as a new
optimization of Tromp's result.

Input representation uses ordinary Church booleans and pairs:

```text
0 = lambda a b. a
1 = lambda a b. b
pair(h,t) = lambda f. f h t
nil = lambda a b. b
```

A raw source string becomes a list of those booleans ending in `nil`. This
framing neither parses the source nor repairs it. The source list, external
input list, underlying lambda evaluator, and host output observer are not part
of the 174-bit program. The whole named reference module is measured separately
in [`artifacts/functional/metrics.json`](../../artifacts/functional/metrics.json), with a SHA-256 digest.
That file includes development and observation utilities and is not a minimized
implementation of the execution rules. The 174-bit kernel supplies the language
definition as well as its executable self-interpreter.

## What “every bitstring is valid” means here

The language frontend constructs `D (bits_as_list(p))`; it does not first ask a
native BLC parser to accept `p`. Both `D` and the list are closed finite lambda
terms for every finite `p`. Application therefore always yields a closed term.

Execution is deterministic call-by-name reduction using closures and an argument
stack. An application saves its argument and evaluates its function; a lambda
with a pending argument binds it and enters its body; a variable follows its
binding. A lambda without pending arguments is a weak-head value. From a closed
initial term no unbound variable can occur in this machine. Memory has no fixed
bound in the mathematical model, and a computation may run indefinitely.

This establishes defined execution for all finite source bitstrings. It does
**not** promise that parsing finishes before execution, that execution halts,
that a returned function has a full normal form, or that its result is a bit list.
This is a different totalization strategy from NAND tape's virtual-zero parser.

EOF is the explicit `nil` lambda value above, not a missing host-language
operand. Out-of-scope source indices likewise invoke functional binding lookup
inside `D`; they never become unbound variables in the host evaluator. The
complete kernel determines their behavior. There is no separate unspecified
error case. For example, the sources empty, `0`, `1`, `00`, and `01` all yield
identity under this definition.

For a complete closed BLC prefix, `D` returns the represented term and ignores
its suffix. For open or incomplete sources, that suffix can affect the result;
one should not generalize the closed-prefix rule to every source.

## Universality and self-interpretation

Tromp's parser has the following property for an encoded closed lambda term `M`:

```text
E continuation (encode(M) ++ remainder)
    = continuation (lambda environment. M) remainder
```

The bitstream notation here stands for the corresponding boolean lists. Setting
the continuation to `I` applies that environment wrapper to the remaining list,
yielding `M`. Thus `D (bits_as_list(encode(M)))` reproduces every closed lambda
term. This embeds the untyped lambda calculus, a known universal model, into the
candidate without excluding other finite bitstrings from its domain. See
[Tromp's parser theorem](https://tromp.github.io/cl/LC.pdf).

Now let `q = encode(D)`. Because `D` is closed:

```text
meaning(q) = D
meaning(q) (bits_as_list(p)) (bits_as_list(x))
    = D (bits_as_list(p)) (bits_as_list(x))
    = run(p, x)
```

This holds for every `p`, including malformed conventional BLC, because the
closed-prefix theorem is needed only for `q`. There is no native `eval` opcode:
the source bits are decoded by the emitted lambda program itself. Divergence
is preserved by this functional equivalence; finite tests alone do not prove it.

## Comparison with Tromp and NAND tape

| Artifact | Bits | Contract |
| --- | ---: | --- |
| Tromp's optimized parser `E` | 168 | Continuation, decoded environment wrapper, and remaining stream |
| This candidate `D = E I` | **174** | Raw source list to a function; external input is a separate argument |
| Tromp's universal machine | 190 | Decode a closed program and apply it to the remaining input stream |
| Compact NAND tape self-interpreter | 25,260 | Framed source and guest tape; output is the represented guest state |

The 174-bit artifact is six bits larger than Tromp's parser. Its being shorter
than the 190-bit universal machine is **not a record improvement**: the interfaces
and handling of source/input boundaries differ. In particular, this candidate
gets the boundary between source and input from its caller. Tromp also publishes
a 178-bit non-strict universal variant, another reason not to present 190 as a
universal lower benchmark. See his
[universal-machine source](https://github.com/tromp/AIT/blob/master/ait/uni.lam).

Likewise, the large reduction from NAND tape is an architectural observation,
not a controlled comparison with identical framing, output, and evaluation
contracts. The functional machine provides application and binding directly;
the tape interpreter implements its guest's storage and control explicitly.
Both contracts are documented so that these differences remain visible.

## Tests and execution

```sh
python3 -m experiments.functional_candidates --run 0010 --input 101101
python3 -m experiments.functional_candidates --run '' --input 101101
python3 -m experiments.functional_candidates --search --emit artifacts/functional/self.blc --report artifacts/functional/metrics.json
python3 -m unittest -v tests.test_functional
```

The first two examples echo `101101`: one uses the conventional identity program,
the other the candidate's defined empty-source behavior. Output observation has
a separate bit limit and step budget. `suspended` means budget exhaustion;
`non-list-value` or `non-bit-value` describes an observation, not a syntax error.

The tests cover:

- All 511 raw sources through eight bits, checking closed construction and
  defined bounded execution.
- All 226 closed BLC terms through sixteen bits, comparing decoded and native
  full normal forms using the reference evaluator.
- Capture avoidance, lazy argument handling, EOF behavior, ignored suffixes for
  closed programs, bit-list processing, and a known divergent computation.
- Completed self-interpretation on raw and well-formed sources, and two completed
  nested levels echoing a bit list.
- Calibration to 168 bits, replay of beta-reduction certificates, and exact
  regeneration of the 174-bit artifact and its measurement report.

For the identity guest on input `101`, observation takes 464 reference-machine
steps directly, 20,312 through one self-interpretation level, and 220,361 through
two. These are implementation-specific counts, not a complexity theorem.

## Search result and limits

The bounded beta-contraction search considered **115 distinct new reducts** with
the recorded settings: 20 rounds, beam width 256, and up to 400 bits of temporary
size growth. It found no term shorter than the 174-bit seed. Its proof paths are
replayable, so an accepted change cannot silently alter arbitrary-source behavior.

This search does not explore all equivalent terms, reverse reductions, alternate
encodings, combinator bases, or alternative evaluators. It proves no lower bound
and is not evidence that 174 is optimal. Nor is assigning semantics to arbitrary
inputs of a closed functional evaluator claimed as a new idea.

The immediate research milestone is a small, tested, explicitly total-domain
candidate competitive in size with Tromp's constructions. Beating his 168-bit
parser under a genuinely comparable contract remains open in this project.
Future comparisons should first fix whether the score is for a parser, a
two-argument interpreter, or a single-stream universal machine.

The subsequent [bit-by-bit combinator experiment](bitfold.md) holds this separate
program/input list contract fixed and measures self-interpreters in their own
native encoding. Its best emitted result is 1,339 bits; the 174-bit candidate
above remains unchanged.

The subsequent [equivalence-rewrite search](rewrite_search.md) adds inverse beta
steps, helper factoring, applied-parameter exchange, larger retained intermediates,
and a certified alternative starting form. Its three bounded runs generated
912,292 candidates in total (with overlap between runs) and found no improvement
below 174 bits. The original contraction-only result above remains reproducible.

The [joint encoding/decoder experiment](encoding_search.md) then tested 24
constructor-tag assignments and unary-index polarities, scoring each generated
decoder in its own encoding. The baseline calibrates exactly, and the best
remains 174 bits after 728,254 generated candidates across variants and phases.
