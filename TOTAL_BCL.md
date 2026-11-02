# Totalized BCL: compact programs with no invalid bitstrings

This candidate preserves BCL's short encoding of every complete SK tree, gives
every finite bitstring a meaning, and optionally makes the empty program a
self-interpreter. It is a separate language experiment; Nought's reverse-fold
definition remains unchanged.

| Measurement | Nought | Reflective totalized BCL |
| --- | ---: | ---: |
| Rule 30 guest program | 1,979 bits | **809 bits** |
| Decoder kernel in BLC | **155 bits** | 261 bits |
| Native self-interpreter | 0 bits | 0 bits |
| Incomplete sources | Fold semantics | Complete missing pieces with K |
| Suffix after a complete SK expression | Whole source is folded | Unused |

The 809-bit Rule 30 program computes the same five demonstrated generations as
the existing Nought program. These are guest sizes, excluding the separate
decoder, input, and host display loop. The new candidate achieves compact guest
programs and total syntax, but does not improve every measurement: its kernel
is 106 bits larger. Neither implementation is claimed minimal.

## Source semantics

Use the BCL convention:

```text
00         K
01         S
1 <f> <x>  application of f to x
```

The choice of which two-bit atom denotes S or K does not affect lengths.
See [Tromp's BCL specification, section 3.1](https://tromp.github.io/cl/LC.pdf).

The ordinary decoder parses the first expression with two EOF rules:

1. If a term is needed but no bits remain, supply K.
2. If a source ends after the atom prefix `0`, supply K.

Thus empty ordinary source and `0` denote K; `1` denotes K K, with both
operands supplied at EOF. `10001` denotes K S. `00` followed by any suffix
denotes K: the remaining bits are unused, not appended to the external input.

All complete BCL codes retain their meaning and length. Every other finite
source can be completed into a finite SK tree: a real application marker
consumes a bit, and an empty recursive call supplies a leaf without recursing
again. Consequently there are no source syntax errors. Evaluation of the
resulting combinator can still diverge or return a non-bit-list value.

The reflective decoder changes only the empty source:

```text
R []     = R
R (b:bs) = D (b:bs)
```

Every SK tree has a nonempty encoding, so this change preserves the universal
embedding. Its empty program is a self-interpreter for all raw source strings,
including itself. Universality follows directly from preservation of K, S,
and application, not from the finite tests.

Complete BCL tree encodings remain prefix-free. The extended set of accepted
source strings is all finite bitstrings and is not prefix-free. Program and
input are separately framed, using exactly the repository's existing raw
boolean-pair lists. No host repair or padding pass is involved: EOF handling
and reflection are included in the measured lambda kernel.

## Implementation and measurements

[`total_bcl.py`](total_bcl.py) constructs a continuation-passing lambda parser.
Its continuation receives the decoded expression and unused suffix. Recursive
application parsing consumes two expressions; the top-level continuation
returns the first decoded expression and discards the remaining source.

A bounded contraction and equivalence-rewrite search reduces the ordinary
decoder from a 238-bit seed to 220 bits. The standard 41-bit reflection wrapper
gives 261 bits. The ordinary native self-interpreter is 1,172 BCL bits; the
reflective one is zero bits. All transformations have replayable beta proofs.
The ordinary rewrite search reaches its 20,000-candidate limit, so these scores
are search results rather than lower bounds.

The compiler uses the existing SK bracket abstraction with BCL's two-bit atom
costs. Rule 30 compiles to 120 S nodes, 150 K nodes, and 269 applications, giving
`2*(120+150)+269 = 809` bits. No new combinator or special interpreter opcode is
introduced.

Generate all artifacts:

```sh
python3 total_bcl.py --report total_bcl_metrics.json --kernel total_bcl_kernel.blc --emit total_bcl_self.bits --rule30 total_bcl_rule30.bits
```

Run one Rule 30 generation from the saved native program:

```sh
python3 total_bcl.py --run-file total_bcl_rule30.bits --input 0000001000000
```

The execution result is `0000011100000`, taking 167,129 reference-machine steps
for this generation. To exercise arbitrary raw source:

```sh
python3 total_bcl.py --run 11010000 --input 101
```

Here `11010000` encodes S K K, so the output is `101`.

```sh
python3 -m unittest -v test_total_bcl
```

Tests compare every raw string through seven bits with an independent completing
tree parser, check unused suffixes and artifact reproduction, replay the kernel
proofs, execute the ordinary native self-interpreter, and run Rule 30 through
eight nested empty-program interpretation levels. They also reproduce the five
13-cell generations from the Nought example. The measurements and complete
proofs are saved in [`total_bcl_metrics.json`](total_bcl_metrics.json).
