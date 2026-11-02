"""Run multiple Rule 30 generations inside one Knot program.

Input is 1^n 0 row; output concatenates the initial row and n successor rows.
Python encodes the arguments and formats the result; iteration runs in Knot.
"""

import argparse
import hashlib
import json
from functools import lru_cache
from pathlib import Path

from functional import CONS, NIL, app, bitlist, encode, named, read_bits
from rule30 import step_function
from total_bcl import build, compile_program


def history_function():
    append = named(r"""(\s. s s) (\s xs ys.
        xs (\head tail ignored. cons head (s s tail ys)) ys)""", {"cons": CONS})
    history = named(r"""(\s. s s) (\s count row.
        append row (count (\head tail ignored. s s tail (step row)) nil))""",
                    {"append": append, "step": step_function(), "nil": NIL})
    return named(r"""((\s. s s) (\s count bits.
        bits (\bit tail ignored.
            bit (history count tail) (s s (cons bit count) tail))
            nil)) nil""", {"history": history, "cons": CONS, "nil": NIL})


@lru_cache(maxsize=1)
def program():
    return compile_program(history_function())


def encode_input(row, generations):
    if any(bit not in "01" for bit in row):
        raise ValueError("row must contain only binary digits")
    if not isinstance(generations, int) or generations < 0:
        raise ValueError("generation count must be a nonnegative integer")
    return "1" * generations + "0" + row


def metrics():
    source = program()
    files = ["functional.py", "functional_candidates.py", "functional_rewrites.py", "bitfold.py",
             "reflective_fold.py", "total_bcl.py", "rule30.py", "knot_rule30.py"]
    implementation = b"".join(Path(__file__).with_name(name).read_bytes() for name in files)
    return dict(language="Knot", program_bits=len(source),
                program_sha256=hashlib.sha256(source.encode()).hexdigest(),
                lambda_function_bits=len(encode(history_function())),
                kernel_bits=build()[2]["reflective_kernel_bits"],
                input_format="1^n 0 row; n updates; fixed width; zero boundaries",
                output_format="initial row followed by n successor rows, concatenated",
                source_files=files, source_bytes=len(implementation),
                source_sha256=hashlib.sha256(implementation).hexdigest())


def run(row, generations=5, budget=100000000):
    bits = encode_input(row, generations)
    if budget < 1:
        raise ValueError("step budget must be positive")
    expected_length = len(row) * (generations + 1)
    # One decoder application, one input list, and one observation for all rows.
    result = read_bits(app(build()[1], bitlist(program()), bitlist(bits)),
                       budget=budget, limit=expected_length + 1)
    if result["status"] != "end" or len(result["output"]) != expected_length:
        raise RuntimeError(f"history did not complete: {result}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="0000001000000", help="initial row")
    parser.add_argument("--generations", type=int, default=5, help="number of updates after the initial row")
    parser.add_argument("--steps", type=int, default=100000000, help="total reference-machine budget")
    parser.add_argument("--emit", type=Path, help="write the native Knot history program")
    parser.add_argument("--report", type=Path, help="write program sizes, contract, and hashes")
    args = parser.parse_args()
    try:
        encode_input(args.input, args.generations)
        if args.steps < 1:
            raise ValueError("step budget must be positive")
        if args.emit:
            args.emit.write_text(program(), encoding="ascii")
        if args.report:
            args.report.write_text(json.dumps(metrics(), indent=2) + "\n")
        result = run(args.input, args.generations, args.steps)
    except (ValueError, RuntimeError) as error:
        parser.exit(1, f"{error}\n")
    width = len(args.input)
    for index in range(args.generations + 1):
        print(result["output"][index * width:(index + 1) * width])


if __name__ == "__main__":
    main()
