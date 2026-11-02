# Repository conventions

Run commands from the repository root using Python's module syntax. No package
installation or third-party Python dependency is required.

```sh
python3 -m examples.knot_rule30
python3 -m languages.knot --run-file artifacts/knot/rule30.bits --input 00100
python3 -m unittest discover -s tests -v
```

## Code and dependencies

`core/` contains the lambda evaluator, SK compiler, contraction and equivalence
searches, proof replay, the empty-source reflection wrapper, and path helpers.
These modules do not depend on language implementations or examples.

`languages/` contains the language definitions and their command-line runners.
Knot and Nought use shared core machinery. Nought additionally uses the bitfold
definitions. Neither language imports the Rule 30 examples or experiment modules.

`examples/rule30.py` defines the shared local rule and single-generation lambda
function. The Nought runner repeats that function in Python; the Knot history
runner compiles iteration into the guest. The single-generation Knot example
has its own compiler and measurement entry point:

```sh
python3 -m examples.knot_rule30_step --emit artifacts/knot/rule30.bits --report artifacts/knot/rule30_metrics.json
```

Language reports measure language implementations. Example reports measure
examples. The Knot language report no longer contains Rule 30 source or sizes.

`experiments/` holds searches, earlier functional candidates, and tape
self-hosting experiments. The original NAND expression and network prototypes
are under `experiments/legacy/`. Tests live in `tests/`, including the original
semantic and artifact reproduction checks.

## Programs and provenance

`artifacts/` groups saved native programs, BLC kernels, measurement reports, and
proofs by language or experiment. Empty self-interpreter files are intentional
zero-byte programs. They remain tracked along with the nonempty artifacts.

`core.artifacts` resolves paths from the repository location rather than from
the calling module's directory. Report source manifests use sorted,
repository-relative paths and include local static imports and their package
initializers. Source bytes and hashes describe the implementation and utilities;
they are not substitutes for measured native-program or BLC-kernel sizes.

The layout migration preserved all 18 existing program and kernel artifacts
byte for byte, and retained saved search results and proof trails. Source
manifests and their byte counts and hashes were refreshed for the reorganized
implementation. Earlier source snapshots and their original reports remain
available in Git history.

Existing untracked exploratory scripts were left in place. Python cache files
are ignored by Git.

## Former entry points

| Former root command | Module command |
| --- | --- |
| `python3 total_bcl.py` | `python3 -m languages.knot` |
| `python3 reflective_fold.py` | `python3 -m languages.nought` |
| `python3 rule30.py` | `python3 -m examples.nought_rule30` |
| `python3 knot_rule30.py` | `python3 -m examples.knot_rule30` |
| `python3 bitfold.py` | `python3 -m languages.bitfold` |
| `python3 triage.py` | `python3 -m languages.triage` |
| `python3 nand_tape.py` | `python3 -m languages.nand_tape` |
| `python3 compact_tape.py` | `python3 -m languages.compact_tape` |
| `python3 functional_candidates.py` | `python3 -m experiments.functional_candidates` |
| `python3 functional_rewrites.py` | `python3 -m experiments.rewrite_search` |
| `python3 encoding_search.py` | `python3 -m experiments.encoding_search` |
| `python3 direction_search.py` | `python3 -m experiments.direction_search` |
| `python3 empty_interpreter.py` | `python3 -m experiments.empty_interpreter` |
| `python3 self_host.py` | `python3 -m experiments.self_host` |
| `python3 compact_self_host.py` | `python3 -m experiments.compact_self_host` |

Use explicit paths under `artifacts/` for `--emit`, `--kernel`, `--report`, and
`--run-file`. The language and experiment guides contain complete commands.
