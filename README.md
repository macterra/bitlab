# Nought and Knot

**Binary languages whose empty programs interpret their own languages.**

Every finite bitstring is a valid program in both languages. Nought constructs
combinators by folding bits from right to left. Knot uses compact BCL trees,
completes missing pieces with K, and ignores bits after the first expression.
Both give empty source the meaning of their own decoder.

This repository contains their implementations, runnable examples, and the
experiments that led to them. It uses Python's standard library; run the commands
below from the repository root.

## Run an example

Compute a complete Rule 30 history inside one Knot invocation:

```sh
python3 -m examples.knot_rule30
python3 -m examples.knot_rule30 --input 0001000 --generations 3
```

Python encodes the input and formats the output. The 2,042-bit Knot program
performs the generation loop itself. See the [example documentation](docs/examples/knot_rule30.md)
and the [physical-simulation discussion](docs/knot_simulation.md).

Run the saved single-generation Knot program directly:

```sh
python3 -m languages.knot --run-file artifacts/knot/rule30.bits --input 00100
```

Run Nought's identity function, or its Rule 30 example with a host iteration loop:

```sh
python3 -m languages.nought --run 00111001110001111111 --input 101
python3 -m examples.nought_rule30
```

Run the complete test suite:

```sh
python3 -m unittest discover -s tests -v
```

## Current languages

| Measurement | Nought | Knot |
| --- | ---: | ---: |
| Native self-interpreter | 0 bits | 0 bits |
| Decoder kernel, encoded in BLC | 155 bits | 261 bits |
| Single-generation Rule 30 guest | 1,979 bits | 809 bits |
| Source interpretation | Whole-source reverse fold | First BCL expression, completed at EOF |

A zero-bit self-interpreter does not eliminate the cost of the language
implementation. Decoder size, guest size, framing, and execution cost are
separate measurements. None of these implementations is claimed globally
minimal or a new smallest-interpreter record against Tromp.

- [Knot: semantics, proofs, and measurements](docs/knot.md)
- [Nought: semantics, proofs, and measurements](docs/nought.md)
- [Research goals and comparison of candidates](docs/research.md)

## Repository layout

| Directory | Contents |
| --- | --- |
| `core/` | Lambda evaluator, SK compiler, search, proof checking, reflection, and path helpers |
| `languages/` | Knot, Nought, bitfold, triage, and the NAND tape dialects |
| `examples/` | Shared Rule 30 function, language-specific runners, and hello-world material |
| `experiments/` | Candidate construction, searches, self-hosting experiments, and original prototypes |
| `tests/` | Semantic, compiler, self-interpretation, and artifact checks |
| `artifacts/` | Compiled programs, kernels, measurement reports, and replayable proofs |
| `docs/` | Language specifications, example guides, and research notes |

Use module commands such as `python3 -m languages.knot` and
`python3 -m experiments.direction_search`. Artifact paths are explicit;
programs do not assume their data lives next to their Python modules.
[Repository conventions and migration details](docs/repository.md) explain
source provenance and the former entry-point names.

## Earlier experiments

The earlier implementations and artifacts remain available for reproduction:

- [Functional/BLC-derived decoder](docs/experiments/functional.md): 174-bit native self-interpreter.
- [Empty-program reflection](docs/research.md#the-zero-bit-boundary): zero-bit interpreter with a 215-bit decoder.
- [Bitfold/Jot family](docs/experiments/bitfold.md) and [scan-direction comparison](docs/nought.md#matched-comparison-with-left-to-right-jot).
- [Equivalence rewriting](docs/experiments/rewrite_search.md) and [encoding search](docs/experiments/encoding_search.md).
- [Triage calculus](docs/experiments/triage.md): structural and raw-bit self-interpreters on another runtime.
- [NAND tape](docs/experiments/nand_tape.md), [self-hosting](docs/experiments/self_interpreter.md), and [compact addresses](docs/experiments/compact_tape.md).
- [Original expression-language prototype](docs/experiments/original_expression.md).

These models have different execution and input/output contracts. Their
measurements are an inventory of experiments, not a controlled ranking.
