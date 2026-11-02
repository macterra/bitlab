# Rule 30 in Nought

[`rule30.bits`](rule30.bits) is a **1,979-bit native Nought program** that maps
an input row to its next Rule 30 generation. [`rule30.py`](rule30.py) constructs
the function, compiles it, and runs it through Nought's decoder and the reference
lambda machine.

Run the five-generation example:

```sh
python3 rule30.py
```

```text
0000001000000
0000011100000
0000110010000
0001101111000
0011001000100
0110111101110
```

Use another initial row or regenerate the native artifact:

```sh
python3 rule30.py --input 0001000 --generations 3
python3 rule30.py --emit rule30.bits --generations 0
python3 -m unittest -v test_rule30
```

## Execution contract

The local rule is `left XOR (center OR right)`, or the truth table
`111,110,101,100,011,010,001,000 -> 0,0,0,1,1,1,1,0`.
See [Wolfram's Boolean formula](https://www.wolframscience.com/nks/notes-2-1--cellular-automaton-rules-as-formulas/).

Rows use Nought's existing boolean-pair list encoding. The function walks the
original row while carrying the previous cell, peeks at the following cell,
and constructs a new output list. All cells update from the same old generation.
XOR, OR, traversal, list construction, and recursion are compiled into the native
program; there is no host cellular-automaton primitive.

The width stays fixed. Cells outside either end are zero, and an empty row stays
empty. This is a finite zero-boundary simulation, not an infinite expanding row
or a ring. Supply enough initial zero padding for the desired observation window.

Each generation executes `R(bitlist(program))(bitlist(row))` and observes its
result as a bit list. Python handles repeated invocations and printing. The
default budget is 20 million reference-machine steps per generation; the example
above takes about 6.17 million per generation. `--steps` changes the budget.
Incomplete execution exits with an error instead of treating partial output as
a new row. The observer limit follows the row width, rather than imposing the
reference helper's default 100-bit output limit.

The 1,979-bit measurement is the guest program only. It excludes the separate
155-bit Nought decoder, input row, and host display loop, and is not a minimality
claim. Tests check all eight local neighborhoods, every row through width five
at the lambda-function level, native boundary cases, the five native generations
above, and exact reproduction of the saved program.
