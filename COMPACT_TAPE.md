# Compact branch addresses: a measured language variant

The compact variant's self-interpreter is **25,260 bits**, compared with
**741,267 bits** for the original unary-address language: **96.6% smaller**, or
about **29.3 times smaller**. This is an implemented, tested comparison, not a
claim of global minimality.

Both languages still accept every finite bitstring. NAND, movement, branching,
tape initialization, and halting have the same execution semantics. Only the
binary encoding of branch operands changes. Use `compact_tape.py` for this
dialect; old `.nand` programs are not generally binary-compatible.

## Address encoding

Each operand is a sequence of pairs `1b`, followed by a terminating `0`. The
payload bits `b` give a nonnegative integer in most-significant-first order.
An empty sequence denotes zero. The canonical encoder omits leading zeros.

| Address | Unary encoding | Compact encoding |
| ---: | --- | --- |
| 0 | `0` | `0` |
| 1 | `10` | `110` |
| 2 | `110` | `11100` |
| 3 | `1110` | `11110` |
| 4 | `11110` | `1110100` |

For positive address `n`, the compact encoding takes `2*bit_length(n)+1` bits,
instead of `n+1`. The two-bit branch prefix `11` is unchanged. For example,
branching to instruction 1 on either input bit is `11110110` in this dialect,
versus `111010` in the original.

All noncanonical encodings with leading zero digits are valid too. EOF supplies
virtual zeros just as before, including a missing payload bit. Thus `111`
decodes to branch `(0,0)`, while `11111` decodes to branch `(2,0)`: its first
operand has payload digits `1` and an implicit `0`. A scan always reaches a
physical zero terminator or EOF, so finite binary sources always decode.

Because both codecs can represent every instruction list, universality carries
over from the original language's Turing-machine construction. Re-encoding an
instruction list preserves all its program-counter targets and execution steps.
This does not require preserving the meaning of the same raw bitstring across
the two dialects.

## A real self-interpreter of the new dialect

[`compact_self_host.nand`](compact_self_host.nand) is encoded in the compact
dialect and decodes that same dialect's raw guest source. Its generator reuses
the baseline's tape operations but changes guest operand decoding, instruction
skipping, and branch-counter representation.

Merely encoding the old interpreter's instructions with the new codec would
produce a 19,714-bit **cross-interpreter**: a compact-language program that still
interprets unary-language guests. That smaller number is deliberately not the
self-interpreter score. The actual self-interpreter includes the new decoder
and costs an additional 5,546 bits.

The input/output contract is the same as in [SELF_INTERPRETER.md](SELF_INTERPRETER.md),
with rows expanded from 18 to **20 cells**. Lane 16 now contains the binary
counter's digits, in source order, and new lane 18 marks its end. Every even
lane still has a permanently zero right neighbor. Input contains only raw source
bits, presence bits, and guest tape data; the program initializes its own metadata.

While reading the selected branch operand, the interpreter appends each payload
digit to its counter. To find the destination instruction it scans for a nonzero
digit, decrements from the least-significant end with borrowing, and skips one
guest instruction. If it reaches EOF first, it halts without counting down to
zero. At a nonhalting guest instruction boundary the counter is empty again,
with its end marker restored to row zero.

This uses space proportional to the operand's encoded length, rather than its
numeric value. An enormous out-of-range address therefore does not create an
enormous unary counter. Execution still involves repeated scans from the origin
and is not optimized for speed. The two-sided guest tape and NAND-neighbor
handling are unchanged.

The original simulation invariants continue to hold, with the binary counter
invariant replacing the unary one. Counter decrement borrows left only after a
nonzero digit has been found, so it never runs past the origin. Source scans
terminate at a delimiter or EOF. Seeking a destination either decreases a finite
counter to zero or encounters the end of a finite program. Thus each simulated
guest instruction still completes in finitely many host steps.

## Size comparison

| Measurement | Original | Compact |
| --- | ---: | ---: |
| Self-interpreter bits | 741,267 | **25,260** |
| Instructions | 3,273 | 4,294 |
| NAND bits | 200 | 252 |
| Movement bits | 8,742 | 11,568 |
| Branch bits | 732,325 | 13,440 |
| Packed bytes, with exact bit length separately retained | 92,659 | 3,158 |
| Complete reference Python source bytes | 6,113 | 9,354 |
| Input-frame row width | 18 | 20 |

The compact interpreter has **31.2% more instructions**, yet a much shorter
encoding. This separates the effect on program length from the effect on the
number of execution steps or semantic rules. It does not establish a runtime
speedup. Branches now account for about 53.2% of bits and movement about 45.8%,
so addressing is no longer overwhelmingly dominant.

The compact reference-source measurement includes the complete files
`nand_tape.py` and `compact_tape.py`, because the latter imports the former's
execution engine. It includes CLIs, comments, utilities, and the original
compiler, and is not minimized. Its SHA-256 is over their bytes concatenated in
that order. Generated interpreter size excludes development tools and
input-dependent framing, and includes all executable helpers and initialization.
The frame-width increase is shown separately rather than hidden in that score.

The original emitted artifact and measurement report remain byte-for-byte
unchanged. The compact artifact has its own
[`compact_self_host_metrics.json`](compact_self_host_metrics.json) report.

## Reproduce and test

```sh
python3 compact_self_host.py --emit compact_self_host.nand --report compact_self_host_metrics.json
python3 compact_self_host.py --run 0
python3 compact_self_host.py --run 01 --ones 0 1
python3 compact_tape.py 11110110
python3 -m unittest -v test_nand_tape test_self_host test_compact_tape
```

The shared differential suite runs against both self-interpreters, including all
511 sources through eight bits on two initial tapes, randomized traces, truncated
operands, loops, and NAND operations across zero. Compact-specific tests cover
leading-zero encodings, a jump to `2**64`, and all 8,191 sources through twelve
bits for native codec round trips and execution. Reader offsets are checked
against physical source spans, not canonical re-encodings that could discard
leading zero digits.

Both dialects also have a bounded self-application smoke test: the complete
interpreter source is supplied as a guest, and its first 12 instructions are
compared with direct execution. This remains a prefix test, not a claim that a
full nested interpretation has been completed.

This experiment supports compact addresses under the proposed self-interpreter
size criterion. The baseline remains available for comparison; changing the
default language is a separate decision. Shared routines and more economical
tape navigation are now substantial remaining opportunities.
