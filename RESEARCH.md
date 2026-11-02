# Nought: open research direction

The goal is a minimal universal binary programming language in which every
finite bitstring has defined execution. Self-interpreter length is a central
measurement, but cannot identify the simplest language by itself.

NAND, lambda calculus, code/data framing, evaluation strategy, and compatibility
with earlier candidates are design choices. New architectures may change them.
Each result must state its interface, establish universality, demonstrate native
self-interpretation, and account for the machinery that gives its bits meaning.

## The zero-bit boundary

Let `D` be the existing 174-bit raw-list decoder. Define a new closed decoder `Q`
with the equations:

```text
Q []     = Q
Q (b:bs) = D (b:bs)
```

This is ordinary lambda recursion, not a new host evaluation opcode. The exact
implementation in [`empty_interpreter.py`](empty_interpreter.py) expands `D`
and the recursive wrapper into a **215-bit BLC kernel**. The list representation
and separate program/input arguments are unchanged.

Every finite source still denotes a closed computation. Every complete closed
BLC encoding is nonempty, so the existing lambda-calculus embedding is preserved.
Consequently the new language is universal. But its empty program denotes `Q`,
and therefore interprets arbitrary source lists, including its own empty source:

```text
meaning_Q("") = Q
meaning_Q("") (bitlist(p)) (bitlist(x)) = run_Q(p, x)
```

The self-interpreter is **zero bits**, the absolute minimum for finite strings.
Tests complete eight nested empty-program interpretation levels and a nontrivial
bit-list computation. The empty artifact is intentionally a zero-byte file.

This resolves the literal single-number minimization but does not make the
underlying language simpler: the kernel grew by 41 bits. The construction is a
benchmark diagnostic, not a claim of a new minimal universal machine. Equivalent
reserved-program tricks can make such a score arbitrarily misleading unless the
language definition is measured too.

```sh
python3 empty_interpreter.py --report empty_metrics.json --kernel empty_kernel.blc --emit empty_self.bits
python3 -m unittest -v test_empty_interpreter
```

## Track a frontier, not one number

For comparable lambda-backed candidates, record at least:

| Candidate | Native self-interpreter | Closed raw-list decoder in BLC |
| --- | ---: | ---: |
| Original functional candidate | 174 bits | 174 bits |
| Empty-program boundary case | **0 bits** | 215 bits |
| Nought (reflective SK bitfold) | **0 bits** | **155 bits** |
| Ordinary SK bitfold | 1,169 bits | **114 bits** |
| Ordinary KSK bitfold | 1,035 bits | 123 bits |

The original two points traded off the coordinates. The subsequent
[Nought construction](REFLECTIVE_FOLD.md) improves both coordinates
over the original 174/174 point. The ordinary folds have smaller kernels but
longer native self-interpreters, preserving a nontrivial frontier. A different runtime needs its own
explicit rules and a measured implementation; Python source bytes are useful
provenance, but not a representation-independent lower bound. Input encoders,
native primitives, omitted parser work, and observation conventions must also
be visible. A changed interface is permitted and labeled, not automatically
disqualified.

## Broader architectural leads

- **Continuation streams:** Stay describes Zot's total binary syntax and a
  six-bit self-interpreting prefix for Keraia. Their interfaces differ from a
  function consuming a raw boolean list. Reproduce the operational behavior and
  measure the representation/adapter cost before comparing scores.
  [Stay, *Very Simple Chaitin Machines for Concrete AIT*](https://arxiv.org/html/cs/0508056)
- **Encoded syntax:** Hart reports a 115-bit lambda evaluator that consumes
  higher-order encoded syntax. Its input has already exposed application and
  binding, so its size is not a raw-bit decoder measurement. It is a useful
  different point in the design space.
  [Hart, *Extremely Simple Self Interpretation*](https://anthonylorenhart.com/2021-09-04-Extremely-Simple-Self-Interpretation/)
- **Structural reflection:** Tree/triage calculus provides native access to tree
  structure without variable indices. Implement and measure this route, including
  both structural-input and raw-bit interfaces.
  [Bader's triage specification](https://treecalcul.us/specification/)

These are prior-art leads, not results established by this repository. The
research should pursue substantive changes in representation and execution,
alongside proof and measurement, rather than exhaust only nearby BLC rewrites.

The [triage-calculus experiment](TRIAGE.md) now implements the structural-reflection
lead. It has native self-interpreters of 329 bits for quoted trees and 987 bits
for raw binary input, with an independent runtime check and constructive SK
embedding. These use a different runtime, so they are separate frontier entries,
not smaller raw-list lambda kernels.

Significant completed milestones are committed and pushed as authorized by the
user. Unrelated exploratory files already in the workspace are preserved.
