"""A zero-bit self-interpreter demonstrating the benchmark's absolute floor.

The empty source denotes the decoder itself; every nonempty source keeps the
existing functional language's meaning. The complete kernel is ordinary closed
lambda calculus. Its larger size is reported alongside the zero-bit program.
"""

import argparse
import hashlib
import json
from pathlib import Path

from functional import app, bitlist, closed, encode, named, read_bits
from functional_candidates import decoder, search
from functional_rewrites import replay


def seed():
    # F self p = if p is empty then self else D p, using the unchanged pair list.
    # The constructor branch receives the extra empty-case argument and ignores it.
    return named(r"""
        (\self. self self)
        (\self bits. bits (\head tail ignored. base bits) (self self))
    """, {"base": decoder()})


def build():
    kernel, reduction = search(seed(), rounds=12, beam=64, slack=128)
    proof = [dict(rule="contract", path=list(path)) for path in reduction["beta_paths"]]
    if replay(seed(), proof) != kernel or not closed(kernel):
        raise ValueError("invalid kernel certificate")
    return kernel, dict(self_interpreter_bits=0, kernel_blc_bits=len(encode(kernel)),
                        baseline_kernel_blc_bits=len(encode(decoder())),
                        kernel_sha256=hashlib.sha256(encode(kernel).encode()).hexdigest(),
                        self_interpreter_sha256=hashlib.sha256(b"").hexdigest(),
                        contract="Unchanged separate raw program/input boolean-pair lists",
                        reduction=reduction, proof=proof)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--kernel", type=Path)
    parser.add_argument("--emit", type=Path)
    parser.add_argument("--run")
    parser.add_argument("--input", default="")
    parser.add_argument("--steps", type=int, default=1000000)
    args = parser.parse_args()
    kernel, report = build()
    files = ["functional.py", "functional_candidates.py", "empty_interpreter.py"]
    source = b"".join(Path(__file__).with_name(name).read_bytes() for name in files)
    report.update(source_files=files, source_bytes=len(source), source_sha256=hashlib.sha256(source).hexdigest())
    if args.run is not None:
        report["execution"] = read_bits(app(kernel, bitlist(args.run), bitlist(args.input)), budget=args.steps)
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    if args.kernel:
        args.kernel.write_text(encode(kernel))
    if args.emit:
        args.emit.write_text("")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
