"""Compile and run the single-generation Rule 30 example in Knot."""

import argparse
import hashlib
import json
from pathlib import Path

from core.artifacts import source_bytes, source_files
from core.lambda_calculus import app, bitlist, read_bits
from examples.rule30 import step_function
from languages.knot import build, compile_program


def program():
    return compile_program(step_function())


def metrics():
    bits = program()
    files = source_files(__file__)
    source = source_bytes(files)
    return dict(language="Knot", program_bits=len(bits),
                program_sha256=hashlib.sha256(bits.encode()).hexdigest(),
                source_files=files, source_bytes=len(source),
                source_sha256=hashlib.sha256(source).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="initial row; run one generation when supplied")
    parser.add_argument("--steps", type=int, default=20000000)
    parser.add_argument("--emit", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = metrics()
    if args.emit:
        args.emit.write_text(program())
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + "\n")
    if args.input is not None:
        result["execution"] = read_bits(app(build()[1], bitlist(program()), bitlist(args.input)),
                                        budget=args.steps, limit=len(args.input) + 1)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
