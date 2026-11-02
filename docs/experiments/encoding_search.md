# Joint encoding and decoder experiment

**None of the 24 variants beat the existing 174-bit self-interpreter.** The
experiment changes the source codes and their decoder together, measuring each
decoder in the language it interprets. The reference lambda machine and the
separate raw program/input boolean-list contract remain fixed.

The generator exactly reproduces the existing 187-bit parser seed for the
original encoding. Optimizing that parser with its identity adapter recovers
the same **174-bit artifact**, not merely a different program of equal size.
This calibrates the experiment against [the functional baseline](functional.md)
and preserves the attribution there to Tromp and the parser's optimizers.

## The 24 languages

A source represents an untyped lambda term with zero-based de Bruijn indices.
There are three kinds of syntax: abstraction, application, and variable.

There are two full binary prefix trees with three leaves:

```text
{0, 10, 11}
{00, 01, 1}
```

Assign the three kinds to the leaves in all six orders. After a variable tag,
encode index `n` with `n` repetitions of one bit followed by the opposite bit.
Both polarities are tried. Thus the family has `2 * 6 * 2 = 24` members.

For the original encoding, the tags are `00` for abstraction, `01` for
application, and `1` for variable. The unary suffix is `1^n 0`, so the complete
variable encoding is `1^(n+1) 0`, exactly standard BLC.

The report names variants with a key such as `L00-A01-V1-U1`: the `L`, `A`,
and `V` fields give the tags, and `U` gives the unary repetition bit. Tags alone
do not specify the full language; the generated closed decoder also determines
what incomplete and otherwise unconventional source strings do.

## Generated decoders and defined execution

[`experiments/encoding_search.py`](../../experiments/encoding_search.py) generates a continuation-passing
parser for each tree. It reuses two techniques from the baseline construction:

- A raw unary suffix also acts as an environment selector.
- When abstraction and application are sibling leaves, their first recursive
  parse is shared before choosing how to use the parsed expression.

Both techniques are applied wherever the tree and unary orientation permit
them, rather than reserving a special parser implementation for the baseline.
When the unary stopping bit is zero, the baseline's compact `s s s` skipping
expression works unchanged. For the opposite polarity the generator uses an
explicit recursive skipper. That implementation choice contributes to the
larger measured sizes for the second polarity; it is not a lower bound on its
possible decoder size.

Let `E_e` be the generated parser for encoding `e`, and `D_e = E_e I`. Define:

```text
meaning_e(p) = D_e (bitlist(p))
run_e(p, x)  = meaning_e(p) (bitlist(x))
```

Each `D_e` is a finite closed lambda term. So is `bitlist(p)` for **every finite
bitstring** `p`. Their application therefore has defined execution without a
host syntax check. It may diverge or return a value that is not a bit list.
EOF is the same ordinary `nil` value as in the baseline, not a host parser
exception or an external source-repair operation.

`Encoding.parse` is a strict inspection utility for artifacts and round-trip
tests. It is not used to define the languages' arbitrary-source semantics.

## Universality and self-interpretation argument

For a proper binding environment, a cell has the following behavior. Write
`h` for its value, `t` for its tail, and `rest` for the remaining unary source:

```text
repeat 1, stop 0: cons h t choose rest = choose h (rest t)
repeat 0, stop 1: cons h t choose rest = choose (rest t) h
```

A source suffix `repeat^n stop` therefore selects the `n`th binding. The stop
case returns the cell's head; the repetition case invokes the remaining suffix
on its tail. Bits following the stopping bit are unused by that lookup. The
skipper returns exactly those following bits to the parser's continuation.

This proves the variable case of the parser simulation. The other cases follow
by induction on the encoded term:

- **Abstraction:** decode its body and construct a function that extends the
  environment with its argument before interpreting the body.
- **Application:** decode the left and right subterms in sequence, then apply
  their interpretations in the same environment.

The tag decision tree selects the appropriate case and consumes exactly its
tag. The unary selector and skipper consume exactly the variable suffix.
Consequently, interpreting an encoded term in an environment containing all
its free bindings reproduces that term with those bindings and returns the
exact unused source suffix to the continuation.

For a **closed** term `M`, the initial environment is never inspected. In this
case the baseline continuation argument applies unchanged:

```text
E_e c (encode_e(M) ++ remainder)
    = c (lambda environment. M) remainder
D_e (encode_e(M) ++ remainder) = M
```

Bitstring expressions stand for their boolean lists. These are beta-equivalence
claims, not guarantees that evaluating a possibly divergent `M` terminates.
Thus every closed lambda term has a representation, establishing universality
for all 24 languages. Complete closed prefixes ignore their suffixes; this is
not asserted for every malformed or incomplete source.

