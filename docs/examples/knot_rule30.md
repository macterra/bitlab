# Rule 30 iteration inside Knot

[`artifacts/knot/rule30_history.bits`](../../artifacts/knot/rule30_history.bits) is a **2,042-bit Knot program** that
computes a complete fixed-width Rule 30 history in one invocation. Count parsing,
the local rule, row traversal, generation iteration, and output concatenation
are all compiled into the native program.

Run the default example:

```sh
python3 -m examples.knot_rule30
```

```text
0000001000000
0000011100000
0000110010000
0001101111000
0011001000100
0110111101110
```

Choose a row and the number of updates:

```sh
python3 -m examples.knot_rule30 --input 0001000 --generations 3
```

Python constructs the input bit list, invokes Knot once, and displays the output
in lines of the original row width. It does not calculate generations or feed
one row back into the decoder. The single-generation guest remains available
as [`artifacts/knot/rule30.bits`](../../artifacts/knot/rule30.bits), at 809 bits; these programs
perform different jobs.

## Bitstring interface

The program consumes one bitstring:

```text
1^n 0 row
```

There are `n` leading ones, a zero delimiter, then the initial row. `n` counts
updates after the initial row, so the output contains `n+1` rows. For example,
five updates of `0000001000000` use input `1111100000001000000`.

The output is the concatenation of the initial row and all successor rows,
without delimiters. The caller knows the row width and can split the result for
display. Width stays fixed and cells outside both ends are zero, as in the
[single-generation implementation](nought_rule30.md).

- Zero updates return the initial row.
- An empty row returns an empty bitstring for any finite count; the display
  wrapper prints the requested number of empty lines.
- A raw input without a zero count delimiter returns an empty bitstring.

The program size excludes the separately supplied count and row, the 261-bit
Knot decoder, and display code. The source lambda function occupies 470 BLC
bits before SK compilation. These are measured implementations, not minimality
claims.

## Guest algorithm

The compiled program first collects the unary count and then evaluates:

```text
history(count, row):
    if count is empty:
        return row
    return append(row, history(rest(count), rule30(row)))
```

`append`, `history`, the count parser, and `rule30` are ordinary lambda functions
compiled into K/S/application. No native iteration primitive or host callback is
introduced. Every output cell in a new row depends on the same old row.

The reference evaluator uses call-by-name, so later generations can recompute
earlier values. `--steps` bounds the entire invocation, not each generation;
the default is 100 million reference-machine steps. If evaluation exceeds the
budget, the wrapper reports incomplete execution rather than presenting a
partial history as a complete result. The observation limit is based on the
expected output length and permits histories longer than 100 bits.

## Artifacts and checks

Regenerate the native program and its measurement report:

```sh
python3 -m examples.knot_rule30 --emit artifacts/knot/rule30_history.bits --report artifacts/knot/rule30_history_metrics.json
python3 -m unittest -v tests.test_knot_rule30 tests.test_total_bcl
```

The generic Knot CLI can also run the saved program directly:

```sh
python3 -m languages.knot --run-file artifacts/knot/rule30_history.bits --input 1111100000001000000 --output-limit 79 --steps 100000000
```

Its output field contains all 78 bits, the concatenation of the six displayed
13-bit rows. This execution uses only Knot's existing raw program/input
interface; the dedicated display wrapper is unnecessary for computation.

Tests check all initial rows through width three and update counts zero through
three against an independent Rule 30 truth-table calculation. Native tests cover
the five-generation example in one invocation, empty rows, zero updates,
boundary cases, missing count delimiters, outputs exceeding 100 bits, incomplete
execution, and exact artifact reproduction. Sizes, input/output contracts, and
hashes are recorded in [`artifacts/knot/rule30_history_metrics.json`](../../artifacts/knot/rule30_history_metrics.json).
