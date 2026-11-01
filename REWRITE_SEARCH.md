# Searching beyond beta contraction

This experiment searches for a shorter program implementing the **same**
[174-bit functional decoder](FUNCTIONAL.md). The language, BLC encoding,
separate raw program/input lists, and call-by-name evaluator are held fixed.
Every accepted improvement must come with a replayable beta-equivalence proof.

**Result: no improvement below 174 bits.** The three runs generated 912,292
candidate terms in total, with overlap between runs. The emitted artifact is
byte-for-byte identical to `functional_self.blc`.

## Why broaden the search?

The original contraction-only search generated 115 distinct new terms. It could
substitute an argument into a function, but could not introduce a helper or
recover a structure removed by a previous substitution.

Factoring can shorten a term even when there is nothing to reduce. For example,
the test suite factors a repeated function in the following beta-normal term:

```text
lambda f.
  f (lambda a b c d e. a (b (c (d e))))
    (lambda a b c d e. a (b (c (d e))))
```

The original occupies 84 BLC bits; the factored expression occupies 55. This is
a test of the optimizer, not an improvement to the decoder benchmark.

## Rewrites and proof checking

[`functional_rewrites.py`](functional_rewrites.py) implements three rules:

1. **Beta contraction.** Substitute an argument into a lambda body.
2. **Helper extraction.** Replace selected occurrences of an expression with a
   fresh bound variable and pass the expression as that binding's argument.
   One beta contraction must recover the exact original expression.
3. **Applied-parameter exchange.** Exchange two adjacent binders and their
   supplied arguments, updating variable references. Reducing the two argument
   applications on each side must produce the same expression.

Helpers can reference variables in the extraction scope. Moving an expression
past a lambda that binds one of its free references is rejected. The generator
can extract all matching occurrences, individual occurrences, and, when enabled,
every nonempty subset for groups of at most six occurrences. Larger groups still
allow individual and whole-group extraction.

The proof checker does not invoke the search or rewrite generators. It reads
replacement terms from BLC, rejects unconsumed suffixes, checks the supplied
reductions using the existing capture-avoiding beta operation, and verifies
that each resulting whole program is closed. An expansion contracts back to
the previous term; a parameter exchange has a common certified reduct. These
steps establish beta equivalence, including behavior on arbitrary source lists.

There are no eta rewrites, new interpreter primitives, or unproved substitutions
between fixed-point combinators. In particular, identifying two functions by an
extensional eta rule would require care under our weak-head evaluation contract.

The checker is an executable certificate verifier over the existing Python
lambda kernel, not a proof assistant or an independent formal verification of
that kernel. Tests exercise binding, capture avoidance, corrupt certificates,
unused divergent arguments, and normal-form agreement for generated rewrites.

## Search strategy and reproducibility

The search uses actual BLC length, including the unary cost of variable indices.
It permits temporary size growth, remembers previously generated terms, and
retains a bounded frontier after each round. Two selection policies are available:

- `size`: retain the shortest candidates, breaking ties by encoded bits.
- `layers`: distribute slots in successive passes across occupied bit lengths,
  starting with the shortest, so larger intermediates can be explored.

An optional second starting point restores the original 193-bit decoder source.
Its three-step expansion proof reverses the previously verified calibration
from the 187-bit parser to the 168-bit parser, with the six-bit adapter attached.
The 174-bit incumbent and its semantics remain the reference for every run.

The fixed suite uses these settings:

| Run | Starts | Rounds | Beam | Allowed growth | Selection | Occurrence subsets |
| --- | --- | ---: | ---: | ---: | --- | --- |
| 1 | 174-bit decoder | 12 | 64 | 32 bits | Size | Individual/all |
| 2 | 174-bit decoder | 16 | 64 | 192 bits | Layers | Enabled |
| 3 | 174- and 193-bit forms | 16 | 128 | 64 bits | Layers | Enabled |

Each run also has a distinct-candidate cap: 500,000, 300,000, and 500,000,
respectively. Counts include generated terms rejected by the size ceiling;
only the retained frontier is expanded in the following round. Counts are
deduplicated within each run, but **not across runs**. Initial seed terms do not
count as newly generated candidates.

```sh
python3 functional_rewrites.py --suite --report rewrite_metrics.json --emit rewrite_self.blc
python3 -m unittest -v test_functional_rewrites
```

Single-run settings can be varied with `--rounds`, `--beam`, `--slack`,
`--policy`, `--subsets`, `--source-start`, and `--max-generated`. `--suite` uses
the fixed table above instead of those single-run settings.

[`rewrite_metrics.json`](rewrite_metrics.json) records settings, per-round
counts and retained size ranges, stopping reasons, proof trails, and artifact
hashes. It also hashes the concatenated search/reference source files in the
recorded order. That source measurement documents the experiment; it is not a
new runtime-language size score. [`rewrite_self.blc`](rewrite_self.blc) contains
the best emitted interpreter. The existing functional and bitfold artifacts
remain unchanged.

## Measured outcome

| Run | New candidates | Largest retained term | Best | Stopping reason |
| --- | ---: | ---: | ---: | --- |
| 1 | 130,323 | 188 bits | 174 bits | 12 rounds |
| 2 | 281,969 | 351 bits | 174 bits | 16 rounds |
| 3 | 500,000 | 238 bits | 174 bits | Candidate cap during round 16 |

The best proof is empty because no shorter term was found. Nonempty proofs are
exercised by the 193-bit starting form, the 84-to-55-bit positive control, and
tests that independently replay generated rewrites. The saved interpreter is
also checked on arbitrary short raw sources and through two full levels of
self-interpretation.

This result gives a reproducible, broader search baseline. It does not justify
claiming that nearby equivalent terms have been exhausted. The next distinct
architectural experiment would change a binary encoding together with its
decoder while preserving the same external input/output contract.

## Limits

This is a bounded heuristic search, not an enumeration of all beta-equivalent
terms. The beam discards candidates, the expansion rules omit most possible
beta expansions, and occurrence extraction is restricted as described above.
Reordering applied binders explores some changes in recursive helper structure;
it does not enumerate alternative recursion constructions.

A failed search establishes no lower bound. Even an exhaustive search within
this rewrite family would not show that 174 bits is minimal. Alternative source
encodings, evaluator designs, and representations remain separate experiments.
