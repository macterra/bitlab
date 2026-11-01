# NAND tape interpreting NAND tape

[`self_host.nand`](self_host.nand) is an executable NAND-tape program that
interprets raw NAND-tape source bits. It uses only ordinary NAND, move, and branch
instructions. There is no `eval` primitive, host callback, guest-step hook, or
predecoded guest instruction table.

[`self_host.py`](self_host.py) is its assembler and development runner, not an
extra runtime instruction set. The assembler is independent of the guest program.
Python frames input, runs the existing NAND-tape machine, and reads the output;
the emitted NAND code performs all guest decoding and execution.

## Measured baseline

| Measurement | Value |
| --- | ---: |
| Self-interpreter program | **741,267 bits** |
| Decoded instructions | 3,273 |
| NAND instruction bits | 200 |
| Movement instruction bits | 8,742 |
| Branch instruction bits | 732,325 |
| Complete Python reference file | 6,113 bytes |

These are exact sizes of this implementation, not proven minima. The reference
measurement is the entire UTF-8 `nand_tape.py`, including its CLI, compiler,
comments, and formatting. It is a reproducible companion measurement, not a
minimal description of the semantics. The generator, tests, and input-dependent
data are excluded from the self-interpreter's program length. All runtime
initialization and helper routines are included in the emitted program.

The `.nand` file stores one ASCII character per bit, with no final newline.
Packed storage would take 92,659 bytes, with the exact bit length retained
separately. Byte padding must not become additional program bits.
[`self_host_metrics.json`](self_host_metrics.json) records exact sizes and SHA-256
digests for both the binary-source artifact and the reference implementation.

The first implementation was 847,931 bits. Removing a duplicated operand-discard
path reduced that to 822,224. Replacing unreachable arms of unconditional jumps
with address zero reduced it to 741,267, without changing the language. These
last rewrites use locally established bit values, such as the origin marker
being one after returning home. `build(optimize=False)` disables that rewrite.

## The input/output contract

The intended equation is:

```text
extract(run(self_host.nand, frame(p, x))) = run(p, x)
```

Equality means the same guest tape contents and head position on halting, and
preservation of nontermination. The guest starts with program counter and head
zero. `p` is any finite bitstring, including empty and truncated programs. `x` is
any finite set of integer guest tape positions initially holding one. All other
guest tape cells start at zero.

The host tape consists of nonnegative rows of 18 cells. Each even lane below is
followed by a permanently zero scratch cell. The odd cells are ordinary blank
tape, not special hardware constants.

| Lane | Meaning in row `i` |
| --- | --- |
| 0 | Origin marker: one only in row zero |
| 2 | Raw source bit `p[i]`, or zero past the end |
| 4 | Source presence: one exactly when `i < len(p)` |
| 6 | Source-reader marker |
| 8 | Guest-head marker for guest position `i` |
| 10 | Guest-head marker for guest position `-i-1` |
| 12 | Guest data at position `i` |
| 14 | Guest data at position `-i-1` |
| 16 | Temporary unary branch counter |

Only source, presence, and guest data are supplied in the input frame. The
interpreter initializes its own origin and pointer markers. Framing does not
parse, repair, or annotate instructions: `frame("0")` and `frame("00")` differ,
even though those two sources decode to the same guest instruction.

The presence lane distinguishes EOF from a real zero. It costs one presence bit
per source bit, alongside the raw bit, within a layout spanning 18 cells per
source bit. This representation overhead is explicit input framing, not an
additional executable program. Other languages must specify equally explicit
framing before their self-interpreter scores can be fairly compared. The
remaining lanes reserve room for working storage; zero cells need not be stored
by the sparse Python implementation.

Output extraction selects the two guest-data lanes and the single guest-head
marker. Source and working-storage lanes are ignored. The host program counter
and host head are implementation details, and the original guest program
counter is not an output value. In particular, a jump past the guest program
halts without needing to retain the numeric out-of-range guest counter.

