"""Compile and run a fixed-width Rule 30 cellular automaton in Nought.

Each native invocation consumes a row and returns its next generation.
Cells outside the row are zero. Python only drives successive invocations.
"""

import argparse
from functools import lru_cache
from pathlib import Path

from bitfold import compile_sk, native_encode
from functional import CONS, FALSE, NIL, TRUE, app, bitlist, named, read_bits
from reflective_fold import build


def local_rule():
    # Encoded zero selects the first argument; encoded one selects the second.
    xor = named(r"\a b. a b (b one zero)", {"zero": TRUE, "one": FALSE})
    return named(r"\left center right. xor left (center right one)",
                 {"xor": xor, "one": FALSE})


def step_function():
    return named(r"""((\s. s s) (\s left xs.
        xs (\center tail ignored.
            cons (rule left center (tail (\head rest ignored. head) zero))
                 (s s center tail)) nil)) zero""",
                 {"cons": CONS, "rule": local_rule(), "zero": TRUE, "nil": NIL})


@lru_cache(maxsize=1)
def compile_program():
    _, _, report = build()
    words = report["certificate"]["words"]
    return native_encode(compile_sk(step_function(), words), words, reverse=True)


def step(row, budget=20000000):
    if any(bit not in "01" for bit in row):
        raise ValueError("row must contain only binary digits")
    if budget < 1:
        raise ValueError("step budget must be positive")
    _, kernel, _ = build()
    result = read_bits(app(kernel, bitlist(compile_program()), bitlist(row)),
                       budget=budget, limit=len(row) + 1)
    if result["status"] != "end" or len(result["output"]) != len(row):
        raise RuntimeError(f"generation did not complete: {result}")
    return result["output"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="0000001000000", help="initial row, including any zero padding")
    parser.add_argument("--generations", type=int, default=5)
    parser.add_argument("--steps", type=int, default=20000000, help="reference-machine budget per generation")
    parser.add_argument("--emit", type=Path, help="write the compiled native Nought program")
    args = parser.parse_args()
    if any(bit not in "01" for bit in args.input) or args.generations < 0 or args.steps < 1:
        parser.error("expected binary input, nonnegative generations, and a positive step budget")
    if args.emit:
        args.emit.write_text(compile_program(), encoding="ascii")
    row = args.input
    print(row, flush=True)
    for _ in range(args.generations):
        try:
            row = step(row, budget=args.steps)
        except RuntimeError as error:
            parser.exit(1, f"{error}\n")
        print(row, flush=True)


if __name__ == "__main__":
    main()