Now let `q_e = encode_e(D_e)`. Because `D_e` is closed, decoding `q_e` returns
`D_e`. Applying it to any raw guest `p` and external input `x` therefore gives
`run_e(p, x)`. The same argument applies to an optimized decoder beta-equivalent
to the seed. This establishes self-interpretation for arbitrary guests, not just
conventionally valid source terms. The argument is mathematical; executable
tests and rewrite certificates support the implementation but are not a
formalization in a proof assistant.

## Optimization and accounting

Each decoder undergoes two deterministic searches:

| Phase | Rounds | Beam | Allowed native growth | New-candidate cap |
| --- | ---: | ---: | ---: | ---: |
| Beta contraction | 12 | 64 | 128 bits | 20,000 |
| Equivalence rewrites | 6 | 32 | 32 bits | 30,000 |

The second phase uses the previous experiment's contraction, helper extraction,
and applied-parameter exchange rules. Both phases rank and bound candidates by
**their own encoding's bit length**. The old rewrite generator's BLC growth
filter is disabled; the replacement filter uses native cost.

Every emitted kernel has a replayable beta-equivalence trail from its generated
seed. Replacement terms inside proof files use standard BLC as a serialization
format for the checker. That format does not contribute to or substitute for
the native self-interpreter score. All decoder helpers, recursion, and the
identity adapter are expanded and included in that score.

The searches generated 10,088 candidates during contraction and 718,166 during
rewriting: **728,254 in total**. Terms are deduplicated within each phase, not
across phases or variants. Counts include candidates rejected by size limits;
they do not mean every generated term was expanded. No rewrite phase improved
on its contraction-phase starting size.

## Results and a cost constraint

Four tag assignments have each row's combination of short-tag kind and unary
polarity. They produced the same sizes within that group:

| One-bit tag | Unary suffix | Generated decoder | Best native interpreter |
| --- | --- | ---: | ---: |
| Variable | `1^n 0` | 193 | **174** |
| Application | `1^n 0` | 214 | 192 |
| Abstraction | `1^n 0` | 221 | 202 |
| Variable | `0^n 1` | 228 | 215 |
| Application | `0^n 1` | 249 | 233 |
| Abstraction | `0^n 1` | 257 | 244 |

There is a useful structural constraint behind these results. For any lambda
term, let `V`, `A`, and `L` count variable occurrences, applications, and
abstractions. Its syntax tree has unary abstraction nodes and binary application
nodes, so **`V = A + 1`**. Changing the one-bit tag from variable to application
saves one bit per application but adds one per variable. For the *same term*,
the result is always **one bit longer**, independently of the actual code labels
or unary polarity.

Giving abstraction the short tag changes the same term's size by `V - L`.
The existing decoder has `V = 28`, `A = 27`, and `L = 17`, so that reassignment
would add 11 bits before any decoder changes. The actual co-designed decoder
sizes above also reflect changes to parsing, and the identities do not prove
that another decoder implementation could not do better.

## Artifacts and validation

```sh
python3 -m experiments.encoding_search --report artifacts/searches/encoding/metrics.json --emit artifacts/searches/encoding/self.bits
python3 -m experiments.encoding_search --no-rewrite
python3 -m unittest -v tests.test_encoding_search
```

[`artifacts/searches/encoding/metrics.json`](../../artifacts/searches/encoding/metrics.json) records all 24 native programs,
their encodings, settings, per-phase results, proof trails, and hashes. It also
records the sizes and hash of the concatenated reference/search source files in
the listed order; this is experiment provenance, not a minimized language
implementation. [`artifacts/searches/encoding/self.bits`](../../artifacts/searches/encoding/self.bits) is the best artifact,
which is identical to `artifacts/functional/self.blc`.

The tests cover the family and codecs, exact baseline calibration, all 226 closed
BLC terms through 16 bits translated into all 24 encodings (with and without a
suffix), open-term binding lookup and exact remainders, and bounded execution
for all 127 raw strings through six bits in every language. They also check
certificate replay and artifact hashes, native cost identities, and a positive
control where helper extraction shortens a term.

Native self-interpretation is checked for every variant, including a bit-list
program that changes `101` to `001` and two full nested interpretation levels
that return `101`.

## Limits and implications

The family of 24 code assignments is exhausted, but the space of interpreters
for each assignment is not. Each row is an upper bound from one parameterized
parser construction and bounded optimization. No global minimality result or
new smallest-interpreter record follows.

This family changes tags while retaining the same three syntax constructs and
unary indices. The cost identities explain why merely making application's tag
shorter is unhelpful for a fixed term. A materially different next family would
need to change more than those tag lengths, such as the representation of
binding or repeated variable references, and count the corresponding decoding
logic in full.
