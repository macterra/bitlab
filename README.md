# nand

Exploring a minimal universal language where every finite bitstring is a valid
program. Our main benchmark is the length of a language's self-interpreter,
measured in bits, with explicit input framing and a companion measurement of
the reference implementation.

The best result so far is the [compact-address dialect](COMPACT_TAPE.md): its
self-interpreter is **25,260 bits**, 96.6% smaller than the original unary-address
baseline. It interprets raw source using only NAND, movement, and branching.
Every finite bitstring is valid in both dialects. Neither is claimed to be
globally minimal.

```sh
python3 compact_tape.py 0
python3 compact_self_host.py --run 0
python3 -m unittest -v test_nand_tape test_self_host test_compact_tape
```

| Dialect | Self-interpreter | Documentation |
| --- | ---: | --- |
| Compact binary addresses | **25,260 bits** | [Specification and comparison](COMPACT_TAPE.md) |
| Original unary addresses | 741,267 bits | [Language](NAND_TAPE.md), [self-interpreter](SELF_INTERPRETER.md) |

These are separate, generally binary-incompatible dialects with dedicated
runners. `nand_tape.py` retains the original unary format; `compact_tape.py`
implements the compact format. The compact interpreter has more instructions
but much shorter encoded addresses; a smaller bit count does not imply faster
execution.

Regenerate the compact artifact and its measurement report:

```sh
python3 compact_self_host.py --emit compact_self_host.nand --report compact_self_host_metrics.json
```

All 26 tests pass, including differential execution, exhaustive short sources,
large branch addresses, and reproducible artifacts. Self-application tests check
bounded execution prefixes, not completed nested interpretations. The current
size breakdown points to shared routines and tape navigation as further
optimization opportunities.

## Original expression-language experiment

The notation below belongs to the earlier `nand.py` interpreter. It is separate
from the NAND tape prototype.

```
00 = 0
01 = 1
1xy = (nand x y) = (not (and x y))
```

```
101x = (nand 1 x) = (not (and 1 x)) = (not x)
100x = (nand 0 x) = (not (and 0 x)) = (not 0) = 1

10000 = (not (and 0 0)) = (not 0) = 1
10001 = (not (and 0 1)) = (not 0) = 1
10100 = (not (and 1 0)) = (not 0) = 1
10101 = (not (and 1 1)) = (not 1) = 0

101100x = (not (nand 0 x) = (not 1) = 0
101101x = (not (nand 1 x) = (not (not x) = x

1011xy = (not (nand x y) = (and x y)
1101x101y = (nand (not x) (not y)) = (or x y)

1x101y = (nand x (not y)) = (not (and x (not y))) = (or (not x) y) = x -> y
1101xy = (nand (not x) y) = (not (and (not x) y)) = (or x (not y)) = x <- y

1011100xy = (not 1100xy) = (not (nand 100x y)) = (and 1 y) = y
```
