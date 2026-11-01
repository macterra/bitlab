# NAND tape: a baseline with total binary syntax

The objective is a minimal universal language in which **every finite bitstring
is a valid program**, including the empty string. This prototype satisfies that
objective except for the unproven superlative: it is a baseline to simplify, not
a claim to be the smallest language, nor a claim of novelty.

NAND is the only operation that computes a new tape bit. Movement and branching
are additional primitives. Counting only NAND would conceal part of the machine.

## Complete specification

A program is a finite sequence of bits, decoded into a finite instruction list.
The machine has an integer program counter `pc`, an integer tape head `h`, and a
two-way infinite bit tape `T`. Initially `pc = h = 0`; all tape cells are zero
unless an input configuration is supplied. Program storage is immutable and
separate from the tape. There is no fixed memory bound in the mathematical model.

Branch addresses use unary encoding: `0` means 0, `10` means 1, `110` means 2,
and so on.

| Prefix | Operands | Meaning |
| --- | --- | --- |
| `0` | One bit `b` | `T[h] = NAND(T[h], T[h+b])`; increment `pc` |
| `10` | One bit `d` | Move one cell left if `d=0`, right if `d=1`; increment `pc` |
| `11` | Natural numbers `z`, `o` | Set `pc` to `z` if `T[h]=0`, otherwise `o` |

Both NAND inputs are read before the destination is overwritten. Branch targets
are zero-based **instruction indices**, not bit positions. Any program counter
outside the instruction list halts. Every integer tape address is valid; an
unwritten cell reads as zero. The final tape is the result; printing and file I/O
are host conveniences rather than language primitives.

NAND can read only the current cell and either itself (`b=0`, giving NOT) or its
right neighbor (`b=1`). There are no general NAND source-address operands.

### No malformed binary programs

Decode an instruction only while at least one physical source bit remains.
Once an instruction has begun, any bits needed beyond the end of the source are
zero. These virtual zeros complete its prefix and operands; they do not start
additional instructions. A final unterminated unary run therefore still gives
its count, and any entirely missing operand is zero.

Examples:

| Entire source | Decoding / behavior on a blank tape |
| --- | --- |
| Empty | No instructions; halt |
| `0` | NAND selector 0; flip the current cell to 1; halt |
| `1` | Move one cell left; halt |
| `11` | Branch to instruction 0 for either bit; loop forever |
| `1111` | Branch to instruction 2 on zero, 0 on one; halt on a blank tape |
| `0000` | Two NANDs with selector 0; flip twice; halt with cell 0 |

Every decode iteration consumes a physical bit, and every unary operand scan
stops at a zero or at EOF. Thus decoding any finite bitstring terminates. Every
decoded instruction has a defined transition for every tape/head state, unless
the machine has already halted. This proves total syntax and defined execution;
it does **not** promise termination of execution.

The command-line wrapper accepts whitespace for convenience and rejects other
nonbinary characters. Those characters are outside the language's domain.

## Constructive universality argument

`compile_tm` translates any deterministic binary-tape Turing machine with a
finite state set. A source transition reads one bit, writes a bit, moves left,
right, or stays, and selects another state or halts. A missing transition halts
without writing or moving.

Represent source cell `i` by target cell `2*i`. Keep every odd target cell zero.
At the beginning of a simulated transition the target head is `2*i`, and its
program counter is at the dispatch instruction for the source state.

1. A branch on the current cell selects the source transition for 0 or 1.
2. `NAND(1)` writes 1, since `NAND(x,0)=1` and the adjacent odd cell is zero.
3. If the transition writes 0, `NAND(0)` flips that 1 to 0.
4. For a left/right source movement, make two unit moves in that direction;
   for a stay, make no moves. This preserves alignment to even cells.
5. Branch with identical targets to the next state's dispatch, or past the end
   of the program to halt.

No generated write touches an odd cell, so the zero-cell invariant is preserved.
The source state, head, and all tape bits therefore match after each block, by
induction. Each source transition takes three to six target instructions.
Missing transitions take one dispatch instruction to halt. Nontermination is
preserved as well as halting behavior. `compile_tm` returns an actual bitstring;
the interpreter has no special Turing-machine execution path.

Binary tape machines can simulate a finite alphabet by using fixed-width binary
blocks with an all-zero code for blank and finite control for reading/writing
each block. Input boundaries and lengths must be encoded when needed; a tape
whose blank is zero does not distinguish absent input from trailing input zeros.
This provides the bridge from ordinary Turing machines to the compiler's model.

For background on NAND plus unbounded memory and control, see Boaz Barak's
[Loops and infinity](https://introtcs.org/public/lec_06_loops.html). That source
establishes the surrounding computational model; the encoding, EOF rules, and
compiler above describe this prototype, not Barak's NAND-TM syntax.

## Run and inspect

Python 3, standard library only:

```sh
python3 nand_tape.py 0 --decode
python3 nand_tape.py 11 --steps 20
python3 nand_tape.py ''
python3 -m unittest -v test_nand_tape
```

The CLI reports JSON containing status, executed steps, head, program counter,
and the positions of all tape cells holding 1. All other cells hold 0.
`--input 101` initializes physical tape cells 0 and 2 to 1. `--steps` is a host
execution budget: `suspended` means the computation can resume, not that the
language halted or that the program was proved divergent. Actual Python runs
are subject to available memory and time.

A unary increment example, compiled from a Turing machine:

```python
from nand_tape import Machine, compile_tm, decode

bits = compile_tm({
    ("scan", 1): (1, 1, "scan"),  # Scan right across the existing ones.
    ("scan", 0): (1, 0, None),    # Append one and halt.
}, start="scan")
machine = Machine(decode(bits), ones={0, 2, 4})  # Three source ones.
assert machine.run(100) == "halted"
assert machine.ones == {0, 2, 4, 6}             # Four source ones.
```

The test suite checks every bitstring through length 12, EOF cases, NAND's truth
table and aliasing, memory growth and resumption, unary increment, and the
compiler against an independent simulator on 300 deterministic random machines.
Finite tests support the implementation; the argument above supplies universality.

## What remains to minimize

This baseline uses three instruction forms, a prefix decoder, local NAND access,
unit tape movement, unary branch operands, absolute instruction addressing, and separate program
storage. Unary encoding is simple but makes distant branches expensive. Changing
the encoding to use fewer bits need not make the execution model simpler.

The compiler already let us remove arbitrary NAND source addresses and arbitrary
movement distances: one-bit selectors suffice. Next, investigate whether
movement or branching can arise from the same update rule. Combining their
fields into a single large instruction would reduce the
opcode count without necessarily reducing the machine's complexity.

No global minimality theorem is claimed. Comparing candidates requires a chosen
cost measure: semantic rules, interpreter size in a fixed notation, or encoded
program lengths. Existing scripts in this repository are separate historical
experiments and are not dependencies of this implementation.

The next milestone is now implemented: [a NAND-tape self-interpreter](SELF_INTERPRETER.md)
with a measured bit length, explicit input framing, differential tests, and a
breakdown of where its encoded size is spent.