The self-interpreter's domain is well-formed frames of arbitrary binary
programs. Arbitrary malformed frames need not simulate a guest, just as arbitrary
arguments to a function need not satisfy its input contract. They are still
defined computations under NAND tape's language semantics.

## How the emitted program works

The source-reader marker points to the next raw instruction. Fetching a bit
checks presence, reads source, and advances the marker. At EOF it returns zero
without advancing, exactly implementing the language's virtual-zero rule. A
separate presence check at instruction boundaries prevents virtual zeros from
creating new instructions.

NAND and movement update the framed guest data and head markers. Negative guest
positions are folded onto nonnegative host rows so every search can start at
the origin and scan right. NAND's right-neighbor case handles the crossing from
guest position -1 to position 0 explicitly.

For a branch, the interpreter reads the current guest bit, counts the selected
unary operand into its counter lane, resets the source reader, and skips that
many instructions. Skipping uses the actual raw instruction grammar, including
truncated operands. A target past the end halts. The other branch operand need
not be evaluated because resetting the source reader discards the old position.

At each guest instruction boundary:

1. Source and presence lanes still contain the original raw program.
2. Exactly one source-reader marker identifies the current instruction.
3. Exactly one guest-head marker and the data lanes represent the guest state.
4. The branch counter is zero and every odd scratch cell remains zero.
5. The host head is at the origin marker.

Each instruction preserves these invariants or halts with the correct output.
All internal searches terminate on a well-formed frame: markers are at finite
positions, operand scans encounter a delimiter or EOF, and branch skipping
decreases a finite counter. Consequently each nonhalting guest step takes
finitely many host steps. This supplies a simulation argument for divergence
preservation as well as the halting cases exercised by tests.

## Reproduce and run

```sh
python3 self_host.py --emit self_host.nand --report self_host_metrics.json
python3 self_host.py --run 0
python3 self_host.py --run 01 --ones 0 1
python3 self_host.py --run 11 --steps 10000
python3 -m unittest -v test_nand_tape test_self_host
```

The first guest flips cell zero to one. The second computes NAND(1,1) and clears
cell zero, retaining cell one. The third guest loops; a finite host budget
reports `suspended`, which is not itself evidence of divergence. For `11`, its
defined branch-to-zero behavior establishes divergence independently.

To execute the checked-in artifact directly:

```python
from pathlib import Path
from nand_tape import Machine, decode
from self_host import frame, result

interpreter = Path("self_host.nand").read_text()
host = Machine(decode(interpreter), frame("0"))
assert host.run(10000) == "halted"
assert result(host.ones) == ({0}, 0)
```

The differential tests check all 511 programs through eight bits on two initial
tapes, 150 deterministic random programs, branch targets, truncated operands,
NAND truth-table cases on both sides of zero, and growing computations. They
compare guest instruction boundaries, including the source reader's position,
against the existing Python interpreter. They also check preservation of raw
source and scratch cells, and exact regeneration of the artifact and size report.

A self-application smoke test feeds the complete interpreter bitstring to itself
and compares the first 12 guest instructions. It does **not** claim a completed
second-level interpretation: repeated tape scans and unary addresses make that
expensive. Universality and the simulation argument do not depend on finishing
that particular test, and finite tests do not prove general correctness.

## What the measurement suggests

Branches account for about **98.8% of the program bits**. The generated program
uses many unit movements, which increase instruction indices; unary absolute
addresses then make jumps to those indices expensive. So the measured size is
mostly addressing overhead, not NAND logic.

The next useful comparison is a language variant with a more compact branch
encoding. Its self-interpreter must implement the new decoder before counting
its size: simply re-encoding this artifact without changing its guest decoder
would not measure a self-interpreter of the new language. Relative addresses and
shared helper routines are other candidates. None of these measurements by
itself establishes a globally minimal language.

That comparison is now implemented in [the compact-address experiment](COMPACT_TAPE.md).
Its self-interpreter is 25,260 bits and decodes the new dialect itself; the unary
artifact and the baseline measurements above remain unchanged.
